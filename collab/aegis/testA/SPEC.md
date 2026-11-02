# 질문 → Aegis 엔진 시나리오 변환 지침

디지몬 카드게임 네/아니요 Q&A를 Aegis 룰 엔진 시나리오로 바꿉니다. **공식 답은 받지 않았고 찾아서도 안 됩니다.** 목표는 엔진이 실제로 돌려서 답이 갈리도록 상황을 만드는 것입니다.

## 금지(누설 방지)
- `C:/Users/Daewonmedia/aegis_q2s` 밖은 lookup.py와 check.sh로만 접근합니다. card_effects* 폴더, 번역 파일, Downloads, 그리고 Aegis 저장소의 `*.test.ts`, conformance, docs, internal-docs는 열지도 grep하지도 마세요. 답이 들어 있을 수 있습니다.
- 답을 추측해 판정을 맞추지 마세요. 판정 조건은 실행 결과를 보기 전에 정하고, 실행은 거부된 단계나 잘못 차려진 보드를 고치는 데에만 씁니다.

## 도구 (작업 폴더 C:/Users/Daewonmedia/aegis_q2s)
- `python -X utf8 lookup.py BT26-014 Agumon` : 카드 영문 본문·레벨·진화 코스트·특징.
- 결과 파일 `out/batchNN.json`에 항목 배열을 쓰고 `bash check.sh NN` : 전체 실행, 항목별 단계 결과와 이벤트 로그 출력. 한 번에 약 20초입니다.

## 출력 항목
{"id":"입력 id 그대로","status":"ok"|"unsupported","reason":null|"needs_choice"|"multi_step"|"no_observable"|"other","unsure":true|false,"note":"한 줄 설명","job":{...},"verdict":{"yes_if":{"all":[...]}}}
- unsupported면 job·verdict는 생략합니다. 억지로 만들지 말고 unsupported로 두세요.
- 재현이 정확한지, 판정 조건이 질문을 정말 가르는지 조금이라도 의심되면 unsure:true입니다.
- yes_if는 {"all":[...]} 또는 {"any":[...]}입니다.

## job
{"you":{"memory":10,"hand":["ID"],"trash":["ID"],"security":["ID"],"field":[{"cards":["맨 위","그 아래 진화원",...],"suspended":false}]},
 "opp":{같은 구조, memory 없음},"steps":[...],"prefer":["ID"],"decline":false}
- 양쪽 덱에는 BT1-009가 12장 자동으로 깔립니다. you와 opp에 "deck":["ID",...]를 주면 그 카드들이 그 앞에 놓입니다(실행해서 어느 쪽이 덱 위인지 확인하세요).
- 시작은 you의 턴 메인 페이즈입니다.
- 행동 가능한 수단이 전혀 없으면 메인 페이즈가 자동 종료됩니다(그때 단계가 wrong-phase로 거부). 패에 사용할 카드나 필드 디지몬을 두세요.
- 진화는 규칙대로 검사합니다. 진화 코스트의 색·레벨(lookup의 evo)이나 본문의 [Digivolve] 조건에 맞는 카드를 frame에 두세요. 안 맞으면 invalid-evolution입니다.
- 시큐리티 0장인 쪽을 어택하면 게임이 끝납니다. 어택 시험에는 상대 시큐리티를 1장 이상 두세요.
- 선택은 자동입니다. 후보를 최대한 고르고, prefer에 적은 카드를 우선합니다. 「~할 수 있다」는 기본 발휘, "decline":true면 전부 거절합니다. 일부만 거절할 수는 없습니다.

## steps
{"do":"play","card":"ID"} / {"do":"digivolve","card":"패ID","frame":k} / {"do":"activate","frame":k,"skill":0} / {"do":"attack","frame":k,"target":-1} (-1은 플레이어, 0 이상은 상대 필드 번호) / {"do":"end_turn"} (턴을 넘김. 이후 단계는 턴 주인이 행동하고 frame도 그 사람 필드 기준이라 상대 턴도 재현할 수 있음)
- 코스트로 턴이 넘어가면 이후 단계는 거부됩니다. memory를 넉넉히 두세요.

## verdict 조건
- {"op":"log_has","re":"정규식"} / log_not : 로그는 check.sh 출력 형식입니다. Effect: <카드> seat<n> …, Play on field: <카드> seat<n>, Evolution: …, Attack …, Delete: <소멸 카드들> {...}, Moved: 출발->도착 {...}, securityChecked, battleCompared, deletionPrevented, effectHadNoEffect, GameOver. seat0이 you입니다.
- {"op":"field_count|hand_count|trash_count|security_count","side":"you|opp","cmp":"==|<|>|<=|>=","n":정수}
- {"op":"stack_size|dp","side":..,"idx":k,"cmp":..,"n":..}
- {"op":"hand_has|trash_has|field_has","side":..,"card":"ID"}
- {"op":"memory","cmp":..,"n":..} : 마지막 메모리(you 기준, check.sh의 mem). 코스트 감소를 볼 때 씁니다.
- {"op":"step_ok|step_rejected","i":단계번호} : 그 단계를 엔진이 받았는지/거부했는지. 「~할 수 있나요」를 직접 가를 때 씁니다.

yes_if가 참이면 네, 거짓이면 아니요입니다. 사건이 안 일어나서 아니요가 되는 판정은 시나리오 오류와 구별되지 않습니다. 대조가 될 사건(예: 효과 자체는 발동했다)을 note에 적고, 가능하면 함께 관측되게 구성하세요. 질문이 부정형이면 그 문장의 네/아니요 방향을 그대로 따릅니다.

## 끝나면
out/batchNN.json이 유효한 JSON이고 check.sh가 돌아가는지 확인한 뒤, 항목 수·ok·unsupported·unsure 수만 보고합니다.
