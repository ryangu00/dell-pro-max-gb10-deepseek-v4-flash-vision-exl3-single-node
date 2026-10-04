#!/usr/bin/env python3
"""Run a script with synthetic HTTP responses in memory; never open a socket."""
import argparse
import http.client
import io
import os
from pathlib import Path
import runpy
import sys
import time
import urllib.error
import urllib.request
from unittest import mock
from urllib.parse import urlsplit

sys.path.insert(0,str(Path(__file__).resolve().parent))
from server import handler


class MemorySocket:
    def __init__(self,data): self.input=io.BytesIO(data); self.output=io.BytesIO()
    def makefile(self,*args): return self.input
    def sendall(self,data): self.output.write(data)


class Response(io.BytesIO):
    def __init__(self,body,status,headers,mode,delay,timeout):
        super().__init__(body); self.status=status; self.headers=headers
        self.mode,self.delay,self.timeout=mode,delay,timeout
    def __next__(self):
        if self.mode=='silent':
            time.sleep(min(self.timeout or 0.01,0.01)); raise TimeoutError('synthetic socket read timeout')
        if self.delay:time.sleep(self.delay)
        line=self.readline()
        if not line:raise StopIteration
        return line


def transport(root,mode='normal',delay=0.002):
    def urlopen(request,timeout=None,**kwargs):
        request=urllib.request.Request(request) if isinstance(request,str) else request
        parsed=urlsplit(request.full_url)
        if parsed.hostname not in ('127.0.0.1','localhost'):
            raise ValueError('offline transport accepts loopback fixture URLs only')
        body=request.data or b''
        headers=dict(request.header_items()); headers['Host']=parsed.netloc; headers['Content-Length']=str(len(body))
        raw=(request.get_method()+' '+parsed.path+' HTTP/1.0\r\n'+''.join(k+': '+v+'\r\n' for k,v in headers.items())+'\r\n').encode()+body
        sock=MemorySocket(raw)
        is_stream=request.get_method()=='POST' and b'"stream": true' in body
        actual_mode='normal' if mode=='silent' else mode
        handler(root,actual_mode,delay=0)(sock,('127.0.0.1',0),None)
        result=http.client.HTTPResponse(MemorySocket(sock.output.getvalue())); result.begin()
        payload=result.read(); status=result.status; response_headers=result.headers; result.close()
        if status>=400: raise urllib.error.HTTPError(request.full_url,status,'synthetic response',response_headers,io.BytesIO(payload))
        return Response(payload,status,response_headers,mode if is_stream else 'normal',delay if is_stream else 0,timeout)
    return urlopen


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('root',type=Path); ap.add_argument('script',type=Path); ap.add_argument('arguments',nargs=argparse.REMAINDER)
    a=ap.parse_args()
    sys.argv=[str(a.script),*a.arguments]
    with mock.patch.object(urllib.request,'urlopen',side_effect=transport(a.root,os.environ.get('OFFLINE_MODE','normal'),float(os.environ.get('OFFLINE_DELAY','0.002')))):
        runpy.run_path(str(a.script),run_name='__main__')


if __name__=='__main__':main()
