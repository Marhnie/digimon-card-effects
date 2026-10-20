"""Build qnorm_dict.json / qnorm_names.json (rules shared by qnorm.py and v3_qnorm.js).

Sources: official wording mined from the pre-BT22 Q&A (test_data4.json) and card text; general Korean TCG
community slang. Card / feature names come ONLY from test_data4.json cards (no invented proper nouns).
Replacement strings use $1-style groups (qnorm.py converts them for Python).
Order matters: rules are applied top to bottom.
"""
import json, re, collections

T = json.load(open('test_data4.json', encoding='utf-8'))
R = []
CUR = 'num'


def r(p, rep, note=''):
    R.append({'p': p, 'r': rep, 'n': note, 'g': CUR})


# --- 0. noise cleanup (applied before the rules) ---
PRE = [
    {'p': '≪', 'r': '《'},
    {'p': '≫', 'r': '》'},
    {'p': '[ㅋㅎㅠㅜㅡ]{2,}', 'r': ' '},
    {'p': '(?:^|\\s)ㅇㅇ(?=\\s|$)', 'r': ' '},
    {'p': '[~^]+', 'r': ' '},
    {'p': '[!]{2,}', 'r': '!'},
    {'p': '[?]{2,}', 'r': '?'},
    {'p': '\\.{2,}', 'r': ' '},
    {'p': '(?:^|\\s)(?:혹시|근데|그럼|님들?|질문)(?=\\s)', 'r': ' '},
]

# --- 1. card numbers ---
r('\\b([Bb][Tt]|[Ee][Xx]|[Ss][Tt]|[Pp])\\s*-?\\s*(\\d{1,2})\\s*-\\s*(\\d{2,3})\\b', '$1$2-$3', 'card no spacing')

CUR = 'timing'
# --- 2. timings (guard: 시키/시켜 = causative, e.g. 등장시키면) ---
G = '(?![키켜킨킬킴])'
def tm(p, rep, note=''):  # timing rule that leaves already-bracketed 【...】 alone
    r('(?<!【)' + p + '(?!】)', rep, note)


for a in ['등장', '진화', '어택', '소멸', '링크', '이동']:
    tm(a + '\s*시' + G + '(?:에)?', '【' + a + ' 시】', a + '시 -> 【' + a + ' 시】')
tm('어택\s*종료\s*시', '【어택 종료 시】')
tm('(?:자신|내|나의?)\s*의?\s*턴\s*종료\s*시', '【자신의 턴 종료 시】')
tm('상대(?:방)?\s*의?\s*턴\s*종료\s*시', '【상대의 턴 종료 시】')
tm('(?:자신|내|나의?)\s*의?\s*메인\s*페이즈\s*(?:개시|시작)\s*시', '【자신의 메인 페이즈 개시 시】')
tm('(?:자신|내|나의?)\s*의?\s*턴\s*(?:개시|시작)\s*시', '【자신의 턴 개시 시】')
r('(?:자신|내|나의?)\\s*의?\\s*턴(?=\\s*효과)', '【자신의 턴】')
r('상대(?:방)?\\s*의?\\s*턴(?=\\s*효과)', '【상대의 턴】')
r('서로\\s*의?\\s*턴(?=\\s*효과)', '【서로의 턴】')
r('(?<![가-힣【])메인\\s*효과', '【메인】 효과')
r('시큐(?:리티)?\\s*효과', '【시큐리티】 효과')
r('(?<![가-힣])등시(?![가-힣])', '【등장 시】')
r('(?<![가-힣])진시(?![가-힣])', '【진화 시】')
r('(【[^】]+】)\\s*효과\\s*효과', '$1 효과')

CUR = 'keyword'
# --- 3. keyword effects (official 《》 forms mined from the Q&A) ---
r('《?(\\d)\\s*드로(?:우)?》?', '《$1 드로우》', 'N드로')
r('《?시큐(?:리티)?\\s*어택\\s*([+-])\\s*(\\d)》?', '《시큐리티 어택 $1$2》')
r('《?(?<![가-힣])[Ss]\s*어택\s*([+-])\s*(\d)》?', '《S 어택 $1$2》')
r('(?<!《)리커버리\s*\+?\s*(\d)(?![^《》]*》)', '《리커버리 +$1》')
for k, o in [('블로커', '블로커'), ('블록커', '블로커'), ('관통', '관통'), ('세이브', '세이브'), ('재기동', '재기동'),
             ('재밍', '재밍'), ('속공', '속공'), ('돌진', '돌진'), ('진격', '진격'), ('방벽', '방벽'), ('충돌', '충돌'),
             ('불굴', '불굴'), ('회피', '회피'), ('길동무', '길동무'), ('딜레이', '딜레이'), ('디지버스트', '디지버스트'),
             ('아머\\s*퍼지', '아머 퍼지'), ('블래스트\\s*진화', '블래스트 진화'), ('흡수\\s*진화', '흡수진화')]:
    r('(?<![《가-힣])' + k + '(?![》가-힣])', '《' + o + '》', 'keyword')

