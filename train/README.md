# GPU 학습: Claude 없는 판정 모델

판정 도우미의 목표는 **Claude 없이, 확신할 때만 답하는 것**입니다. 이 폴더는 그 판정을 학습된 모델로 해 보기 위한 데이터와 스크립트입니다.

비교 기준(브라우저 엔진, E19·E25·E26)은 다음과 같습니다.

| 질문 | 지금 엔진 | 모델이 넘어야 할 것 |
|---|---|---|
| 네/아니요 (최신 팩 597) | 확신 0.8 이상에서 **48% @ 99%** | 같은 정확도에서 더 넓은 범위 |
| 설명형 (최신 팩 290) | 같은 질문의 공식 답변 재사용 **42% (117/118 일치)** | 같은 일치율에서 더 넓은 범위 |

## 1. 준비

```bash
git clone https://github.com/Marhnie/digimon-card-effects.git
cd digimon-card-effects
python -m venv .venv && source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cu124   # GPU의 CUDA 버전에 맞춰
pip install -r train/requirements.txt
python -c "import torch; print(torch.cuda.is_available(), torch.cuda.get_device_name(0))"
```

## 2. 데이터

`train/data/`에 이미 만들어 두었습니다. 다시 만들려면 다음을 실행합니다. 표준 라이브러리만 쓰고, 약 20초 걸립니다.

```bash
python train/export_dataset.py
```

**시간 분할**
- test: 최신 팩(BT22·BT23·BT24·EX9·EX10·ST21·ST22).
- train과 valid: 그 이전 팩. 카드 단위로 나눠서 valid의 10%는 train과 같은 카드가 없습니다.

**파일과 필드**

| 파일 | 내용 |
|---|---|
| `yesno_*.jsonl` | 네/아니요 질문. 필드: `question`, `effect`(한글 효과), `card_text_en`(DCGO 영문, 최신 팩 보충), `label`(1=네), `neighbours`(이전 팩의 비슷한 공식 Q&A K개와 정렬된 답) |
| `explain_*.jsonl` | 설명형 질문과 공식 답변(`answer`) |
| `engine_test.json` | 브라우저 엔진의 test 예측(비교용) |

**누설 방지:** `neighbours`에는 자기 자신이 들어가지 않습니다. 거의 같은 문항(Jaccard > 0.8)과 train 쪽 근거만 넣습니다.

## 3. 학습

**네/아니요 판정 (cross-encoder, 입력에 선례 포함)**

```bash
python train/train_yesno.py --model klue/roberta-large --epochs 4 --bs 16 --lr 1.5e-5        # 24GB GPU 기준
python train/train_yesno.py --model klue/roberta-large --bs 8 --grad_accum 2                 # 메모리가 작을 때
python train/train_yesno.py --model klue/roberta-base --max_len 384                          # 가볍게
python train/train_yesno.py --model klue/roberta-large --k 0 --name nok                      # 선례 없이(비교 실험)
```

**설명형 답변 검색 (bi-encoder)**

```bash
python train/train_explain.py --model jhgan/ko-sroberta-multitask --epochs 3 --bs 64
```

**CPU에서 동작만 확인 (몇 초)**

```bash
python train/train_yesno.py --tiny
python train/train_explain.py --tiny
```

## 4. 결과 보는 법

결과는 `train/runs/<이름>/metrics.json`에 저장됩니다.

**네/아니요 (`train_yesno.py`)**

| 항목 | 의미 |
|---|---|
| `test.cov@99` | 확신이 높은 순으로 답할 때 정확도 99%를 유지하며 답할 수 있는 비율. 엔진은 약 0.48 |
| `test_with_valid_threshold` | **valid에서 고른 문턱**을 test에 그대로 적용한 결과. 정직한 수치이니 이걸 보고하세요 |
| `vs_engine.union_*` | 엔진이 확신하거나 모델이 확신할 때 답한다고 볼 때의 범위와 정확도 |

**설명형 (`train_explain.py`)**

| 항목 | 의미 |
|---|---|
| `curve` | 코사인 문턱별 범위(`coverage`)와 공식 답변 일치율(`agree`) |

모델 가중치는 저장소에 올리지 않습니다(`.gitignore`). `metrics.json`, `test_pred.json`, `test_retrieval.json`만 커밋하면 결과를 공유할 수 있습니다.

```bash
git add train/runs && git commit -m "GPU 학습 결과: <모델>" && git push
```

## 5. 주의

- test(최신 팩)로 하이퍼파라미터를 고르지 마세요. 문턱과 에폭은 valid로 고릅니다.
- 학습된 모델도 「Claude 없이」라는 조건은 지킵니다. 다만 판정 도우미(브라우저)에 넣으려면 ONNX나 경량 모델로 바꾸거나 서버가 필요합니다. 그건 결과를 보고 정합니다.
- 데이터는 공식 Q&A·카드 텍스트(공개 정보)와 DCGO 카드 스크립트의 영문 텍스트(MIT)입니다. 검수자 개인 기록은 들어 있지 않습니다.

