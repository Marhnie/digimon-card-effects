# DCGO 헤드리스 시험 장치 메모 (2026-10-18, 코드 읽기만 함, 미실행)

DCGO2/DCGO (Unity 2021.3.45f2) 기준입니다. 경로는 `Assets/Scripts/Script/` 기준입니다.

## 실행 방식
- **오프라인 대전:** BattleScene을 네트워크 없이 직접 불러오면 봇 대전이 됩니다.
  - GManager.cs:254-265에서 `IsAI=true`가 켜집니다.
  - TurnStateMachine.cs:54-87에서 `PhotonNetwork.OfflineMode`가 켜집니다.
- **필요한 객체:** `ContinuousController`는 TurnStateMachine.Init에서 ContinuousControllerScene을 추가로 불러와 스스로 생깁니다.
- **카드 생성:**
  - `CardObjectController.CreateCardSource(playerId, CEntity_Base, isToken)`로 만듭니다.
  - 효과 클래스는 이름으로 찾아 붙입니다(리플렉션, CEntity_EffectController.cs:199).
- **영역 조작:**
  - Player의 `HandCards`, `TrashCards`, `SecurityCards`, `LibraryCards`를 직접 다룹니다.
  - 필드 카드는 `new Permanent(list)`를 만든 뒤 `CreateNewPermanent(perm, frameID)`로 놓습니다.
  - 메모리는 `SetFixedMemory`로 정합니다.
- **행동 실행:** `turnStateMachine.QueueMainPhaseAction(player, new PlayCardAction / ActivatePermanentAction / AttackPermanentAction)`로 넣습니다.
  - 진화는 이미 카드가 있는 frameID에 PlayCardAction을 넣으면 됩니다.
- **선택 응답:**
  - `player.QueuePlayerSelection(...)`에 미리 넣어 둡니다. 내 쪽(isYou) 선택은 봇이 대신 답하지 않습니다.
  - 상대 쪽 선택은 AI 봇이 답합니다. OptionalSkill은 90% 확률로 「예」를 고릅니다.
- **로그:** `PlayLog.OnAddLog`(정적 Action)에 연결합니다. 발휘된 효과마다 「Effect: 카드명(ID) "효과명"」이 기록됩니다.

## 걸림돌
- **UI 의존:** UI와 애니메이션 대기(isClose, commandText, WaitForSeconds, DOTween)가 곳곳에 있습니다.
  - 대책: `Time.timeScale`을 올리거나 `Time.captureDeltaTime`을 씁니다.
  - CC.Init이 targetFrameRate를 60으로 바꾸므로, 초기화 뒤에 다시 설정해야 합니다.
- **밴 리스트 요청:** 밴 리스트를 HTTP로 받아옵니다(ContinuousController.cs:570). 오프라인이면 지연되거나 실패합니다.
- **에디터 전용 코드:** 에디터에서는 `#if UNITY_EDITOR`로 봇의 어택이 꺼집니다(TurnStateMachine.cs:1061).
- **선택 대기 멈춤:** SelectCardEffect의 봇 처리는 후보 수가 maxCount보다 적으면 멈출 수 있습니다(SelectCardEffect.cs:650).

## 권장 구조
`com.unity.test-framework` 1.1.33이 이미 설치되어 있으니, PlayMode UnityTest로 만듭니다.

1. BattleScene을 불러옵니다.
2. `DoneStartGame`이 되고 메인 페이즈에 들어올 때까지 기다립니다.
3. 영역을 비우고 상황을 주입합니다.
4. 선택 응답을 미리 넣고 행동을 실행합니다.
5. `isExecuting`이 끝날 때까지 기다립니다.
6. 상태와 로그를 읽어 판정합니다.