CUR = 'term'
# --- 4. zone / term synonyms -> official wording ---
r('시큐(?!리)', '시큐리티', '시큐 = 시큐리티')
r('(?:상속|밑|하단)\\s*효과', '진화원 효과', '상속 효과 = 진화원 효과')
r('상속', '진화원 효과')
r('진화원\\s*효과', '진화원 효과')
r('(?:배틀\\s*존|배틀\\s*필드|필드|전장)(?![가-힣]*에어리어)', '배틀 에어리어')
r('육성\\s*(?:존|구역)', '육성 에어리어')
r('(?:핸드|손패)', '패')
r('(?:묘지|그레이브|트래쉬)', '트래시')
r('(?:디지타마\\s*덱|알\\s*덱)', '디지타마 덱')
r('(?<![가-힣])메모(?![리가-힣])', '메모리')
r('(?<![A-Za-z])[Dd][Pp]\\s*(?=[-+]?\\d)', 'DP ')
r('(?<![A-Za-z])[Dd][Pp](?![A-Za-z])', 'DP')
r('한\\s*장', '1장'); r('한\\s*마리', '1마리'); r('두\\s*장', '2장'); r('두\\s*마리', '2마리')
r('(?:턴\\s*1\\s*회|1\\s*턴\\s*1\\s*회)', '[턴 1회]')
r('발동', '발휘'); r('소환', '등장')
r('죽으면', '소멸하면'); r('죽었을', '소멸했을'); r('죽는', '소멸하는'); r('죽어도', '소멸해도'); r('죽이', '소멸시키')
r('어케|어캐|어떡', '어떻게'); r('뭐야|머야|뭔가요|뭐임|머임', '무엇인가요')
r('안\\s*받', '받지 않'); r('안\\s*쓰', '쓰지 않')

CUR = 'ending'
# --- 5. predicate endings -> official 「~할 수 있나요?」 ---
r('(?:쓸|써질)\\s*수\\s*(?=있|잇)', '발휘할 수 ', '쓸 수 있 = 발휘할 수 있')
r('(?:써도|써지|써짐|써져)', '발휘할 수 있')
r('수\\s*(?:있|잇)(?:어여?|나여?|냐|음|엉|니|는가|어요|을까요?|는지|ㅇ|는거야|는거임|는\\s*거야|는\\s*건가요|나요|습니까)?\\s*[?]*\\s*$', '수 있나요?')
r('수\\s*(?:없|업)(?:어여?|나여?|냐|음|엉|니|는가|어요|나요|습니까)?\\s*[?]*\\s*$', '수 없나요?')
r('(?:가능해여?|가능함|가능하냐|가능하나|ㄱㄴ|가능한가요|가능)\\s*[?]*\\s*$', '가능한가요?')
r('유발\\s*(?:됨|되냐|되나여|되나염|되나|돼)\\s*[?]*\\s*$', '유발되나요?')
r('발휘\\s*(?:됨|되냐|되나여|되나염|되나|돼)\\s*[?]*\\s*$', '발휘되나요?')
r('어떻게\\s*(?:됨|되나여?|돼|되는거야|되냐)\\s*[?]*\\s*$', '어떻게 되나요?')
r('([되돼])(?:냐|니|나여|나염|나|지|는거야|는거임|는\\s*건가요|는건가요|요|여|염)?\\s*[?]*\\s*$', '되나요?')
r('([가-힣])함\s*[?]*\s*$', '$1하나요?')
r('([하했])(?:냐|니|남|나염|나여|나|함)\\s*[?]*\\s*$', '$1나요?')

F = T['form']
ASK = [  # first match wins; endings mined from pre-BT22 questions (있나요 679, 되나요 224, 얻나요 126, 발휘하나요 85, 유발되나요 79 ...)
    ['발휘', '발휘할 수|발휘하나|발휘되나|발휘합니까|발휘됩니까'],
    ['유발', '유발'],
    ['진화', '진화할 수|진화하나|진화합니까'],
    ['등장', '등장시킬 수|등장할 수|등장하나|등장합니까'],
    ['부여·획득', '얻나요|얻습니까|부여'],
    ['순서', '순서'],
    ['정의', '무엇인가요|무엇입니까|의미|뜻|어떤 효과|룰인가요'],
    ['처리', '어떻게'],
    ['가능', '수 있나요|수 있습니까|수 없|가능한가요'],
]
d = {'pre': PRE, 'rules': R, 'slots': F['slots'], 'intents': F['intents'], 'ask': ASK,
     'weights': {'timing': 0.0, 'ask': 0.08, 'slot': 0.10, 'card': 0.0}}
json.dump(d, open('qnorm_dict.json', 'w', encoding='utf-8'), ensure_ascii=False, indent=0)
names = sorted({v[0] for v in T['cards'].values() if v[0]})
json.dump(names, open('qnorm_names.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(len(R), 'rules', len(names), 'names')

# common-word guard for the truncated-name expansion: hangul tokens (>=3 chars) seen >=3 times in the official Q&A text
# that are not themselves official card names (so 「디지몬」 etc. are never expanded to a card name that starts with them)
cnt = collections.Counter(re.findall(r'[가-힣]{3,}', ' '.join(r[1] + ' ' + r[2] for r in T['qa'])))
nm = {n.replace(' ', '') for n in names}
vocab = sorted(t for t, c in cnt.items() if c >= 3 and t not in nm)
json.dump(vocab, open('qnorm_vocab.json', 'w', encoding='utf-8'), ensure_ascii=False)
print(len(vocab), 'common words')
