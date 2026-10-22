# 디지몬 카드 판정 도우미 서버

AI 판정 없이 공식 Q&A, 종합 룰, 심판이 확인한 판정만으로 답하는 판정 도우미입니다. 이 서버가 페이지와 API를 함께 제공합니다. 어느 PC나 서버에서든 아래 순서대로 똑같이 띄울 수 있습니다.

## 1. 설치 (한 번만)

```bash
git clone https://github.com/Marhnie/digimon-card-effects.git
cd digimon-card-effects
python -m venv .venv
. .venv/bin/activate                     # Windows: .venv\Scripts\activate
pip install torch --index-url https://download.pytorch.org/whl/cpu
pip install -r server/requirements.txt
python server/setup.py
```

`setup.py`가 하는 일:
1. 필요한 패키지가 설치돼 있는지 확인합니다.
2. 검색 모델(약 390MB)을 [GitHub 릴리스 retriever-cpu-v1](https://github.com/Marhnie/digimon-card-effects/releases/tag/retriever-cpu-v1)에서 내려받아 `train/runs/retriever_cpu/model`에 풉니다. sha256으로 파일이 맞는지 검사합니다.
   - 두 번째 검색 모델(설명이 부족한 질문용, 약 400MB)도 [retriever-cpu-vague-v1](https://github.com/Marhnie/digimon-card-effects/releases/tag/retriever-cpu-vague-v1)에서 내려받아 `train/runs/retriever_cpu_vague/model`에 풉니다. 메모리가 부족하면 `python server/setup.py --no-model2`로 건너뛰세요. 없으면 서버는 모델 하나로 돌아갑니다.
3. 페이지를 빌드합니다(`build_v3.py --server` → `server/static/index.html`).
4. 처음이면 심판 키를 만들어 `server/judges.json`에 저장하고 화면에 보여 줍니다.

GPU는 필요 없습니다. 검색 한 번에 CPU로 0.05초 안팎입니다.

## 2. 실행

| 환경 | 명령 |
|---|---|
| 한 번만 실행 | `python server/app.py` → http://127.0.0.1:8787 |
| 같은 네트워크의 다른 기기에서도 접속 | `HOST=0.0.0.0 python server/app.py` (Windows: `set HOST=0.0.0.0` 후 실행) |
| 꺼지면 자동 재시작 (Linux·macOS) | `sh server/run_server.sh` |
| 꺼지면 자동 재시작 (Windows) | `server\run_server.cmd` |
| Windows에서 로그인할 때 자동 시작 + 인터넷 공개 | `server\run_server_hidden.vbs`를 시작프로그램 폴더(`shell:startup`)에서 실행되게 등록합니다. 서버, 터널, 공개 주소 감시를 창 없이 띄웁니다 |
| Docker | `docker build -f server/Dockerfile -t judge-helper .` 후 `docker run -p 8787:8787 -v judge-data:/app/server/data judge-helper` |

처음 켤 때는 공식 Q&A 5,294개의 벡터를 계산하느라 CPU로 몇 분 걸립니다. 그다음부터는 캐시를 씁니다. 준비가 됐는지는 `/health`의 `"semantic": true`로 확인합니다.

## 3. 인터넷 공개 (선택)

- **임시 주소:** `cloudflared tunnel --url http://127.0.0.1:8787` 하나면 됩니다. `https://….trycloudflare.com` 주소가 나오는데, 다시 켤 때마다 바뀝니다. Windows용 `run_tunnel.cmd`와 `watch_tunnel.ps1`은 현재 주소를 `server/public_url.txt`에 적어 둡니다.
- **고정 주소:** Cloudflare 계정과 도메인으로 이름 있는 터널을 만들거나, 리버스 프록시(nginx 등)를 씁니다.

## 4. 심판(운영자)

- **심판 키:** `server/judges.json`(`{"키": "이름"}`)에 있습니다. 공개 저장소에 올라가지 않게 git에서 제외해 두었습니다. 사람마다 키를 따로 추가하세요.
- **로그인:** 페이지 아래 「심판 로그인」에 키를 넣으면 판정 확인·저장, 「받은 판정 코드 가져오기」의 「받은 제보 불러오기」, 「판정 현황」을 쓸 수 있습니다.
- **데이터:** 확인 판정과 이용자 제보는 `server/judge.db`(SQLite)에 쌓입니다. 백업할 때는 이 파일과 judges.json만 복사하면 됩니다. Docker에서는 `JUDGE_DATA` 경로(볼륨)에 저장됩니다.

## 5. API

| 경로 | 설명 |
|---|---|
| `POST /api/search {"q","k"}` | 의미가 가까운 공식 Q&A 인덱스를 돌려줍니다. 검색 모델 코사인(두 번째 모델이 있으면 그것도)과 2-gram을 RRF로 합칩니다(qfuse.py). 판정은 하지 않습니다 |
| `GET /api/rulings` | 확인 판정 목록(누구나) |
| `POST /api/rulings` | 확인 판정 저장(헤더 `X-Judge-Key` 필요) |
| `POST /api/reports` | 이용자 제보(누구나, 5초 간격 제한) |
| `GET /api/reports` | 제보 검토(심판) |
| `GET /api/whoami`, `GET /health` | 키 확인, 상태 확인 |

## 6. 데이터를 갱신할 때

카드나 Q&A가 바뀌어 `test_data4.json`을 다시 만들었다면 `python build_v3.py --server`로 페이지를 다시 빌드하고 서버를 재시작합니다. 벡터 캐시는 Q&A 수가 바뀌면 자동으로 다시 계산됩니다. 연구 과정은 `paper/01_연구기록.md` E30~E34에 있습니다.
