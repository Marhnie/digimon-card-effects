# 질문 → DCGO 시나리오 변환 지침 (q2scenario)

당신은 디지몬 카드게임 공식 Q&A 「네/아니요」 질문을 **룰 엔진(DCGO) 시험 장치용 시나리오**로 바꾸는 변환기입니다.
공식 답은 모릅니다(받지도 말고 찾지도 마세요). 목표는 "엔진이 실제로 돌려서 답이 갈리도록" 상황을 구성하는 것입니다.

## 금지(누설 방지)
- 저장소의 `pilot_set*`, `qa*.json`, `gold*`, `eval*`, `paper/`, `test_data*.json`, `collab/jobs`는 **열지도 grep하지도 마세요**. 카드 정보는 오직 `python -X utf8 lookup.py <ID또는이름>` 으로만 보세요(`PYTHONIOENCODING=utf-8`).
- 답이 무엇일지 추측해 판정 규칙을 짜지 마세요. 판정 규칙은 "엔진에서 관측될 사실 → 네/아니요" 의 기계적 대응이어야 합니다.

## 시험 장치가 하는 일
디지몬 카드게임 엔진 DCGO를 봇 대전으로 띄우고, 내 차례 메인 페이즈에서 **보드를 주입**한 뒤 **단계(steps)를 실행**하고, 효과 로그와 최종 상태를 남깁니다.
제약:
- 나(you)가 먼저 행동하는 내 차례 메인 페이즈 한 번만 재현됩니다. 상대 차례/턴 시작 효과/턴 종료 효과(할 일이 없으면 엔진이 턴을 자동 종료함)는 어렵습니다.
- 내 쪽 선택(대상·장수·패 선택·「~하지 않음」)은 장치가 정하지 못하고 엔진 봇 로직이 자동으로 고릅니다. 따라서 **후보가 하나뿐이라 선택이 자명한 상황**이거나 선택이 필요 없는 효과만 믿을 수 있습니다. 질문이 "(특정 선택을) 할 수 있는가/하지 않을 수 있는가"를 묻는데 선택을 지정해야 하면 unsupported(needs_choice).
- 「발휘할 수 있는가」「조건을 만족하는가」「코스트를 지불하는가」「효과가 처리되는가」처럼 **효과가 발동·처리되는지**를 묻는 문항이 가장 잘 재현됩니다.
- 메모리는 `memory`로 내 메모리(기본 10 권장; 높은 코스트면 충분히 크게)를 정합니다. 최종 메모리 값은 턴이 넘어가면 부호가 뒤집혀 신뢰할 수 없으므로 판정 규칙에서 쓰지 마세요(예외: 로그로 확인되는 코스트는 효과 설명).
- 사용할 카드는 반드시 DCGO에 있는 카드여야 합니다(lookup.py가 `DCGO:yes/NO`로 알려줌). 없으면 unsupported(not_impl).
- 보드에 필요한 보조 카드(대상용 상대 디지몬, 진화 소스, 패의 카드 등)는 질문이 요구하는 카드가 있으면 그것을, 아니면 `python -X utf8 lookup.py --filler` 의 효과 없는 카드(Lv별)를 쓰세요. 특징·유형·레벨 조건이 있으면 lookup.py로 조건에 맞는 실제 카드를 찾으세요.

## 출력 JSON (항목 하나)
```
{"id": <문항 id>, "status": "ok" | "unsupported",
 "reason": null | "needs_choice" | "opp_turn" | "multi_card" | "hand_or_inherited" | "not_impl" | "other",
 "note": "한 줄 설명(왜 이렇게 구성했는지/왜 불가능한지)",
 "job": { ... },        // status=ok일 때만
 "verdict": { "yes_if": {"all": [조건...]}  또는 {"any": [조건...]} }   // status=ok일 때만. 모두(all)/하나라도(any) 참이면 「네」, 아니면 「아니요」
}
```
unsupported 사유 코드: needs_choice(특정 선택 지정 필요), opp_turn(상대 차례·턴 시작/종료 시점 필요), multi_card(질문이 다른 카드와의 복잡한 상호작용/여러 카드 상황을 요구해 구성이 불확실), hand_or_inherited(진화원 효과·{패}/{트래시} 효과 등 특수 영역 효과 발휘 필요), not_impl(DCGO에 카드 없음 등), other. 애매하면 무리하게 ok로 만들지 말고 unsupported로 내세요.

