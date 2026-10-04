"""Offline contract tests. All numeric fixture values are synthetic, not measurements."""
import contextlib
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shlex
import struct
import subprocess
import sys
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from unittest import mock

ROOT=Path(__file__).resolve().parents[1]


def module(name,path):
    spec=importlib.util.spec_from_file_location(name,ROOT/path)
    value=importlib.util.module_from_spec(spec); spec.loader.exec_module(value); return value


fixtures=module('fixture_build','fixtures/build.py')
server_module=module('fixture_server','fixtures/server.py')
offline=module('offline_transport','fixtures/offline.py')
ACTIVE={}
graft=module('graft','scripts/graft0731.py')
verifier=module('verify','scripts/verify_graft_bytes.py')
suite=module('suite','scripts/suite.py')
stress=module('stress','scripts/ve_stress.py')
compare=module('compare','scripts/g2_compare.py')


@contextlib.contextmanager
def server(root,mode='normal',delay=0.002):
    """Exercise the HTTP handlers in memory; no socket binding or network access."""
    ACTIVE.update(root=str(root),mode=mode,delay=delay)
    try:
        with mock.patch.object(offline.urllib.request,'urlopen',side_effect=offline.transport(root,mode,delay)):
            yield 'http://127.0.0.1:8888'
    finally: ACTIVE.clear()


class OfflineTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='.offline-',dir=ROOT)
        self.addCleanup(self.temp.cleanup); self.work=Path(self.temp.name)
        self.native=fixtures.build(self.work)
        self.env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',NO_PROXY='127.0.0.1,localhost')
    def run_command(self,*args,ok=True,env=None):
        args=[str(a) for a in args]
        env=dict(env or self.env)
        if ACTIVE:
            env.update(OFFLINE_FIXTURE=ACTIVE['root'],OFFLINE_MODE=ACTIVE['mode'],OFFLINE_DELAY=str(ACTIVE['delay']))
            if args[0]==sys.executable and len(args)>1 and args[1].endswith('.py'):
                args=[sys.executable,str(ROOT/'fixtures/offline.py'),ACTIVE['root'],*args[1:]]
            bins=self.work/'offline-bin'; bins.mkdir(exist_ok=True)
            (bins/'curl').write_text('#!/bin/sh\nexit 0\n')
            wrapper='#!/bin/sh\nexec '+shlex.quote(sys.executable)+' '+shlex.quote(str(ROOT/'fixtures/offline.py'))+' "$OFFLINE_FIXTURE" "$@"\n'
            # Validation embeds Python on stdin, which runpy cannot address directly.
            wrapper='#!/bin/sh\nif [ "$1" = - ]; then\n  shift\n  exec '+shlex.quote(sys.executable)+' '+shlex.quote(str(ROOT/'fixtures/offline_stdin.py'))+' "$@"\nelse\n'+wrapper.split('\n',1)[1]+'fi\n'
            (bins/'python3').write_text(wrapper)
            for path in bins.iterdir():path.chmod(0o755)
            env['PATH']=str(bins)+os.pathsep+env['PATH']
        p=subprocess.run(args,cwd=ROOT,env=env,capture_output=True,text=True,timeout=20)
        if ok: self.assertEqual(p.returncode,0,p.stdout+p.stderr)
        else: self.assertNotEqual(p.returncode,0,p.stdout+p.stderr)
        return p
    def make_graft(self,base):
        return self.run_command(sys.executable,'scripts/graft0731.py','--target',self.native,'--source-base',base)
    def test_graft_complete_and_immutable_target(self):
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.native.iterdir()}
        with server(self.work/'donor') as base:
            dry=self.run_command(sys.executable,'scripts/graft0731.py','--dry-run','--target',self.native,'--source-base',base)
            self.assertIn('range requests 3',dry.stdout)
            dest=self.native.parent/graft.GREV; self.assertFalse(dest.exists())
            self.assertIn('GRAFT_DONE',self.make_graft(base).stdout)
            for flag in ['--all','--n']:
                args=[sys.executable,'scripts/verify_graft_bytes.py','--local',dest/graft.OUTNAME,'--source-base',base,flag]
                if flag=='--n': args+=['40']
                self.assertIn('mismatches=0',self.run_command(*args).stdout)
            self.run_command(sys.executable,'scripts/graft0731.py','--target',self.native,'--source-base',base,ok=False)
        self.assertEqual(before,{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in self.native.iterdir()})
        self.assertTrue((dest/'native.safetensors').is_symlink())
        self.assertFalse(os.path.isabs(os.readlink(dest/'native.safetensors')))
        index=json.loads((dest/'model.safetensors.index.json').read_text())
        self.assertTrue(all(f==graft.OUTNAME for k,f in index['weight_map'].items() if k.startswith('mtp.')))
        total=0
        for key,file in index['weight_map'].items():
            v=graft.local_header(dest/file)[key]; total+=v['data_offsets'][1]-v['data_offsets'][0]
        self.assertEqual(index['metadata']['total_size'],total)
        q=json.loads((dest/'quantize_config.json').read_text())
        self.assertNotIn('mtp.old',q['tensor_storage']); self.assertIn('target.weight',q['tensor_storage'])
        self.assertIn('mtp',q['meta']['ds4rt_inline_mixed_namespaces'])
        c=json.loads((dest/'config.json').read_text()); self.assertEqual(c['num_nextn_predict_layers'],1)
        self.assertIn('mtp',c['quantization_config']['meta']['ds4rt_inline_mixed_namespaces'])
    def test_corrupt_graft_is_rejected(self):
        with server(self.work/'donor') as base:
            self.make_graft(base); local=self.native.parent/graft.GREV/graft.OUTNAME
            data=bytearray(local.read_bytes()); data[-1]^=1; local.write_bytes(data)
            p=self.run_command(sys.executable,'scripts/verify_graft_bytes.py','--all','--local',local,'--source-base',base,ok=False)
            self.assertIn('MISMATCH bias_vl',p.stdout)
    def test_graft_retries_short_and_extra_payloads(self):
        for fault in ('short','extra'):
            work=self.work/fault; native=fixtures.build(work)
            g=module('retry_'+fault,'scripts/graft0731.py')
            source=offline.transport(work/'donor',delay=0); responses=[]; injected=[False]
            def open_fault(request,timeout=None):
                response=source(request,timeout=timeout)
                interval=request.get_header('Range') if not isinstance(request,str) else None
                if interval and int(interval.split('=')[1].split('-')[0])>8 and not injected[0]:
                    injected[0]=True
                    data=response.read(); headers=response.headers; response.close()
                    response=offline.Response(data[:-1] if fault=='short' else data+b'x',206,headers,'normal',0,timeout)
                    responses.append(response)
                return response
            with mock.patch.object(g.urllib.request,'urlopen',side_effect=open_fault),mock.patch.object(g.time,'sleep'),mock.patch.object(sys,'argv',['graft','--target',str(native),'--source-base','http://127.0.0.1:8888']),contextlib.redirect_stdout(io.StringIO()):g.main()
            self.assertTrue(injected[0]); self.assertTrue(all(r.closed for r in responses))
            with server(work/'donor') as base:
                result=self.run_command(sys.executable,'scripts/verify_graft_bytes.py','--all','--local',native.parent/g.GREV/g.OUTNAME,'--source-base',base)
                self.assertIn('mismatches=0',result.stdout)
    def test_graft_failed_payload_never_publishes(self):
        g=module('failed_graft','scripts/graft0731.py'); source=offline.transport(self.work/'donor',delay=0)
        def fail_payload(request,timeout=None):
            response=source(request,timeout=timeout); interval=request.get_header('Range') if not isinstance(request,str) else None
            if interval and int(interval.split('=')[1].split('-')[0])>8:
                headers=response.headers; response.close()
                return offline.Response(b'',206,headers,'normal',0,timeout)
            return response
        with mock.patch.object(g.urllib.request,'urlopen',side_effect=fail_payload),mock.patch.object(g.time,'sleep'),mock.patch.object(sys,'argv',['graft','--target',str(self.native),'--source-base','http://127.0.0.1:8888']),contextlib.redirect_stdout(io.StringIO()):
            with self.assertRaises(SystemExit):g.main()
        self.assertFalse((self.native.parent/g.GREV).exists())
    def test_invalid_revision_rejected_before_download(self):
        self.run_command(sys.executable,'scripts/graft0731.py','--new-revision','invalid',ok=False)
    def test_range_total_change_and_close(self):
        class Response(io.BytesIO):
            status=206
            def __init__(self,total): super().__init__(b'12345678'); self.headers={'Content-Range':f'bytes 0-7/{total}'}
        first,second=Response(30),Response(40); graft.TOTALS.clear()
        with mock.patch.object(graft.urllib.request,'urlopen',side_effect=[first,second]):
            graft.get('http://127.0.0.1/file',0,7).close()
            with self.assertRaises(OSError):graft.get('http://127.0.0.1/file',0,7)
        self.assertTrue(second.closed)
    def test_verifier_short_and_extra_range_body(self):
        class Response(io.BytesIO):
            status=206; headers={'Content-Range':'bytes 0-7/30'}
        for body in (b'x',b'123456789'):
            verifier.TOTALS.clear()
            with mock.patch.object(verifier.urllib.request,'urlopen',return_value=Response(body)):
                with self.assertRaises(SystemExit):verifier.rng('x',0,7)
    def test_assets_size_hash_and_sizes_only(self):
        args=[sys.executable,'scripts/verify-assets.py','ve-k22-d2',self.work/'assets','--manifest',self.work/'manifest.json']
        self.assertIn('PASS 2 files',self.run_command(*args).stdout)
        (self.work/'assets/one.txt').write_bytes(b'bad\n')
        self.assertIn('SHA256 mismatch',self.run_command(*args,ok=False).stderr)
        self.run_command(*args,'--sizes-only')
        (self.work/'assets/one.txt').write_bytes(b'x')
        self.assertIn('size mismatch',self.run_command(*args,'--sizes-only',ok=False).stderr)
    def test_layout_marker_and_reference_env(self):
        download=self.work/'download'; download.mkdir(); (download/'dummy').write_text('synthetic')
        (download/'.cache').mkdir(); log=self.work/'download.log'; log.write_text('incomplete\n')
        recipe=self.work/'recipe'; cache=self.work/'cache with spaces'
        args=['bash','scripts/ve-finalize-layout.sh',download,cache,recipe,log]
        self.run_command(*args,ok=False); self.assertTrue(download.exists())
        log.write_text('DL_EXIT=0\n'); self.run_command(*args)
        target=cache/'hub/models--wrldsuksgo2mars--DeepSeek-V4-Flash-Vision-Exp-EXL3-K2.2-D2-v1'
        self.assertEqual((target/'refs/main').read_text().strip(),fixtures.NATIVE)
        self.assertFalse((target/'snapshots'/fixtures.NATIVE/'.cache').exists())
        self.assertIn('MAX_MODEL_LEN=256000',(recipe/'.env').read_text())
        p=self.run_command('bash','-c','source "$1"; test -d "$HF_CACHE"','test',recipe/'.env')
        self.run_command(*args)
    def test_validation_and_model_metadata(self):
        with server(self.work) as base:
            p=self.run_command('bash','scripts/ve-validate.sh',base,'deepseek-v4-flash-vision-exp',self.work/'image.png',self.work/'output')
            self.assertIn('VALIDATION_DONE',p.stdout)
            self.run_command('bash','scripts/ve-validate.sh',base,'wrong-model',self.work/'image.png',self.work/'output',ok=False)
    def test_needle_and_shuffled_prompts(self):
        with server(self.work) as base:
            for shuffle in ([],['--shuffle']):
                p=self.run_command(sys.executable,'scripts/v3_1m_needle.py','--base',base,'--model','synthetic','--tokens','128','--out',self.work/'needle.jsonl',*shuffle)
                self.assertTrue(json.loads(p.stdout)['exact'])
        needle=module('needle','scripts/v3_1m_needle.py'); prompts=[]
        class Response(io.BytesIO): pass
        def post(base,key,body,timeout):
            text=body['messages'][0]['content']; prompts.append(text)
            import re
            code=re.search(r'secret access code is (\d+)',text).group(1)
            return Response(('data: '+json.dumps({'choices':[{'delta':{'content':code}}]})+'\n\ndata: [DONE]\n').encode())
        with mock.patch.object(needle,'post',side_effect=post),contextlib.redirect_stdout(io.StringIO()):
            for _ in range(2):
                with mock.patch.object(sys,'argv',['needle','--model','synthetic','--tokens','128','--shuffle','--out',str(self.work/'shuffle.jsonl')]):
                    with self.assertRaises(SystemExit) as result: needle.main()
                    self.assertEqual(result.exception.code,0)
        self.assertNotEqual(prompts[0],prompts[1])
    def test_needle_chain_dry_run(self):
        p=self.run_command('bash','scripts/run-ve-chain.sh','--dry-run')
        self.assertIn('--tokens 128000',p.stdout); self.assertIn('--tokens 245000',p.stdout)
        self.assertIn('--max-tokens 1500',p.stdout)
    def test_suite_streaming_and_replacement(self):
        with server(self.work) as base:
            for flags in ([],['--think','high']):
                p=self.run_command(sys.executable,'scripts/suite.py','--base',base,'--trials','3','--label','synthetic','--out',self.work/'suite.jsonl',*flags)
                self.assertIn('SUITE_DONE',p.stdout)
        records=[json.loads(l) for l in (self.work/'suite.jsonl').read_text().splitlines()]
        self.assertEqual(set(records[0]['summary']),set(suite.P))
        self.assertIn('think_synthetic',records[1]['summary'])
    def test_suite_usage_not_delta_and_median(self):
        lines=[b'data: {"choices":[{"delta":{"content":"batch"}}]}\n',b'data: {"usage":{"completion_tokens":30}}\n',b'data: [DONE]\n']
        with mock.patch.object(suite.urllib.request,'urlopen',return_value=io.BytesIO(b''.join(lines))),mock.patch.object(suite.time,'time',side_effect=[0,1,4]):
            self.assertEqual(suite.run('http://127.0.0.1','synthetic','synthetic')['tok_s'],10.0)
        rates=iter([3,1,2]*4)
        with mock.patch.object(suite,'run',side_effect=lambda *a,**k:{'tok_s':next(rates),'ttft':1}),mock.patch.object(sys,'argv',['suite','--warmup','0','--label','synthetic','--out',str(self.work/'median.jsonl')]),contextlib.redirect_stdout(io.StringIO()):suite.main()
        rec=json.loads((self.work/'median.jsonl').read_text())
        self.assertTrue(all(x==2 for x in rec['summary'].values()))
    def test_suite_missing_usage_rejected(self):
        with server(self.work,'missing-usage') as base:
            with self.assertRaises(ValueError):suite.run(base,'synthetic','synthetic')
    def test_stress_slow_stream_and_silence(self):
        for mode,want_stall in [('normal',False),('silent',True)]:
            with server(self.work,mode,delay=0.01) as base:
                rec={}; stress.one_stream(base,'synthetic','high','synthetic',32768,0.05,1,rec)
                self.assertEqual(rec['stall'],want_stall)
                if not want_stall:self.assertEqual(rec['gen_tokens'],30)
                self.assertFalse(stress.dead(stress.env_state(base+'/health')))
    def test_stress_client_cap_has_no_fabricated_usage(self):
        with server(self.work,'long',delay=0.01) as base:
            rec={}; stress.one_stream(base,'synthetic',None,'synthetic',32768,0.05,0.02,rec)
            self.assertEqual(rec['finish'],'client_timeout'); self.assertIsNone(rec['gen_tokens'])
    def test_stress_cli_and_memory_fallback(self):
        with server(self.work) as base:
            port=base.rsplit(':',1)[1]
            p=self.run_command(sys.executable,'scripts/ve_stress.py','--rounds',port+':2','--health-url',base+'/health','--heartbeat','0.01','--out',self.work/'stress')
            self.assertIn('STRESS_DONE completed',p.stdout)
        with mock.patch('builtins.open',side_effect=FileNotFoundError):self.assertIsNone(stress.mem_avail_gib())
    def test_compare_synthetic_arithmetic_and_missing_safety(self):
        output=self.work/'comparison.md'
        p=self.run_command(sys.executable,'scripts/g2_compare.py','--runs',self.work/'runs','--baseline','synthetic-reference','--vision','vision','--control','control','--out',output)
        self.assertEqual(output.read_text(),p.stdout)
        self.assertIn('85.0* (80/90)',p.stdout); self.assertIn('| -5.0 |',p.stdout)
        self.assertIn('Reference (unverified)',p.stdout)
        self.assertIn('Original and rewritten quality gates: not evaluated',p.stdout)
        self.assertIn('These deltas do not establish the quality cost',p.stdout)
        self.assertNotIn('passed',p.stdout); self.assertNotIn('missed',p.stdout)
        fixture=json.loads((self.work/'runs'/'synthetic-reference'/'results.json').read_text())
        self.assertTrue(fixture['synthetic'])
        incomplete=compare.rows({'rows':[{'cat':'c3-tool','runs':[80,80]}]})
        report=compare.render({},incomplete,{},[],['c3-tool'])
        self.assertIn('Safety: not evaluated',report)
        self.assertIn('| own mean | not provided |',report)
    def test_compare_favorable_scores_do_not_validate_a_shared_alias(self):
        # Matching label text and favorable scores cannot establish backend identity.
        reference=self.work/'runs'/'shared-alias'; reference.mkdir()
        data=json.loads((self.work/'runs'/'synthetic-reference'/'results.json').read_text())
        data['model']='shared-alias'
        for row in data['rows']: row['runs']=[50,50]
        (reference/'results.json').write_text(json.dumps(data))
        p=self.run_command(sys.executable,'scripts/g2_compare.py','--runs',self.work/'runs','--baseline','shared-alias','--vision','vision','--control','control')
        self.assertIn('| +35.0 |',p.stdout)
        self.assertIn('Original and rewritten quality gates: not evaluated',p.stdout)
        self.assertNotIn('passed',p.stdout); self.assertNotIn('missed',p.stdout)
        self.assertIn('Safety failures: none recorded.',p.stdout)
    def test_dockerfile_sed_and_guard(self):
        text=(ROOT/'configs/Dockerfile.k5').read_text()
        command=text[text.index('RUN ')+4:].replace('\\\n','')
        for line,ok in [('if (( vision_model && dspark_tokens % 3 != 0 )); then\n',True),('changed entrypoint\n',False)]:
            target=self.work/'entrypoint.sh'; target.write_text(line)
            # Portable sed invocation on macOS; the actual replacement and grep guard are unchanged.
            local=command.replace('/opt/recipe/scripts/k2-entrypoint.sh',shlex.quote(str(target)))
            if sys.platform=='darwin':local=local.replace('sed -i ',"sed -i '' ")
            self.run_command('sh','-c',local,ok=ok)
    def test_arm_success_and_failure_logs(self):
        bins=self.work/'bin'; bins.mkdir(); recipe=self.work/'recipe'; recipe.mkdir()
        (recipe/'.env').write_text('DRAFT_SAMPLE_METHOD=probabilistic\n')
        launch=recipe/'launch.sh'; launch.write_text('#!/bin/sh\ncp "$ENV_FILE" "'+str(self.work/'effective.env')+'"\n'); launch.chmod(0o755)
        stubs={
            'docker':'#!/bin/sh\ncase "$1" in logs) echo "revision: synthetic; max_model_len: 256000; Mean acceptance length: 2.51"; echo "RuntimeError: synthetic failure";; inspect) echo synthetic;; esac\n',
            'curl':'#!/bin/sh\nexit "${CURL_EXIT:-0}"\n',
            'sudo':'#!/bin/sh\nexit 99\n',
            'python3':'#!/bin/sh\ncase "$1" in *suite.py) echo SUITE_DONE;; *) exec '+shlex.quote(sys.executable)+' "$@";; esac\n'}
        for name,text in stubs.items():p=bins/name;p.write_text(text);p.chmod(0o755)
        env=dict(self.env,PATH=str(bins)+os.pathsep+os.environ['PATH'],RECIPE_DIR=str(recipe),ARM_DIR=str(self.work/'arms'))
        p=self.run_command('bash','scripts/arm.sh','synthetic','DRAFT_SAMPLE_METHOD=greedy',env=env)
        self.assertIn('READY synthetic',p.stdout)
        self.assertIn('DRAFT_SAMPLE_METHOD=greedy',(self.work/'effective.env').read_text())
        self.assertIn('DRAFT_SAMPLE_METHOD=probabilistic',(recipe/'.env').read_text())
        p=self.run_command('bash','scripts/arm.sh','failed',env=dict(env,CURL_EXIT='1'),ok=False)
        self.assertIn('CONTAINER_EXITED failed',p.stdout)
        self.assertIn('synthetic failure',(self.work/'arms/failed.docker.log').read_text())
    def test_shell_syntax(self):
        for path in (ROOT/'scripts').glob('*.sh'):self.run_command('bash','-n',path)


if __name__=='__main__': unittest.main()
