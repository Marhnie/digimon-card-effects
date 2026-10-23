"""E51: 「AI 의견」 — 판정 도우미가 확정 판정을 못 낼 때, 이용자가 버튼을 눌렀을 때만 Claude에게 참고 의견을 받는다.
사용자 결정(2026-10-23): AI 의견을 이용자에게 보여 주는 것을 허용. 단, 공식 판정으로 보이면 안 되므로 항상 「AI 의견 · 비공식」으로 표시한다.

Safeguards (all enforced here, not in the page):
  * only on an explicit request (POST /api/ai), never automatically;
  * result cache by (question, cards) — a repeated question costs nothing;
  * daily budget in USD (AI_DAILY_USD, default 3.0) and per-IP rate (AI_PER_IP_PER_DAY, default 10) — beyond that: 429, page falls back to the plain 보류 화면;
  * every opinion is also queued as a draft (status open) so a judge can confirm / correct it (E41), and flagged src='claude';
  * the model gets the evidence S3 style (E3: 82 → 98 %): card texts, nearest official Q&A (RRF search), rulebook clauses; it must answer
    with JSON {ans, confidence, summary, refs}, may say null (「판단 불가」), and never cites anything it was not given.
Setup: pip install anthropic ; set ANTHROPIC_API_KEY (and optionally AI_MODEL, default claude-opus-5-5 ; AI_EFFORT default medium).
Wiring (server/app.py, two lines):  from ai_opinion import register ; register(app, ctx)   — see register() for the ctx fields.
"""
import json, os, re, sqlite3, time, threading

MODEL = os.environ.get('AI_MODEL', 'claude-opus-5-5')
EFFORT = os.environ.get('AI_EFFORT', 'medium')
DAILY_USD = float(os.environ.get('AI_DAILY_USD', '3.0'))
PER_IP = int(os.environ.get('AI_PER_IP_PER_DAY', '10'))
PRICE = {'claude-opus-5-5': (4.0, 20.0), 'claude-sonnet-5-5': (2.0, 10.0), 'claude-haiku-5-5': (0.1, 0.5)}   # $/MTok in, out
SYSTEM = """당신은 디지몬 카드게임(한국판)의 룰 판정 보조입니다. 아래 근거만 사용해 질문에 대한 의견을 JSON으로만 답합니다.
규칙:
- 근거는 (1) 카드 문구, (2) 가까운 공식 Q&A, (3) 종합 룰 조항입니다. 근거에 없는 효과나 룰을 만들어 내지 마세요.
- 공식 Q&A의 상황과 질문의 상황이 다르면(조건·수치·타이밍) 그대로 옮기지 말고 차이를 짚으세요.
- 판단할 근거가 부족하면 ans를 null로 하세요. 추측으로 네/아니요를 정하지 마세요.
- 출력: {"ans": 1(네) | 0(아니요) | null, "confidence": "high"|"medium"|"low", "summary": "한국어 3~6문장, 이유 중심", "refs": ["근거 번호", ...]}
- refs는 입력에 붙은 근거 번호(C1, Q2, R3 등)만 쓰세요."""


KEY_FILE = os.environ.get('AI_KEY_FILE', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'anthropic_key.txt'))


def _key_from_file():
    """Fallback for a server started at logon (its environment never sees a later `setx`): server/anthropic_key.txt (git-ignored), one line."""
    try:
        return open(KEY_FILE, encoding='utf-8').read().strip() or None
    except OSError:
        return None


def key_ready():
    return bool(os.environ.get('ANTHROPIC_API_KEY') or _key_from_file())


# E52: our own fine-tuned model (train/train_gen.py → merged weights) as a free backend; used when there is no API key
LOCAL_DIR = os.environ.get('AI_LOCAL_MODEL', os.path.join(os.path.dirname(os.path.abspath(__file__)), 'ai_local_model'))
local_ready = lambda: any(os.path.exists(os.path.join(LOCAL_DIR, f)) for f in ('config.json', 'adapter_config.json'))


def backend():
    b = os.environ.get('AI_BACKEND', 'auto')
    if b == 'auto': return 'api' if key_ready() else 'local' if local_ready() else None
    return b if (b == 'api' and key_ready()) or (b == 'local' and local_ready()) else None


