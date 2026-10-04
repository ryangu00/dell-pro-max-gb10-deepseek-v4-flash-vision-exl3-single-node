#!/usr/bin/env python3
"""Streaming stress rounds with socket silence detection and usage-based rates."""
import argparse
import json
import subprocess
import threading
import time
import urllib.error
import urllib.request
from pathlib import Path

PROMPTS = [
    'Write a complete, production-grade design document for a distributed job scheduler (leader election, at-least-once delivery, backpressure, retries, observability). Every section must be fully written out, no placeholders, no summaries. Then write the full Python implementation with tests.',
    'Prove rigorously that every bounded monotone sequence of real numbers converges, then prove the Bolzano-Weierstrass theorem, then the Heine-Borel theorem, stating and proving every lemma you use from the axioms of the reals. Be exhaustive and check every step twice in writing.',
    'Implement a single-file interpreter for a small Lisp in Rust (reader, evaluator, tail calls, closures, macros, error reporting) with an extensive test suite and a long walkthrough explaining every design decision line by line.',
    'Write a 20-chapter technical book outline on GPU memory hierarchies, then write the full text of chapters 1 through 6 with worked examples and exercises with solutions. Do not stop early; do not summarize.',
]


def mem_avail_gib():
    try:
        with open('/proc/meminfo') as stream:
            for line in stream:
                if line.startswith('MemAvailable:'):
                    return round(int(line.split()[1])/1048576,1)
    except OSError:
        pass
    return None


def env_state(health_url, container=None):
    try:
        with urllib.request.urlopen(health_url,timeout=10) as response:
            health=response.status
    except Exception as exc:
        health=type(exc).__name__
    status='not_checked'
    if container:
        try:
            result=subprocess.run(['docker','ps','--format','{{.Names}} {{.Status}}'],capture_output=True,text=True,timeout=20)
            status=next((line for line in result.stdout.splitlines() if line.split(maxsplit=1)[0]==container),'MISSING')
        except Exception as exc:
            status=type(exc).__name__
    return {'health':health,'container':status,'mem_avail_gib':mem_avail_gib()}


def dead(state):
    c=state['container']
    return state['health']!=200 or (c!='not_checked' and ('unhealthy' in c or 'healthy' not in c))


def one_stream(base,model,effort,prompt,max_tokens,stall_s,timeout_s,rec):
    body={'model':model,'stream':True,'max_tokens':max_tokens,'temperature':0.6,
          'messages':[{'role':'user','content':prompt}],'stream_options':{'include_usage':True}}
    if effort:
        body['chat_template_kwargs']={'thinking':True,'reasoning_effort':effort}
    request=urllib.request.Request(base+'/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json'})
    t0=time.monotonic()
    rec.update(deltas=0,reasoning_chars=0,content_chars=0,ttft=None,first_content=None,
               last_delta=None,finish=None,usage=None,status=None,stall=False)
    try:
        with urllib.request.urlopen(request,timeout=stall_s) as response:
            rec['status']=response.status
            for raw in response:
                line=raw.decode(errors='replace').strip()
                if not line.startswith('data:'): continue
                payload=line[5:].strip()
                if payload=='[DONE]': break
                data=json.loads(payload); now=time.monotonic()
                if data.get('usage'): rec['usage']=data['usage']
                for choice in data.get('choices') or []:
                    delta=choice.get('delta') or {}
                    reasoning=delta.get('reasoning_content') or delta.get('reasoning') or ''
                    content=delta.get('content') or ''
                    if reasoning or content:
                        rec['deltas']+=1; rec['last_delta']=now
                        if rec['ttft'] is None: rec['ttft']=round(now-t0,2)
                        if content and rec['first_content'] is None: rec['first_content']=round(now-t0,2)
                        rec['reasoning_chars']+=len(reasoning); rec['content_chars']+=len(content)
                    if choice.get('finish_reason'): rec['finish']=choice['finish_reason']
                if now-t0>timeout_s:
                    rec['finish']='client_timeout'; break
    except urllib.error.HTTPError as exc:
        rec['status']=exc.code; rec['err']=type(exc).__name__
    except TimeoutError as exc:
        rec['stall']=True; rec['err']=type(exc).__name__
    except Exception as exc:
        rec['err']=type(exc).__name__
    rec['wall']=round(time.monotonic()-t0,1)
    rec['gen_tokens']=(rec['usage'] or {}).get('completion_tokens')
    rec['tok_s']=round(rec['gen_tokens']/rec['wall'],1) if rec['gen_tokens'] is not None and rec['wall'] else None


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--rounds',required=True,help='Comma-separated port[h]:concurrency; h requests high effort')
    ap.add_argument('--host',default='127.0.0.1')
    ap.add_argument('--model',default='deepseek-v4-flash-vision-exp')
    ap.add_argument('--health-url',default='http://127.0.0.1:8888/health')
    ap.add_argument('--container',help='Optional local Docker health check')
    ap.add_argument('--max-tokens',type=int,default=32768)
    ap.add_argument('--stall',type=float,default=180)
    ap.add_argument('--timeout',type=float,default=1700)
    ap.add_argument('--heartbeat',type=float,default=120)
    ap.add_argument('--out',type=Path,default=Path('results/stress'))
    a=ap.parse_args(); a.out.mkdir(parents=True,exist_ok=True); failed=False
    with (a.out/'streams.jsonl').open('a') as log:
        for spec in a.rounds.split(','):
            port,count=spec.split(':'); count=int(count)
            effort='high' if port.endswith('h') else None
            base=f'http://{a.host}:{int(port.rstrip("h"))}'
            pre=env_state(a.health_url,a.container)
            print('ROUND_START',spec,json.dumps(pre),flush=True)
            if dead(pre): failed=True; break
            records=[{'round':spec,'i':i,'effort':effort or 'server-default'} for i in range(count)]
            threads=[threading.Thread(target=one_stream,args=(base,a.model,effort,PROMPTS[i%len(PROMPTS)],a.max_tokens,a.stall,a.timeout,records[i])) for i in range(count)]
            t0=time.monotonic(); next_heartbeat=t0+a.heartbeat
            for thread in threads: thread.start()
            while any(thread.is_alive() for thread in threads):
                for thread in threads: thread.join(timeout=min(a.heartbeat/count,1))
                now=time.monotonic()
                if now>=next_heartbeat and any(thread.is_alive() for thread in threads):
                    idle=[round(now-r['last_delta'],1) if r.get('last_delta') and not r.get('finish') else None for r in records]
                    print('HB',spec,'idle_s=',idle,'state=',env_state(a.health_url,a.container),flush=True)
                    next_heartbeat=now+a.heartbeat
            wall=time.monotonic()-t0
            for record in records: log.write(json.dumps(record)+'\n')
            log.flush()
            post=env_state(a.health_url,a.container)
            complete=all(r.get('usage') is not None for r in records)
            aggregate=sum(r['gen_tokens'] for r in records)/wall if complete and all(r['gen_tokens'] is not None for r in records) else None
            ok=all(r['status']==200 and not r['stall'] and r['finish'] in ('stop','length') for r in records)
            print('ROUND_END',spec,'wall=',round(wall,1),'aggregate_tok_s=',round(aggregate,1) if aggregate is not None else None,'usage_complete=',complete,'post=',json.dumps(post),flush=True)
            failed=failed or not ok or dead(post)
            if dead(post) or all(r['stall'] for r in records): break
    print('STRESS_DONE', 'incomplete_or_failed' if failed else 'completed')
    raise SystemExit(1 if failed else 0)


if __name__=='__main__': main()
