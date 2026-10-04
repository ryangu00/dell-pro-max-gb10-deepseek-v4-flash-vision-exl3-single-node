#!/usr/bin/env python3
"""Test-only adapter for shell scripts embedding Python on stdin."""
import os
import sys
from unittest import mock
import urllib.request
from offline import transport

with mock.patch.object(urllib.request,'urlopen',side_effect=transport(os.environ['OFFLINE_FIXTURE'])):
    exec(compile(sys.stdin.read(),'<synthetic-stdin>','exec'),{'__name__':'__main__'})
