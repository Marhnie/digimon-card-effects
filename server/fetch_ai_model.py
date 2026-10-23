"""E52: install our own 「AI 의견」 model on the server PC — the LoRA adapter zip made by train/train_gen.py.

  python server/fetch_ai_model.py <url-or-local-zip> [sha256]
    url: e.g. https://github.com/Marhnie/digimon-card-effects/releases/download/gen-adapter-v1/gen_qwen2_5_1_5b_instruct_adapter.zip
  -> server/ai_local_model/ (adapter + tokenizer + gen_info.json). The base model (e.g. Qwen/Qwen2.5-1.5B-Instruct, ~3 GB) is
     downloaded from Hugging Face the first time the server answers an AI opinion, then cached.
  Then restart the server; GET /api/ai/usage shows backend "local".
"""
import hashlib, json, os, shutil, sys, tempfile, urllib.request, zipfile
HERE = os.path.dirname(os.path.abspath(__file__)); DEST = os.environ.get('AI_LOCAL_MODEL', os.path.join(HERE, 'ai_local_model'))
if len(sys.argv) < 2: sys.exit(__doc__)
src, want = sys.argv[1], (sys.argv[2].upper() if len(sys.argv) > 2 else None)
tmp = tempfile.mkdtemp()
zp = src if os.path.exists(src) else os.path.join(tmp, 'adapter.zip')
if zp != src:
    print('downloading', src); urllib.request.urlretrieve(src, zp)
h = hashlib.sha256(open(zp, 'rb').read()).hexdigest().upper()
if want and h != want: sys.exit(f'checksum mismatch: {h} != {want}')
print('sha256', h, '(matches)' if want else '(not checked — pass the sha256 to verify)')
out = os.path.join(tmp, 'x')
with zipfile.ZipFile(zp) as z:
    for n in z.namelist():   # refuse paths that would leave the folder
        if n.startswith(('/', chr(92))) or '..' in n.replace(chr(92), '/').split('/'): sys.exit('unsafe path in zip: ' + n)
    z.extractall(out)
if not os.path.exists(os.path.join(out, 'adapter_config.json')): sys.exit('not an adapter zip (adapter_config.json missing)')
if os.path.exists(DEST):
    shutil.move(DEST, DEST + '.prev'); print('previous model kept at', DEST + '.prev')
shutil.move(out, DEST); shutil.rmtree(tmp, ignore_errors=True)
info = os.path.join(DEST, 'gen_info.json')
print('installed', DEST, json.load(open(info, encoding='utf-8')).get('base_model') if os.path.exists(info) else '')
print('next: restart the server (or the keeper restarts it), then GET /api/ai/usage -> backend "local"')
