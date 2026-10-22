"""One-time setup for the judge-helper server on any machine (E34).

  python server/setup.py          # download the retriever models (GitHub releases), build the page, create a judge key
  python server/setup.py --no-model2   # skip the second (vague-question) retriever: less memory, slightly weaker on vague questions
Then:  python server/app.py       # http://127.0.0.1:8787   (HOST=0.0.0.0 to listen on the LAN)
"""
import hashlib, json, os, subprocess, sys, urllib.request, zipfile

HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
MODEL_DIR = os.path.join(ROOT, 'train', 'runs', 'retriever_cpu', 'model')
URL = 'https://github.com/Marhnie/digimon-card-effects/releases/download/retriever-cpu-v1/retriever_cpu_model.zip'
SHA = 'F26EC77CCBAC1D37F2DE2D239EC8523A0360EFD5F5E574E1FDEE4CCE7B4614E4'
# E38: second retriever (vague questions), fused in by RRF — optional; the server runs without it
MODEL2_DIR = os.path.join(ROOT, 'train', 'runs', 'retriever_cpu_vague', 'model')
URL2 = 'https://github.com/Marhnie/digimon-card-effects/releases/download/retriever-cpu-vague-v1/retriever_cpu_vague_model.zip'
SHA2 = 'CB4798931B6EE9F452E18F9BFD9FB532363AEE592DF8FE1FDD7E32E7563E2A81'


def step(msg): print('==', msg, flush=True)


step('git hooks (public repo: commits must use a noreply e-mail)')
try:
    subprocess.run(['git', 'config', 'core.hooksPath', '.githooks'], cwd=ROOT, check=True)
    em = subprocess.run(['git', 'config', 'user.email'], cwd=ROOT, capture_output=True, text=True).stdout.strip()
    if em and not em.endswith('@users.noreply.github.com'):
        print('!! 이 저장소의 커밋 이메일이 noreply가 아닙니다. 커밋하려면:  git config user.email "<id>+<name>@users.noreply.github.com"')
except Exception as e:
    print('git hook setup skipped:', e)

step('python packages')
missing = []
for mod in ('fastapi', 'uvicorn', 'numpy', 'sentence_transformers', 'torch'):
    try: __import__(mod)
    except ImportError: missing.append(mod)
if missing:
    print('missing:', ', '.join(missing))
    print('install:  pip install -r server/requirements.txt   (CPU torch: pip install torch --index-url https://download.pytorch.org/whl/cpu)')
    sys.exit(1)

def fetch_model(name, model_dir, url, sha):
    step(name)
    if os.path.exists(os.path.join(model_dir, 'model.safetensors')):
        print('already present:', model_dir); return
    os.makedirs(model_dir, exist_ok=True)
    zp = os.path.dirname(model_dir) + '_model.zip'
    if not os.path.exists(zp):
        print('downloading', url, '(~400 MB)')
        def hook(n, bs, total):
            if total > 0 and n % 400 == 0: print(f'  {min(100, n * bs * 100 // total)}%', flush=True)
        urllib.request.urlretrieve(url, zp, hook)
    h = hashlib.sha256()
    with open(zp, 'rb') as f:
        for b in iter(lambda: f.read(1 << 20), b''): h.update(b)
    if h.hexdigest().upper() != sha:
        os.remove(zp); sys.exit('checksum mismatch — download again')
    with zipfile.ZipFile(zp) as z: z.extractall(model_dir)
    os.remove(zp); print('extracted to', model_dir)


fetch_model('retriever model', MODEL_DIR, URL, SHA)
if '--no-model2' in sys.argv:
    print('second retriever skipped (--no-model2)')
else:
    fetch_model('second retriever (vague questions, optional: --no-model2 to skip)', MODEL2_DIR, URL2, SHA2)

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