### job 스키마
```
{"id": "q<문항id>",
 "you": {"memory": 10, "hand": ["ID",...], "trash": ["ID",...], "security": ["ID",...], "field": [ {"cards": ["위 카드ID","...아래(진화원)..."], "suspended": false}, ... ]},
 "opp": { 같은 구조(memory는 0), 상대 필드/트래시/시큐리티/패 },
 "steps": [ ... ],
 "timeScale": 20}
```
- `field`의 각 항목은 디지몬 한 마리의 스택: `cards[0]`이 **맨 위 카드**(디지몬 본체), 뒤가 진화원(위→아래). 한 장만 쓰면 진화원 없음. 디지타마 진화원은 디지타마 ID.
- security는 카드 ID 목록(장수가 의미). 비우면 0장. hand/trash는 주입 전 전부 비워지고 지정한 것만 들어갑니다. 지정하지 않은 영역은 빈 상태.
- 필드 순서가 스텝의 `frame` 번호(0부터)입니다. 테이머도 필드 스택(1장)으로 둡니다.
### steps (순서대로 실행, 각 단계 후 효과 처리가 끝날 때까지 기다림)
- `{"do":"play","card":"ID"}` : 패의 카드를 사용(디지몬/테이머 등장, 옵션 사용). 등장 시 효과 등이 자동 유발.
- `{"do":"digivolve","card":"패ID","frame":k}` : 필드 k번 디지몬을 패의 카드로 진화.
- `{"do":"activate","frame":k,"skill":0}` : 필드 k번 디지몬의 【메인】 등 능동 효과 발휘(skill=0이 첫 번째 능동 효과, 효과가 여럿이면 1,2…).
- `{"do":"attack","frame":k,"target":-1}` : k번 디지몬으로 상대 플레이어에 어택. target=상대 필드 번호(0부터)면 디지몬에 어택.
- `{"do":"optional","yes":true|false}` : 이후 「~할 수 있다」 선택 효과를 발휘(true)/거절(false). 기본 true.
- `{"do":"pass"}` : 턴 종료(보통 불필요).
### verdict 조건(DSL) — 최종 상태(you/opp)와 효과 로그로 검사
- `{"op":"log_has","re":"정규식"}` / `{"op":"log_not","re":"..."}` : 로그 항목 중 하나라도 정규식에 맞는다/맞지 않는다. 로그 항목은 줄바꿈이 ` / `로 바뀐 한 줄입니다. 예) `Effect: / Angewomon(BT23-031) / "Add top security..."`, `Delete: / Garurumon(BT23-018)`, `Play on field: / 카드명(ID)`, `Evolution: / ...`, `Add 1 cards to security:Player`, `De-Digivolve : / ...`, `Draw 1 card / Player`. 카드 ID(예 BT23-031)나 "Effect:" 로 키를 잡으세요. 효과가 발휘되면 `Effect:` 항목이 생깁니다.
- `{"op":"log_not","re":"step error"}` : 단계 자체가 거부/실패하지 않았다(필요하면 사용).
- `{"op":"field_count","side":"you|opp","cmp":"==|<|>|<=|>=","n":정수}` : 필드 디지몬/테이머 스택 수(최종).
- `{"op":"stack_size","side":..,"idx":k,"cmp":..,"n":..}` : 필드 k번 스택의 카드 수. `{"op":"dp","side":..,"idx":k,"cmp":..,"n":..}`
- `{"op":"hand_count|trash_count|security_count","side":..,"cmp":..,"n":..}`, `{"op":"hand_has|trash_has","side":..,"card":"ID"}`, `{"op":"field_has","side":..,"card":"ID"}`(스택 어디든 포함)
핵심은 **질문이 "네"가 되는 사건이 관측되는 조건**을 yes_if로 쓰는 것입니다(그 사건이 안 보이면 자동으로 「아니요」). 질문이 "~하지 않을 수 있는가"처럼 부정/생략을 묻는 경우는 선택 지정이 필요하므로 보통 unsupported(needs_choice)입니다.

