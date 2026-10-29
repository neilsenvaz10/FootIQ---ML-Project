import os, sys; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
"""Write the DRAFT pinned artifact manifest (regression/shadow use). Official use binds the manifest sha256 inside the owner's approval file."""
from _common import *
m = artifacts.write_pin()
out(dict(artifacts=len(m), manifest_sha256=artifacts.manifest_sha(m)))