class LocalGen:
    """CPU inference of the fine-tuned model; the same prompt as training (gen_prompt.py). Loaded on first use."""
    def __init__(self):
        self.tok = self.model = None; self.lock = threading.Lock()

    def load(self):
        if self.model is None:
            import torch
            from transformers import AutoTokenizer, AutoModelForCausalLM
            self.torch = torch
            self.tok = AutoTokenizer.from_pretrained(LOCAL_DIR)
            if os.path.exists(os.path.join(LOCAL_DIR, 'adapter_config.json')):
                # LoRA adapter (what train_gen.py ships): the public base model is fetched from Hugging Face once (cached), then merged
                from peft import PeftModel
                info = os.path.join(LOCAL_DIR, 'gen_info.json')
                base_id = json.load(open(info, encoding='utf-8'))['base_model'] if os.path.exists(info) else                     json.load(open(os.path.join(LOCAL_DIR, 'adapter_config.json'), encoding='utf-8'))['base_model_name_or_path']
                base = AutoModelForCausalLM.from_pretrained(base_id, torch_dtype=torch.bfloat16)
                self.model = PeftModel.from_pretrained(base, LOCAL_DIR).merge_and_unload().eval()
            else:
                self.model = AutoModelForCausalLM.from_pretrained(LOCAL_DIR, torch_dtype=torch.bfloat16).eval()
            t = self.tok
            self.yes = list({t('네', add_special_tokens=False)['input_ids'][0], t('예', add_special_tokens=False)['input_ids'][0]})
            self.no = list({t('아니요', add_special_tokens=False)['input_ids'][0], t('아니', add_special_tokens=False)['input_ids'][0]})

    def answer(self, system, user):
        with self.lock:
            self.load(); torch = self.torch
            p = self.tok.apply_chat_template([{'role': 'system', 'content': system}, {'role': 'user', 'content': user}], tokenize=False, add_generation_prompt=True)
            ids = self.tok(p, add_special_tokens=False, return_tensors='pt')['input_ids'][:, -1280:]
            with torch.no_grad():
                pr = self.model(input_ids=ids).logits[0, -1].float().softmax(-1)
                py, pn = float(pr[self.yes].sum()), float(pr[self.no].sum())
                g = self.model.generate(input_ids=ids, max_new_tokens=200, do_sample=False, pad_token_id=self.tok.pad_token_id or self.tok.eos_token_id)
            return self.tok.decode(g[0, ids.shape[1]:], skip_special_tokens=True).strip(), py / ((py + pn) or 1)


LOCAL = LocalGen()


def _bg(s):
    t = re.sub(r'\s+', '', s)
    return {t[i:i + 2] for i in range(len(t) - 1)}


def _jac(a, b):
    x = len(a & b)
    return x / ((len(a) + len(b) - x) or 1)


