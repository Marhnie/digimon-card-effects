"""One-time setup for the judge-helper server on any machine (E34).

  python server/setup.py          # download the retriever model (GitHub release), build the page, create a judge key
Then:  python server/app.py       # http://127.0.0.1:8787   (HOST=0.0.0.0 to listen on the LAN)
"""
import hashlib, json, os, subprocess, sys, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MODEL_DIR = os.path.join(ROOT, 'train', 'runs', 'retriever_cpu', 'model')
URL = 'https://github.com/Marhnie/digimon-card-effects/releases/download/retriever-cpu-v1/retriever_cpu_model.zip'
SHA = 'F26EC77CCBAC1D37F2DE2D239EC8523A0360EFD5F5E574E1FDEE4CCE7B4614E4'


def step(msg): print('==', msg, flush=True)


step('python packages')
missing = []
for mod in ('fastapi', 'uvicorn', 'numpy', 'sentence_transformers', 'torch'):
    try: __import__(mod)
    except ImportError: missing.append(mod)
if missing:
    print('missing:', ', '.join(missing))
    print('install:  pip install -r server/requirements.txt   (CPU torch: pip install torch --index-url https://download.pytorch.org/whl/cpu)')
    sys.exit(1)

step('retriever model')
if os.path.exists(os.path.join(MODEL_DIR, 'model.safetensors')):
    print('already present:', MODEL_DIR)
else:
    os.makedirs(MODEL_DIR, exist_ok=True)
    zp = os.path.join(ROOT, 'train', 'runs', 'retriever_cpu_model.zip')
    if not os.path.exists(zp):
        print('downloading', URL, '(~390 MB)')
        def hook(n, bs, total):
            if total > 0 and n % 400 == 0: print(f'  {min(100, n * bs * 100 // total)}%', flush=True)
        urllib.request.urlretrieve(URL, zp, hook)
    h = hashlib.sha256()
    with open(zp, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    if h.hexdigest().upper() != SHA:
        os.remove(zp); sys.exit('checksum mismatch — download again')
    with zipfile.ZipFile(zp) as z: z.extractall(MODEL_DIR)
    os.remove(zp); print('extracted to', MODEL_DIR)

step('page (build_v3.py --server)')
subprocess.run([sys.executable, 'build_v3.py', '--server'], cwd=ROOT, check=True)

step('judge key')
jf = os.path.join(HERE, 'judges.json')
if not os.path.exists(jf):
    import secrets
    k = secrets.token_urlsafe(12); json.dump({k: '운영자'}, open(jf, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('created server/judges.json — first judge key:', k)
else:
    print('server/judges.json exists (keys kept)')
print('\ndone. run:  python server/app.py   → http://127.0.0.1:8787')
