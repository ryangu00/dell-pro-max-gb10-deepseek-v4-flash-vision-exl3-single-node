#!/usr/bin/env python3
"""Eight offline cases for strict byte-range response validation."""
import importlib.util
import pathlib
import urllib.request

spec = importlib.util.spec_from_file_location("g", pathlib.Path(__file__).resolve().parents[1] / "scripts/graft0731.py")
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


class Fake:
    def __init__(self, st, cr):
        self.status, self.headers = st, {"Content-Range": cr}

    def close(self):
        pass


orig = urllib.request.urlopen
cases = [((200, ""), False), ((206, "bytes 100-107/999"), False), ((206, "bytes 0-7/"), False), ((206, "bytes 0-7/0"), False),
         ((206, "bytes 0-7/garbage"), False), ((206, "bytes 0-7/999 trailing"), False), ((206, "bytes 0-7/7"), False), ((206, "bytes 0-7/999"), True)]
try:
    for (st, cr), want_ok in cases:
        urllib.request.urlopen = lambda req, timeout=0, st=st, cr=cr: Fake(st, cr)
        try:
            g.get("https://example.invalid/x", 0, 7)
            ok = True
        except IOError:
            ok = False
        assert ok == want_ok, (st, cr, ok)
        print(st, repr(cr), "accepted" if ok else "rejected")
finally:
    urllib.request.urlopen = orig
print("RANGE_SELFTEST_PASS")
