# AI 의견 (E51) 연결 방법

사용자 결정(2026-10-23): 확정 판정을 못 낼 때 **이용자가 버튼을 눌렀을 때만** Claude의 참고 의견을 보여 주는 것을 허용. 항상 「AI 의견 · 비공식」으로 표시하고, 모든 의견은 심판 확인 대기열에 들어가 확인되면 확정 판정으로 승격됩니다.

## 준비 (사용자가 해야 할 것)
1. `pip install anthropic`
2. API 키 설정(저장소·페이지에 넣지 않음). 가장 쉬운 방법: 메모장으로 `servernthropic_key.txt`를 만들어 키 한 줄만 저장(.gitignore에 들어 있음, 서버 재시작 불필요 수준으로 호출 때마다 읽음 — 단 `/api/ai` 연결 뒤). 또는 서버 프로세스의 `ANTHROPIC_API_KEY` 환경 변수(로그온 때 뜬 서버는 나중에 `setx`한 값을 못 보므로 키 파일이 더 안전). `GET /api/ai/usage`의 `ready`가 키 유무를 알려 줍니다. 모델 기본 `claude-opus-5-5`, effort `medium`; 바꾸려면 `AI_MODEL=claude-sonnet-5-5`(비용 절반), `AI_EFFORT=high`.
3. 한도: `AI_DAILY_USD`(기본 3.0달러/일), `AI_PER_IP_PER_DAY`(기본 10회). 한 번 호출은 입력 약 3천·출력 약 0.4천 토큰이라 Opus 5.5 기준 약 0.02달러(Sonnet 5.5는 약 0.01달러)이고, 3달러 한도면 하루 약 150회입니다. 같은 질문은 캐시되어 다시 과금되지 않습니다.

## server/app.py (두 군데; 허브 세션 파일이라 직접 고치지 않았습니다)
```python
from ai_opinion import register as register_ai          # sys.path에 server/ 필요(같은 폴더라면 그대로)
# RULES = json.load(open(os.path.join(ROOT, 'rules2.json'), encoding='utf-8'))['rules']; CARDS = {c['no']: c for c in json.load(open(.../'cards.json'))}
register_ai(app, dict(db_path=DB, QA=QA, cards=CARDS, rules=RULES,
                      search=lambda q, k: [h['i'] for h in fused_hits(q, k)],        # /api/search가 쓰는 융합 검색을 함수로 분리해 재사용
                      queue_draft=lambda d: insert_draft(d)))                       # drafts 표에 open으로 넣는 기존 함수(E41)
```
- 엔드포인트: `POST /api/ai {q, cards:[카드번호,...]}` → `{ans: 1|0|null, confidence, summary, refs:[{id, ref}], label, model, cached, usd}` 또는 429 `{error: 'budget'|'rate', message}`.
- `GET /api/ai/usage` → 오늘 사용액·한도(운영자용).

## 페이지 (v3_ui.js 쪽, 허브 세션)
- 판정이 `보류`일 때만 「AI 의견 보기」 버튼을 보여 줍니다. 누르면 `/api/ai` 호출.
- 결과는 확정 판정과 **다른 색·라벨**(`label` 값 그대로: 「AI 의견 · 비공식」)로, `confidence`가 low이거나 `ans`가 null이면 「판단 불가」로 표시합니다.
- 429면 「오늘 AI 의견 한도에 도달했습니다」를 보이고 기존 보류 화면으로 돌아갑니다.
- `refs`의 C/Q/R 번호는 근거 카드·Q&A·룰 조항으로 풀어서 링크합니다(서버가 `ref` 값으로 카드번호/Q&A 인덱스/조항 번호를 돌려줍니다).

## 안전장치 (모듈이 강제)
버튼 눌렀을 때만 호출 · 같은 질문 캐시 · 일 예산/IP 한도 · 근거(카드 문구·가까운 공식 Q&A 6개·룰 조항 5개)만 사용하고 모르면 null · 입력에 없는 근거 번호는 버림 · 모든 의견은 `src:'claude'` 초안으로 심판 대기열에 적재.
시험: `python tests/test_ai_opinion.py`(가짜 클라이언트; 캐시·예산·IP 한도·JSON 파싱·근거 필터).
