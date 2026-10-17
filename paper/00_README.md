# 논문 준비 폴더

카드게임 룰 판정 근거 탐색 — 룰북 구조 기반 효과 분해, Q&A 연결, 네트워크 분석, LLM 하이브리드 판정
(디지몬 카드게임 한국어판 사례)

| 파일·폴더 | 내용 |
|---|---|
| `01_연구기록.md` | 실험 이력 E1~E12 — 설정·수치·해석·결정, 남은 확인 항목 |
| `02_방법.md` | 방법 초안(데이터, 분할, 룰북 구조 분해, Q&A 연결, 판정 방식, 평가 프로토콜, 네트워크) |
| `03_데이터사전.md` | 데이터 파일과 필드 정의 |
| 저장소 루트 | 재현 스크립트와 데이터(2026-10-17 E15부터 작업 루트, 예전 `repro/` 스냅샷 대체) |
| `results/` | LLM 비교 시험 100문항(시험지·근거·채점), 네트워크(GEXF·JSON) |
| `figures/` | 논문 그림(작성 예정) |

## 실행 환경
Python 3.11.9 · scikit-learn 1.9.1 · numpy 2.4.6 · scipy 1.17.1 · networkx 3.6.1 · openpyxl 3.1.5 · python-docx 1.2.0
(Windows 11, CPU만 사용 — Intel i5-12400, RAM 16GB, GPU 없음)

## 재현 순서
스크립트는 저장소 루트(`card_effects`)에서 실행한다.
1. 수집: `scrape_cards.py`(카드 리스트) · `scrape_qa.py`(카드/규칙 해설 Q&A) · `extract_rulebook.py`(종합 룰 docx → 조항) · `review_rule_refs.py`(참조 번호 검증)
2. 분할·태그: `parse_fx.py`(→ units.json, 내부에서 `trigger_fx.py` 사용)
3. 패턴 군집: `cluster_fx.py`(→ units2.json, patterns.json)
4. Q&A·조항 연결: `link_fx.py`(→ units3.json, qa_items.json, general_by_rule.json)
5. **룰북 구조 분해**: `rule_struct.py`(→ struct.json) → `struct_groups.py`(→ struct2.json) → `export_struct.py`(엑셀)
6. Q&A 쟁점 그룹: `qa_group.py`(→ qa_labels_*.npy, 거리별 지표 출력)
7. 평가
   - LLM 비교: `eval_build.py` → (Claude 판정: results/llm_eval_100/*_out.json) → `eval_score.py`
   - LLM 없는 예측: `ml_yesno.py`(실행 예 `K=15 PW=4 python ml_yesno.py 0.92`)
   - 질문 규격화: `q_intent.py`, `q_slots.py`, `form_accuracy.py`, `hybrid_est.py`
   - 비슷한 질문 / 쟁점 그룹 배정: `sim_est_eval.py`, `grp_eval.py`
8. 네트워크: `effect_sna2.py`(효과 노드, 해상도 RES_F 1.6·RES_C 0.4) · `cluster_check.py`(해상도 검증), `effect_net.py`(요소·패턴), `qa_sna.py`(Q&A 네트워크·개인화 PageRank)

## 산출물(사용자용)
- 엑셀: `Downloads\카드효과_분류\카드효과_룰북구조_v4.xlsx` (현재 기준), v1~v3(이전 분류)
- 판정 도우미: https://claude.ai/artifact/SMx1gyAxdjjCMDFrZfi7ug
- 효과 노드 SNA: https://claude.ai/artifact/Ajp5RDDZHM2uG7wiR1XrVg
- 효과 요소·패턴 네트워크: https://claude.ai/artifact/FchxbX4PQt95QeZzrATWRU
- 종합 룰·Q&A 검색: https://claude.ai/artifact/GuewW7hVAeH4GoCHFZRkSE

## 논문 작성 시 주의
- 데이터는 공식 사이트 공개 자료와 자체 번역 룰북이다. 원문 인용 범위와 저작권 표기는 투고 전에 확인한다.
- 수치는 2026-10-17 데이터 스냅샷 기준이다. 데이터를 갱신하면 `01_연구기록.md`의 표를 다시 계산한다.
- LLM 판정은 하위 에이전트(웹 차단) 결과이다. 논문에는 모델·설정·프롬프트를 명시하고, 가능하면 API로 다시 측정한다.