## 6. 검색 모델 (E31, 아직 실행하지 않음)

「네/아니요를 직접 판정」하는 대신 **같은 판정의 공식 Q&A를 찾는 검색**에 언어 모델을 씁니다(E27에서 직접 판정은 엔진보다 못했음).

```bash
python train/train_retriever.py --tiny                                                  # CPU 스모크(수 초, 영어 소형 모델이라 수치 무의미)
python train/train_retriever.py --model jhgan/ko-sroberta-multitask --epochs 3 --bs 64   # GTX 1660 SUPER 6GB 기준 bs 32~64
python train/train_retriever.py --norm ...                                               # qnorm 정규화를 질문·말뭉치에 적용
```

- 학습: 긍정 쌍(이유 묶음이 같고 답의 방향이 같음 / 묻는 것·상황·방향이 같고 공식 답이 비슷함) + 어려운 부정(문장은 비슷하고 답이 반대) 3중쌍, MultipleNegativesRankingLoss. 앵커는 확률 0.7로 구어체로 바꿉니다(`colloquialize`).
- 평가 세트 문항(`paper/results/colloquial_test.json`)과 최신 팩 Q&A 전체는 학습에서 제외합니다.
- 평가(`train/runs/retriever_<이름>/metrics.json`): `time_split`(최신 팩 공식 질문 → 이전 팩), `colloquial`(구어체 세트, 원문 제외). 각각 `model`, `browser_2gram`(지금 방식), 학습 전(`zero_shot`)과 후(`fine_tuned`)를 같은 질문·말뭉치에서 비교합니다. 이 모델이 의미 있으려면 구어체에서 `browser_2gram`을 넘어야 합니다.
- 주의: 시간 분할의 `browser_2gram`은 공식 문장 사이의 거의 같은 문항 때문에 높게 나옵니다(스모크에서 @1 0.87). 구어체 쪽이 실제 판단 기준입니다.

**작은 모델로 증류(계획만)**: 브라우저용 10MB 안팎이 목표입니다.
1. 학습된 ko-sroberta(110M)를 교사로, 말뭉치(5,308문항 + 구어체 증강 수만 개)의 임베딩을 정답으로 하여 학생(문자 2~3-gram 해시 임베딩 + 평균 풀링 + 작은 선형층, 또는 4층·256차원 Transformer)을 코사인/MSE 손실로 학습합니다.
2. 학생은 int8 양자화한 뒤 ONNX(onnxruntime-web, wasm)나 순수 JS 행렬곱으로 실행하고, 말뭉치 임베딩(5,308×256 int8 ≈ 1.3MB)은 미리 계산해 파일로 넣습니다. 질문 하나는 학생으로만 임베딩하면 됩니다.
3. 승인 기준: 구어체 세트 recall@3이 교사의 95% 이상, 모델 크기 15MB 이하. 아니면 서버 방식(고정 임베딩 API)으로 갑니다.

## 7. 검색 모델 증류 → 판정 도우미 (E33)

```bash
python train/distill_student.py --teacher train/runs/retriever_base/model                 # 평가(시간 분할, 정직한 수치)
python train/distill_student.py --teacher train/runs/retriever_base/model --final         # 평가 + 전체 Q&A로 다시 학습해 내보내기
python train/distill_student.py --tiny                                                    # CPU 스모크
node tests/tqemb.js train/export_qemb                                                     # JS 이식이 Python과 같은지(코사인 > 0.99)
```

- **학생 모델:** 문자 2·3-gram을 FNV-1a 해시(32,768칸)로 바꾼 뒤, 256차원 임베딩 평균 → 선형층(256→교사 차원) → 정규화합니다. 질문만 학생이 벡터로 바꾸고, 공식 Q&A 쪽은 교사 벡터를 int8로 미리 넣어 둡니다.
  - 크기: 학생 약 8.6MB + Q&A 벡터 약 4MB.
  - 브라우저에서는 `v3_qemb.js`로 돌립니다. 순수 JS이고 라이브러리가 필요 없습니다.
- **승인 기준:** 구어체 recall@3이 교사의 95% 이상이고, 내보낸 파일이 15MB 이하여야 합니다(`train/runs/distill/metrics.json`의 `approved`).
- **반영:** `train/export_qemb/`가 있으면 `build_v3.py`가 `window.__QEMB_BASE="qemb/"`를 켭니다. 배포할 때는 이 폴더의 파일을 아티팩트 `qemb/` 경로로 함께 올립니다.
  - 판정 도우미에서는 **질문 추천(「의미가 비슷한 공식 질문」)과 「의미 검색」 근거 탭에만** 씁니다. 판정에는 쓰지 않습니다.
