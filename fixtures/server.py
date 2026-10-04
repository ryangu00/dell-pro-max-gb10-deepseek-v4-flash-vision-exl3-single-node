#!/usr/bin/env python3
"""Loopback-only fixture server: strict byte ranges and synthetic chat responses."""
import argparse
import json
import re
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


def handler(root, mode='normal', delay=0.002):
    root=Path(root).resolve()
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,status,data,content_type='application/json',extra=None):
            self.send_response(status); self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(data)))
            for k,v in (extra or {}).items(): self.send_header(k,v)
            self.end_headers(); self.wfile.write(data)
        def do_GET(self):
            path=urlsplit(self.path).path
            if path=='/health': return self.send(200,b'{}')
            if path=='/v1/models':
                return self.send(200,json.dumps({'data':[{'id':'deepseek-v4-flash-vision-exp','max_model_len':256000}]}).encode())
            target=(root/unquote(path).lstrip('/')).resolve()
            if not target.is_relative_to(root) or not target.is_file(): return self.send(404,b'{}')
            blob=target.read_bytes(); match=re.fullmatch(r'bytes=(\d+)-(\d+)',self.headers.get('Range',''))
            if not match: return self.send(200,blob,'application/octet-stream')
            start,end=map(int,match.groups())
            if start>end or end>=len(blob): return self.send(416,b'{}')
            return self.send(206,blob[start:end+1],'application/octet-stream',{'Content-Range':f'bytes {start}-{end}/{len(blob)}'})
        def do_POST(self):
            body=json.loads(self.rfile.read(int(self.headers['Content-Length'])))
            content=body['messages'][0]['content']
            text=content if isinstance(content,str) else 'Synthetic image transport.'
            needle=re.search(r'secret access code is (\d+)',text)
            answer=needle.group(1) if needle else 'Synthetic answer: 3 to the 5th power is 243.'
            usage={'prompt_tokens':len(text.split()),'completion_tokens':30,'prompt_tokens_details':{'cached_tokens':0}}
            if not body.get('stream'):
                return self.send(200,json.dumps({'choices':[{'message':{'content':answer}}],'usage':usage}).encode())
            self.send_response(200); self.send_header('Content-Type','text/event-stream'); self.end_headers()
            try:
                if mode=='silent': time.sleep(0.2); return
                events=[{'choices':[{'delta':{'content':answer}}]}]
                if mode=='long': events*=30
                events += [{'choices':[{'delta':{},'finish_reason':'stop'}]}]
                if mode!='missing-usage': events += [{'choices':[],'usage':usage}]
                for event in events:
                    time.sleep(delay)
                    self.wfile.write(b'data: '+json.dumps(event).encode()+b'\n\n'); self.wfile.flush()
                self.wfile.write(b'data: [DONE]\n\n'); self.wfile.flush()
            except (BrokenPipeError,ConnectionResetError): pass
    return Handler


if __name__=='__main__':
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root',type=Path); ap.add_argument('--port',type=int,default=8888)
    ap.add_argument('--mode',choices=['normal','silent','long','missing-usage'],default='normal')
    a=ap.parse_args(); server=ThreadingHTTPServer(('127.0.0.1',a.port),handler(a.root,a.mode))
    print(f'SYNTHETIC_SERVER http://127.0.0.1:{server.server_port}',flush=True)
    try: server.serve_forever()
    except KeyboardInterrupt: pass
    finally: server.server_close()