## 예시 (손으로 만든 11개; 각 줄은 질문 요지 → 결과)
1) 「시큐리티가 0장일 때 BT23-031 【등장 시】 효과를 발휘할 수 있나」:
{"id":279,"status":"ok","reason":null,"note":"시큐리티 0장, 패의 BT23-031을 등장","job":{"id":"q279","you":{"memory":10,"hand":["BT23-031"],"security":[]},"opp":{},"steps":[{"do":"play","card":"BT23-031"}],"timeScale":20},"verdict":{"yes_if":{"all":[{"op":"log_has","re":"Effect:.*BT23-031"}]}}}
2) 「BT22-074 【메인】은 소멸시킬 상대 디지몬이 없어도 발휘할 수 있나」:
{"id":715,"status":"ok","reason":null,"note":"상대 필드 없음에서 메인 효과 발휘","job":{"id":"q715","you":{"memory":10,"field":[{"cards":["BT22-074"]}]},"opp":{},"steps":[{"do":"activate","frame":0,"skill":0}],"timeScale":20},"verdict":{"yes_if":{"all":[{"op":"log_has","re":"Effect:.*BT22-074"}]}}}
3) 「BT22-074 【메인】으로 상대 디지몬을 소멸시켰을 때도 이후 어택할 수 있나」(상대 Lv4 디지몬 BT23-018을 대상으로 둠): 판정은 소멸 로그가 있고 어택 선택이 열리는(이후 로그에 Attack 혹은 장치가 선택 대기) 것으로 하되, 어택 로그가 안 남는 경우도 있어 이런 문항은 note에 불확실성을 적으세요.
4) 「BT23-008 진화원이 디지타마뿐일 때 【메인】을 발휘할 수 있나」: field [{"cards":["BT23-008","BT21-004"]}] (BT21-004는 디지타마), activate frame 0 → yes_if log_has `Effect:.*BT23-008`.
5) 「BT24-041 【등장 시】로 패의 카드를 등장시키지 않은 경우에도 상대 디지몬을 퇴화시키나」: 패에 Iliad 없이 BT24-041 등장, 상대 필드에 2장 스택 디지몬 → yes_if log_has `De-Digivolve`.
6) 「BT22-074 【메인】은 코스트를 1만 지불할 수 있나」처럼 메모리 지불 문항은 최종 메모리가 부호가 바뀌어 위험하므로 보통 unsupported(other) 또는 효과가 정상 발휘되는지로 대체해 note에 적으세요.
7) 「어택하지 않을 수 있나」 「선택하지 않을 수 있나」 계열: unsupported(needs_choice).
8) 「상대의 턴 중 ~」 「메인 페이즈 시작 시」 「턴 종료 시」: unsupported(opp_turn).

## 작업 방식
- 입력은 `inputs/batchNN.json`(항목: id, card, effect, question, card_info[질문 카드 본문 요약]). 항목마다 필요하면 lookup.py로 질문에 나온 다른 카드(「ID 이름」)나 보조 카드를 조회해 실제 ID를 쓰세요.
- 각 항목에 대해 1) 질문이 묻는 사건을 한 문장으로 정리 2) 재현 가능한지 판단 3) 가능하면 job+verdict 작성.
- 결과는 `out/batchNN.json`(항목 배열)로 `Write` 하세요. JSON 문법이 맞아야 합니다. 마친 뒤 `python -X utf8 q2s_validate.py out/batchNN.json` 을 실행해 오류가 없을 때까지 고치세요(검증은 문법·DCGO 카드 존재·스키마만 확인하며 정답과는 무관).
- 20개가 넘는 시간을 쓰지 말고 항목당 간결하게. 확신이 낮으면 unsupported로 내세요(오답 시나리오보다 낫습니다).
