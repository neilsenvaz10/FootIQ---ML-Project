"""Run unchanged legacy suite in a fresh snapshot; preserve all attempts."""
from pathlib import Path
import json
import subprocess
import sys
import time
import zipfile

base = Path(__file__).parent.resolve()
capture = base / "capture_2026-10-20"
root = capture / "isolated_execution/tests_verified"
root.mkdir(exist_ok=False)
with zipfile.ZipFile(capture / "reference_snapshot.zip") as z:
    z.extractall(root)
cmd = [sys.executable, "-B", "-X", "utf8", str(base / "isolated_runner.py"), str(root), "pytest", str(root / "test_trace.json")]
start = time.perf_counter()
p = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
record = {"command": cmd, "exit_code": p.returncode, "duration_seconds": time.perf_counter()-start,
          "note": "-s disables temp capture; no:logging disables null-device logfile; no:cacheprovider avoids cache writes. Test functions unchanged."}
for name, content in [("tests_verified.stdout.txt",p.stdout),("tests_verified.stderr.txt",p.stderr),("tests_verified_command.json",json.dumps(record,indent=2))]:
    with (capture/name).open("x",encoding="utf-8") as f:
        f.write(content)
if (root/"test_results.xml").exists():
    with (capture/"tests_verified.junit.xml").open("xb") as f:
        f.write((root/"test_results.xml").read_bytes())
print(p.stdout)
print(p.stderr)
print(json.dumps(record))
raise SystemExit(p.returncode)
