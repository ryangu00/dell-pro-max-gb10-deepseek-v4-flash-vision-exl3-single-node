#!/usr/bin/env bash
# Check health, model metadata, text, image and an essay through one base URL.
set -euo pipefail
B=${1:?Usage: ve-validate.sh BASE_URL MODEL IMAGE_FILE [OUT_DIR]}
M=${2:?Model required}
IMAGE=${3:?Image file required}
OUT=${4:-results}
mkdir -p "$OUT"
curl -fsS --max-time 5 "$B/health" >/dev/null
echo 'health OK'
python3 - "$B" "$M" "$IMAGE" "$OUT" <<'PY'
import base64,json,pathlib,sys,time,urllib.request
base, model, image, out = sys.argv[1:]
with urllib.request.urlopen(base+'/v1/models',timeout=5) as r:
    models=json.load(r)['data']
assert any(m['id']==model and m.get('max_model_len')==256000 for m in models), models
print('models OK: max_model_len=256000')
def chat(content, max_tokens):
    body={'model':model,'messages':[{'role':'user','content':content}],
          'max_tokens':max_tokens,'temperature':0.0,'chat_template_kwargs':{'thinking':False}}
    t0=time.monotonic()
    req=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=900) as r:
        d=json.load(r)
    d['_wall']=time.monotonic()-t0
    if not d['choices'][0]['message']['content'].strip():
        raise ValueError('empty response')
    return d
text=chat('Explain in one sentence what 3 to the 5th power is.',200)
print('text:',repr(text['choices'][0]['message']['content'][:120]))
encoded=base64.b64encode(pathlib.Path(image).read_bytes()).decode()
vision=chat([{'type':'text','text':'Describe this image in two sentences. What text, if any, is visible?'},
             {'type':'image_url','image_url':{'url':'data:image/png;base64,'+encoded}}],300)
print('vision:',repr(vision['choices'][0]['message']['content'][:300]))
(pathlib.Path(out)/'vision-probe.json').write_text(json.dumps(vision,indent=2)+'\n')
d=chat('Write a 400-word essay about tides.',500)
ct=d['usage']['completion_tokens']
print('throughput: completion',ct,'wall',round(d['_wall'],2),'s',round(ct/max(d['_wall'],0.01),1),'tok/s (incl. prefill)')
print('VALIDATION_DONE; inspect text and image answers for correctness')
PY
