"""Phase 4.18B canary: a harmless process that logs a heartbeat every 30 s, launched the same way the backend was (WMI Win32_Process.Create, cmd.exe /c, output redirected), to see whether such
detached processes are terminated by something outside FootIQ, and how (graceful signal or hard kill). It reads and writes nothing else."""
import atexit
import signal
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

LOG = Path(__file__).resolve().parent / "canary.log"


def stamp():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def note(msg):
    with open(LOG, "a", encoding="utf-8") as fh:
        fh.write(f"{stamp()} {msg}\n")


def on_signal(signum, frame):
    note(f"received signal {signum}: shutting down (graceful)")
    sys.exit(0)


for name in ("SIGINT", "SIGTERM", "SIGBREAK"):
    if hasattr(signal, name):
        signal.signal(getattr(signal, name), on_signal)
atexit.register(lambda: note("process exiting"))
note(f"canary started pid {__import__('os').getpid()}")
while True:
    time.sleep(30)
    note("alive")
