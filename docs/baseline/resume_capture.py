"""Resume the first capture after the sandbox denied its temporary directory.

Does not overwrite evidence. All legacy execution stays in new local copies.
Run only after reviewing capture_baseline.py. This is audit orchestration,
not a modification of legacy code.
"""
from pathlib import Path
import ast
import json
import sys

base = Path(__file__).parent.resolve()
capture = base / "capture_2026-10-20"
source = (base / "capture_baseline.py").read_text(encoding="utf-8")
tree = ast.parse(source)
definitions = ast.Module(body=[n for n in tree.body if isinstance(n, (ast.Import, ast.ImportFrom, ast.FunctionDef))], type_ignores=[])
scope = {"__file__": str(base / "capture_baseline.py"), "__name__": "baseline_resume"}
exec(compile(definitions, str(base / "capture_baseline.py"), "exec"), scope)
root = base.parents[1]
before = json.loads((capture / "original_files_before.json").read_text(encoding="utf-8"))["files"]
inventory = json.loads((capture / "dataset_inventory.json").read_text(encoding="utf-8"))["files"]
work = capture / "isolated_execution"
work.mkdir(exist_ok=False)
scope.update(ROOT=root, OUT=capture, SKIP={".git", ".venv", "venv", "__pycache__", ".pytest_cache", "node_modules", "provider_cache"},
             before=before, inventory=inventory, paths=[root/r["path"] for r in before],
             archive=capture / "reference_snapshot.zip", work=work)
scope["emit"]("execution_workspace_verified.json", {
    "path": str(work), "policy": "Fresh workspace-local isolation; original temporary attempt failed before execution",
    "initial_failure": "WinError 5 creating run1 under sandbox temporary directory; no legacy command executed in that attempt"
})
exec(compile(source[source.index("commands = []"):], str(base / "capture_baseline.py"), "exec"), scope)