class AiOpinion:
    def __init__(self, db_path, QA, cards, rules, search, client=None):
        """search(q, k) -> [qa_index, ...] (the server's fused retrieval). cards: {no: card dict}. rules: rules2.json['rules'] list."""
        self.QA, self.cards, self.search = QA, cards, search
        self.rules = [r for r in rules if r.get('l', 0) >= 2 and r.get('t')]
        self.rbg = [_bg(r['t']) for r in self.rules]
        self.db_path, self.lock, self._client = db_path, threading.Lock(), client
        with self._db() as c:
            c.execute('create table if not exists ai_cache (key text primary key, doc text, at real)')
            c.execute('create table if not exists ai_spend (id integer primary key, at real, ip text, usd real, key text)')

    def _db(self):
        return sqlite3.connect(self.db_path)

    @property
    def client(self):
        if self._client is None:
            import anthropic
            key = os.environ.get('ANTHROPIC_API_KEY') or _key_from_file()
            self._client = anthropic.Anthropic(api_key=key) if key else anthropic.Anthropic()
        return self._client

    # ---------- evidence ----------
    def evidence(self, q, card_nos, k_qa=6, k_rule=5):
        ev, lines = {}, []
        for n, no in enumerate(card_nos[:4], 1):
            c = self.cards.get(no)
            if not c: continue
            ev[f'C{n}'] = no
            lines.append(f"[C{n}] {no} {c.get('name', '')} ({c.get('type', '')})\n{c.get('상단 텍스트', '')}\n진화원 효과: {c.get('하단 텍스트', '') or '-'}")
        qa_idx = [i for i in self.search(q, k_qa + 4) if self.QA[i][0]][:k_qa]
        for n, i in enumerate(qa_idx, 1):
            ev[f'Q{n}'] = i
            ans = re.sub(r'\s+', ' ', self.QA[i][2])[:500]
            lines.append(f"[Q{n}] 공식 Q&A ({self.QA[i][0]})\nQ: {self.QA[i][1]}\nA: {ans}")
        A = _bg(q + ' ' + ' '.join(self.cards[no].get('상단 텍스트', '') for no in card_nos[:2] if no in self.cards))
        top = sorted(range(len(self.rules)), key=lambda j: -_jac(A, self.rbg[j]))[:k_rule]
        for n, j in enumerate(top, 1):
            ev[f'R{n}'] = self.rules[j]['n']
            lines.append(f"[R{n}] 종합 룰 {self.rules[j]['n']}: {self.rules[j]['t'][:400]}")
        return ev, '\n\n'.join(lines)

    # ---------- budget ----------
    def spent_today(self):
        t0 = time.time() - 86400
        with self._db() as c:
            return c.execute('select coalesce(sum(usd),0) from ai_spend where at>?', (t0,)).fetchone()[0]

    def ip_count(self, ip):
        with self._db() as c:
            return c.execute('select count(*) from ai_spend where at>? and ip=?', (time.time() - 86400, ip)).fetchone()[0]

    # ---------- main ----------
    def ask(self, q, card_nos, ip='-'):
        q = q.strip()[:600]
        key = q + '|' + ','.join(card_nos[:4])
        with self._db() as c:
            row = c.execute('select doc from ai_cache where key=?', (key,)).fetchone()
        if row:
            return {**json.loads(row[0]), 'cached': True}
        if backend() == 'local':
            return self.ask_local(q, card_nos, key, ip)
        if self.spent_today() >= DAILY_USD: return {'error': 'budget', 'message': '오늘 AI 의견 한도에 도달했습니다.'}
        if self.ip_count(ip) >= PER_IP: return {'error': 'rate', 'message': '하루 이용 한도를 넘었습니다.'}
        ev, text = self.evidence(q, card_nos)
        msg = f"질문: {q}\n\n근거:\n{text}"
        # max_tokens covers adaptive thinking + the JSON answer, so leave room (1500 could cut the answer off)
        r = self.client.messages.create(model=MODEL, max_tokens=16000, system=SYSTEM, messages=[{'role': 'user', 'content': msg}],
                                        output_config={'effort': EFFORT}, thinking={'type': 'adaptive'})
        if getattr(r, 'stop_reason', None) == 'refusal':
            return {'error': 'refusal', 'message': 'AI 의견을 받을 수 없는 질문입니다.'}
        out = next((b.text for b in r.content if b.type == 'text'), '')
        m = re.search(r'\{.*\}', out, re.S)
        try:
            d = json.loads(m.group(0)) if m else {}
        except Exception:
            d = {}
        ans = d.get('ans') if d.get('ans') in (0, 1) else None
        doc = {'ans': ans, 'confidence': d.get('confidence') if d.get('confidence') in ('high', 'medium', 'low') else 'low',
               'summary': str(d.get('summary') or out)[:1500], 'refs': [{'id': x, 'ref': ev[x]} for x in (d.get('refs') or []) if x in ev],
               'model': MODEL, 'label': 'AI 의견 · 비공식'}
        pin, pout = PRICE.get(MODEL, (4.0, 20.0))
        usd = r.usage.input_tokens * pin / 1e6 + r.usage.output_tokens * pout / 1e6
        with self._db() as c:
            c.execute('insert or replace into ai_cache values (?,?,?)', (key, json.dumps(doc, ensure_ascii=False), time.time()))
            c.execute('insert into ai_spend (at, ip, usd, key) values (?,?,?,?)', (time.time(), ip, usd, key))
        return {**doc, 'cached': False, 'usd': round(usd, 4)}


