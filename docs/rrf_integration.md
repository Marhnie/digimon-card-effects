# 서버 검색에 RRF 합치기 넣는 방법 (E31 후속)

근거: `paper/01_연구기록.md` E31 추가 2 — 구어체 @1 모델 0.816 → RRF 0.874, 최신 팩 손해 없음.
`server/app.py`는 허브 세션 파일이라 수정하지 않았습니다. 아래 변경이면 됩니다.

```python
# 상단
from qfuse import Fuser
FUSE = Fuser(QA, DOC)          # sys.path에 ROOT 필요: sys.path.insert(0, ROOT)

# /api/search 안, `s = SEM['E'] @ v; o = ...; return ...` 세 줄을 다음으로 교체
s = SEM['E'] @ v
return {'ready': True, 'hits': FUSE.hits(q, s, k * 3)}
```
- 응답의 `s`가 코사인에서 RRF 점수(약 0.01~0.033)로 바뀝니다. 페이지가 `s`를 코사인 문턱으로 쓴다면 `cos` 필드(원래 코사인)를 쓰도록 바꿔야 합니다. 순위만 쓴다면 그대로입니다.
- 모델이 안 켜졌을 때(503)의 후퇴는 지금처럼 브라우저 2-gram입니다.
