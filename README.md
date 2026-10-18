# 디지몬 카드게임 카드 효과 구조·판정 근거 네트워크

디지몬 카드게임 한국어판의 카드 효과를 **종합 룰 15장(효과)의 구조**대로 분해하고, 카드 Q&A·룰 조항과 연결해 판정 근거를 찾는 연구 코드와 데이터입니다.

- 효과 분해: 출처 → 분류 4종(15-8: 기동형·유발형·즉시형·상재형) → 타이밍/아이콘(15-14·15-16) → 유발 조건(15-5) → 처리 조건(15-6) → 임의 처리 조건(15-7) → 처리 단계(대상·편·필터, 강제/임의, 단일/전체)
- Q&A 연결과 쟁점 그룹, 선례 기반 판정 + 선례가 없을 때 LLM 하이브리드
- 효과 하나하나를 노드로 한 네트워크(SNA): 구조 유사·같은 유발 조건·같은 처리·같은 Q&A 쟁점·같은 카드·이름 언급 링크, 강도 0~100, 2단 Louvain 클러스터

저장소: https://github.com/Marhnie/digimon-card-effects · 효과 네트워크 뷰어: https://claude.ai/artifact/Ajp5RDDZHM2uG7wiR1XrVg

연구 기록·방법 초안은 [`paper/`](paper/)에 있습니다(`01_연구기록.md`가 실험 이력).

## 실행 환경
Python 3.11 · scikit-learn · numpy · scipy · networkx · openpyxl · python-docx / Node 20+ (`npm install` — 뷰어 헤드리스 테스트용 jsdom)

## 재현 순서 (저장소 루트에서 실행)
1. 수집: `scrape_cards.py` · `scrape_qa.py` · `extract_rulebook.py` · `review_rule_refs.py` → `cards.json`, `qa.json`, `rules2.json`
2. 분할·태그: `parse_fx.py` (`trigger_fx.py` 사용) → 패턴 군집 `cluster_fx.py` → Q&A·조항 연결 `link_fx.py` → `units3.json`, `qa_items.json`
3. 룰북 구조 분해: `rule_struct.py` → `struct.json` → `struct_groups.py` → `struct2.json` → `export_struct.py` (엑셀, `out/`)
4. Q&A 쟁점 그룹: `qa_group.py` → `qa_labels_*.npy`
5. 효과 네트워크: `effect_sna2.py` (해상도 `RES_F`·`RES_C` 환경 변수, `ONLY_GRAPH=1`이면 그래프만 `net/G.pkl`) → `net/effect_sna.json`, GEXF
   - 클러스터 검증: `cluster_check.py fine` / `cluster_check.py coarse <RES_F>`
   - 뷰어: `patch_viewer.py` → `sna_template2.html`, `__DATA__`에 `net/effect_sna.json`을 넣어 `effect-sna.html`
6. 판정 도우미 뷰어: `build_v4data.py`(→ test_data4.json, 룰북 구조·클러스터) → `build_v3.py` → `card-effect-test.html`
7. 평가: `eval_build.py`·`eval_score.py`(LLM 비교), `ml_yesno.py`, `q_intent.py`·`q_slots.py`·`form_accuracy.py`·`hybrid_est.py`, `sim_est_eval.py`·`grp_eval.py`
8. 테스트: `node tests/t11.js`(판정 도우미), `node tests/tsna.js effect-sna.html`, `node tests/trev.js effect-review.html`

## 데이터 출처와 권리
- 카드 텍스트·카드 Q&A: 디지몬 카드게임 한국 공식 사이트(digimoncard.co.kr) 공개 자료. 카드 텍스트와 게임 자료의 권리는 ©BANDAI 및 각 권리자에게 있습니다.
- 종합 룰: 공식 사이트에 공개된 한국어 종합 룰.
- 연구·분석 목적의 사본이며, 원 자료의 재배포 권리를 주장하지 않습니다.

## GPU 학습
Claude 없는 판정 모델 학습 데이터·스크립트는 [train/README.md](train/README.md)를 보세요.
