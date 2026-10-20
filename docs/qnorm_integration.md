# 판정 도우미에 질문 정규화(v3_qnorm.js) 연결하는 방법 (E31)

이 문서는 **연결 방법만** 적습니다. `v3_ui.js`·`test_template.html`·`v3_head.html`은 이 작업에서 수정하지 않았습니다. 연결은 허브 세션이 합니다.

## 파일
| 파일 | 역할 |
|---|---|
| `v3_qnorm.js` | 전역 `QN` 하나만 만듭니다. 외부 라이브러리 없음, 약 84KB(사전 규칙 82개 + 카드명 1,847개 + 일반어 1,877개). `qnorm.py`와 출력이 같음을 구어체 200문항에서 확인했습니다(불일치 0). |
| `qnorm_dict.json`, `qnorm_names.json`, `qnorm_vocab.json` | 사전·카드명·일반어. `python qnorm_make_dict.py`로 만들고, `python qnorm_make_js.py`로 `v3_qnorm.js`를 다시 만듭니다. |

`build_v3.py`(또는 `v3_head.html`을 이어 붙이는 단계)에서 `v3_qnorm.js` 내용을 `v3_ui.js`보다 앞에 넣으면 됩니다.

## QN API
- `QN.normalize(q)` → 공식 표현으로 바꾼 질문. 예: 「샤인그레이몬 루인모드가 걸려있는데 파피몬 등장시키면 1드로 등장시효과 쓸수있어?」 → 「… 파피몬 등장시키면 《1 드로우》 【등장 시】효과 발휘할 수 있나요?」
- `QN.content(s)` → 2-gram 비교용 본문(질문 끝맺음과 「이 카드의」 같은 군말 제거).
- `QN.frame(s)` → `{cards, timing, slots, ask}` (대상 카드 / 효과(타이밍) / 상황 / 묻는 것).
- `QN.frameBonus(fq, fd, cardName)` → 틀 일치 가산점(현재 가중치: 묻는 것 0.08, 상황 0.10, 타이밍 0, 카드 0).
- `QN.simQ(a, b)` → `v3_ui.js`의 `simQ`와 같은 2-gram Jaccard.

## 어디를 바꾸나
지금 `ST.q`를 `simQ(ST.q, q.q)` 형태로 쓰는 곳이 판정 도우미의 질문–Q&A 유사도입니다.

1. **한 곳에서 만들기.** `judge()`(약 401행, `ST.res=precedents()`를 부르는 줄 바로 앞)와 `askq`의 `input` 핸들러(약 484행)에서 `ST.qn = QN.normalize(ST.q)`를 계산해 둡니다. 화면에 보이는 `ST.q`와 저장(`crDoc`·`doc.q`)은 그대로 원문을 씁니다.
2. **비교용 문장만 `ST.qn`으로 바꾸기.** 아래는 모두 「사용자 질문 ↔ 공식 Q&A」 유사도라서 `ST.q` 자리에 `ST.qn`을 넣으면 됩니다.
   - `precedents()` 안 (104행 `simQ(ST.q,q.q)`, 112행 `simQ(ST.q,q.q)`)
   - `similarQA()` (121행 `bg(ST.q)`) → `bg(QN.content(ST.qn))`
   - 139·156·220행의 `simQ(ST.q, QA[x.i].q)`
   - `crMatch()` (277행), `comboRef()`(350행 부근), `explainRef()`(381행 `bg(ST.q)`)
   - 의도·상황 자동 분류 `intentOf(ST.q)`, `slotsOf(ST.q)`(84행)는 **원문 그대로** 두어도 되고, `ST.qn`으로 바꿔도 됩니다(공식 표현이 정규식에 더 잘 걸립니다). 바꾸면 `tests/t11.js`의 엔진 수치(확신 44.5%, 정확도 96.6%)가 변하지 않는지 먼저 확인하세요.
3. **말뭉치 쪽도 같은 방식으로.** 공식 Q&A 질문도 `QN.content(QN.normalize(q.q, false))`로 바꾼 2-gram 집합을 캐시(`QBG`, `EXQB`)에 넣어야 합니다. 질문만 정규화하고 말뭉치는 원문이면 오히려 떨어집니다(E31 개발 세트: 질문만 정규화 0.71, 양쪽 정규화 0.77, 양쪽 + 군말 제거 0.84).
4. **틀 가산점(선택).** `similarQA()`의 점수 `s`에 `QN.frameBonus(fq, fd, cardName)`을 더하려면 `fq=QN.frame(ST.qn)`을 한 번, 각 Q&A의 `fd=QN.frame(정규화된 q.q)`를 캐시로 만듭니다. E31 평가에서는 효과가 작거나 없었으므로(아래 표) 기본은 꺼 두기를 권합니다.
5. **카드명 자동 인식(`qCards`, 338행).** `ST.qn`에는 유일 접두 일치로 늘린 공식 카드명이 들어 있고 `QN.frame(ST.qn).cards`가 후보를 줍니다. 쓸 때는 `qCards`의 기존 결과와 합집합만 하고, 근거가 약한 접두 일치로 카드를 자동 추가하지는 마세요.

## 주의
- 사전은 한 방향(구어체→공식)이고, 모르는 약칭(예: 「샤그」)은 그대로 둡니다. 근거 없는 고유명칭을 확정하지 않기 위해서입니다. 후보 목록은 `paper/results/e31_unresolved_terms.json`.
- 정규화는 판정이 아니라 **검색용**입니다. 정규화된 문장을 사용자에게 보여 줄 때는 「이렇게 이해했습니다」로 표시하세요.
