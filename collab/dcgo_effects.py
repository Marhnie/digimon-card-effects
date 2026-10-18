"""DCGO 카드 스크립트를 효과(타이밍 블록) 단위로 정적 분해: 블록마다 아이콘 태그, 턴 1회, 임의(isOptional),
선택 생략 가능(canNoSelect), 최대치 미만 종료 가능(canEndNotMax), 발휘 시 필드 재확인 여부. 출력 collab/dcgo_effects.json"""
import json, re, os, glob
SRC = os.environ.get('DCGO', r'C:\Users\Daewonmedia\ext\DCGO-Card-Scripts')
TAG = {'등장 시': r'\[On Play', '진화 시': r'\[When Digivolving|isWhenDigivolving:\s*true', '어택 시': r'\[When Attacking', '소멸 시': r'\[On Deletion|SaveEffect',
       '메인': r'\[Main\]', '시큐리티': r'\[Security\]|SecurityEffect\(', '자신의 턴': r"\[Your Turn\]", '상대의 턴': r"\[Opponent's Turn\]",
       '서로의 턴': r'\[All Turns\]', '자신의 메인 페이즈 개시 시': r'\[Start of Your Main Phase', '자신의 턴 종료 시': r'\[End of Your Turn',
       '자신의 턴 개시 시': r'\[Start of Your Turn', '어택 종료 시': r'\[End of Attack', '상대의 턴 종료 시': r"\[End of Opponent'?s Turn",
       '링크 시': r'\[When Link', '이동 시': r'\[When Moving'}
def brace(s, i):
    """s[i] 이후 첫 '{'부터 짝이 맞는 '}'까지"""
    j = s.find('{', i); d = 0
    for k in range(j, len(s)):
        if s[k] == '{': d += 1
        elif s[k] == '}':
            d -= 1
            if d == 0: return s[j:k + 1]
    return s[j:]
def methods(s):
    out = {}
    for m in re.finditer(r'\b(?:IEnumerator|bool|string|void|int|List<[^>]+>|[A-Z]\w+)\s+(\w+)\s*\([^;{)]*\)\s*\{', s):
        out.setdefault(m.group(1), brace(s, m.start()))
    return out
def expand(b, M, depth=3):
    seen = set(); txt = b
    for _ in range(depth):
        add = [n for n in M if n not in seen and re.search(r'\b' + n + r'\b', txt) and M[n] not in txt]
        if not add: break
        for n in add: seen.add(n); txt += '\n' + M[n]
    return txt
eff = {}
for f in glob.glob(os.path.join(SRC, 'CardEffect', '*', '**', '*.cs'), recursive=True):
    no = os.path.basename(f)[:-3].replace('_', '-')
    if not re.match(r'^[A-Z]+\d*-\d+$', no): continue
    s = open(f, encoding='utf-8', errors='ignore').read(); rows = []
    blk = [(m, brace(s, m.end())) for m in re.finditer(r'if\s*\(\s*timing\s*==\s*EffectTiming\.(\w+)\s*\)', s)]
    spans = [(m.end(), m.end() + len(b) + (s.find('{', m.end()) - m.end())) for m, b in blk]
    # 블록 밖(공유)에서 정의된 함수만 확장 대상
    M = {}
    for mm in re.finditer(r'(?:IEnumerator|bool|string|void|int|List<[^>]+>|[A-Z]\w+)\s+(\w+)\s*\([^;{)]*\)\s*\{', s):
        if not any(a <= mm.start() < b for a, b in spans): M.setdefault(mm.group(1), brace(s, mm.start()))
    for m, b in blk:
        x = expand(b, M)
        tags = sorted(k for k, p in TAG.items() if re.search(p, x, re.I))
        su = re.findall(r'SetUpActivateClass\([^;]*?,[^;]*?,\s*(-?\d+)\s*,\s*(true|false)\s*,', x)
        rows.append({'timing': m.group(1), 'tags': tags,
                     'once': any(a == '1' for a, _ in su), 'optional': any(o == 'true' for _, o in su),
                     'noselect': bool(re.search(r'canNoSelect:\s*true', x)), 'endnotmax': bool(re.search(r'canEndNotMax:\s*true', x)),
                     'all_forced': bool(re.search(r'canNoSelect:\s*false', x)) and not re.search(r'canNoSelect:\s*true', x),
                     'recheck_field': (lambda c: bool(re.search(r'IsExistOnBattleArea', c)) if c else None)((lambda mm: brace(x, mm.start()) if mm else '')(re.search(r'bool\s+\w*CanActivateCondition\w*\s*\(', x))),
                     'inherited': bool(re.search(r'isInheritedEffect:\s*true|SetIsInheritedEffect\(true\)', b)),
                     'desc': (re.findall(r'"(\[[^"]{5,300})"', x) or [''])[0][:300]})
    eff[no] = rows
json.dump(eff, open('collab/dcgo_effects.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(len(eff), sum(len(v) for v in eff.values()))