def _ask_local(self, q, card_nos, key, ip):
    """E52: free opinion from our own model. Confidence = P(네) vs P(아니요) at the first token; below LOCAL_CONF it says 판단 불가."""
    if self.ip_count(ip) >= PER_IP: return {'error': 'rate', 'message': '하루 이용 한도를 넘었습니다.'}
    import sys
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from gen_prompt import SYSTEM as GSYS, prompt as gprompt
    c = self.cards.get(card_nos[0]) if card_nos else None
    nb = [{'id': i, 'card': self.QA[i][0], 'question': self.QA[i][1]} for i in [i for i in self.search(q, 8) if self.QA[i][0]][:4]]
    x = {'question': q, 'card': card_nos[0] if card_nos else '', 'card_name': (c or {}).get('name', ''), 'effect': '',
         'card_text': ((c or {}).get('상단 텍스트', '') + ' / 진화원: ' + ((c or {}).get('하단 텍스트', '') or '-')) if c else '', 'neighbours': nb}
    out, p = LOCAL.answer(GSYS, gprompt(x, self.QA))
    conf = max(p, 1 - p); thr = float(os.environ.get('LOCAL_CONF', '0.9'))
    head = out[:6]
    ans = 1 if head.startswith(('네', '예')) else 0 if head.startswith('아니') else None
    doc = {'ans': ans if conf >= thr else None, 'confidence': 'high' if conf >= 0.97 else 'medium' if conf >= thr else 'low',
           'summary': out[:1500], 'refs': [{'id': f'Q{n + 1}', 'ref': d['id']} for n, d in enumerate(nb)],
           'model': 'local:' + os.path.basename(os.path.normpath(LOCAL_DIR)), 'label': 'AI 의견 (자체 모델) · 비공식', 'p_yes': round(p, 3)}
    with self._db() as cdb:
        cdb.execute('insert or replace into ai_cache values (?,?,?)', (key, json.dumps(doc, ensure_ascii=False), time.time()))
        cdb.execute('insert into ai_spend (at, ip, usd, key) values (?,?,?,?)', (time.time(), ip, 0.0, key))
    return {**doc, 'cached': False, 'usd': 0.0}


AiOpinion.ask_local = _ask_local


def register(app, ctx):
    """ctx: dict(db_path, QA, cards, rules, search, queue_draft). search(q,k)->qa indices; queue_draft(doc) inserts a draft row (optional).
    Adds POST /api/ai {q, cards:[no,...]} and GET /api/ai/usage (spend today)."""
    from fastapi import Request
    from fastapi.responses import JSONResponse
    ai = AiOpinion(ctx['db_path'], ctx['QA'], ctx['cards'], ctx['rules'], ctx['search'])

    @app.post('/api/ai')
    async def api_ai(req: Request):
        b = await req.json(); q = str(b.get('q', '')); cards = [str(x) for x in (b.get('cards') or [])][:4]
        ip = req.headers.get('cf-connecting-ip') or (req.client.host if req.client else '-')
        if not q.strip(): return JSONResponse({'error': 'empty'}, status_code=400)
        try:
            res = ai.ask(q, cards, ip)
        except Exception as e:   # missing key, network, API error: the page keeps its plain 보류 view
            print('ai opinion failed', type(e).__name__, e)
            return JSONResponse({'error': 'unavailable', 'message': 'AI 의견을 지금 받을 수 없습니다.'}, status_code=503)
        if res.get('error'): return JSONResponse(res, status_code=429 if res['error'] in ('budget', 'rate') else 422)
        if not res.get('cached') and ctx.get('queue_draft'):
            ctx['queue_draft']({'q': q, 'card': cards[0] if cards else '', 'others': ','.join(cards[1:]), 'ans': res['ans'], 'summary': res['summary'],
                                'src': 'claude', 'note': 'AI 의견(이용자 요청)'})
        return res

    @app.get('/api/ai/usage')
    def api_ai_usage():
        b = backend()
        return {'ready': b is not None, 'backend': b, 'spent_today_usd': round(ai.spent_today(), 3), 'daily_cap_usd': DAILY_USD,
                'model': MODEL if b == 'api' else ('local:' + os.path.basename(os.path.normpath(LOCAL_DIR)) if b == 'local' else None)}
    return ai
