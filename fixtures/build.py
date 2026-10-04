#!/usr/bin/env python3
"""Build tiny synthetic fixtures. No model weights or benchmark answers are used."""
import argparse
import base64
import hashlib
import json
import struct
from pathlib import Path

NATIVE='8347bfb8776287ef2dcab2b46e9f15c655825c3a'
SHARDS=['model-00002-of-00011.safetensors','model-00010-of-00011.safetensors','model-00011-of-00011.safetensors']


def safetensors(path, tensors):
    header={}; payload=b''
    for name,value in tensors.items():
        start=len(payload); payload+=value
        header[name]={'dtype':'U8','shape':[len(value)],'data_offsets':[start,len(payload)]}
    raw=json.dumps(header,separators=(',',':')).encode()
    raw+=b' '*((-len(raw))%8)
    path.write_bytes(struct.pack('<Q',len(raw))+raw+payload)


def build(root):
    root=Path(root); root.mkdir(parents=True,exist_ok=True)
    donor=root/'donor'; donor.mkdir(exist_ok=True)
    native=root/'snapshots'/NATIVE; native.mkdir(parents=True,exist_ok=True)
    storage={}; weight_map={}
    for i,shard in enumerate(SHARDS):
        bias=f'mtp.{i}.ffn.gate.bias'; weight=f'mtp.{i}.ffn.weight'
        safetensors(donor/shard,{bias:bytes([i+1])*4,weight:bytes([i+2])*8})
        storage[weight]={'synthetic':'mixed'}
        weight_map[bias]='native.safetensors'; weight_map[weight]='native.safetensors'
        weight_map[f'{bias}_vl']='native.safetensors'
    namespace={'mtp':{'synthetic':True}}
    q={'tensor_storage':storage,'meta':{'ds4rt_inline_mixed_namespaces':namespace}}
    c={'num_nextn_predict_layers':1,'quantization_config':{'meta':{'ds4rt_inline_mixed_namespaces':namespace}}}
    for name,data in [('quantize_config.json',q),('config.json',c)]:
        (donor/name).write_text(json.dumps(data)+'\n')
    tensors={name:b'old' for name in weight_map}; tensors['target.weight']=b'target-unchanged'
    safetensors(native/'native.safetensors',tensors)
    weight_map['target.weight']='native.safetensors'
    (native/'model.safetensors.index.json').write_text(json.dumps({'weight_map':weight_map,'metadata':{'total_size':0}})+'\n')
    (native/'quantize_config.json').write_text(json.dumps({'tensor_storage':{'mtp.old':{},'target.weight':{'synthetic':'target'}},'meta':{}})+'\n')
    (native/'config.json').write_text(json.dumps({'num_nextn_predict_layers':3,'quantization_config':{'meta':{}}})+'\n')
    (native/'tokenizer.json').write_text('{}\n')
    assets=root/'assets'; assets.mkdir(exist_ok=True); files=[]
    for name,value in [('one.txt',b'one\n'),('two.txt',b'two\n')]:
        (assets/name).write_bytes(value)
        files.append({'name':name,'bytes':len(value),'sha256':hashlib.sha256(value).hexdigest()})
    (root/'manifest.json').write_text(json.dumps({'candidates':{'ve-k22-d2':{'files':files}}},indent=2)+'\n')
    # A synthetic blank PNG used only to exercise data-URL transport.
    (root/'image.png').write_bytes(base64.b64decode('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aF1cAAAAASUVORK5CYII='))
    cats=['c1-kbqa','c2-longctx','c4-code','c5-extract','c6-vision','c7-zhif','c9-long-coding','c10-sre-ops','c3-tool','c7-agentic-if','c8-judgment']
    # These scores exercise arithmetic only, not the historical mislabeled baseline.
    for label,runs in [('synthetic-reference',[90,90]),('vision',[80,90]),('control',[70,70])]:
        dest=root/'runs'/label; dest.mkdir(parents=True,exist_ok=True)
        (dest/'results.json').write_text(json.dumps({'synthetic':True,'purpose':'arithmetic only; no model or topology evidence','rows':[{'cat':cat,'runs':runs,'safety':0} for cat in cats]})+'\n')
    return native


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('directory',type=Path)
    print('SYNTHETIC_TARGET',build(parser.parse_args().directory))
