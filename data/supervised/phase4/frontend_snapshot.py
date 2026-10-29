"""Local snapshot of the FootIQ frontend (Phase 4, stage P4.0): create, verify, diff and restore. Standard library only.

    python data/supervised/phase4/frontend_snapshot.py create                    write baseline/frontend_baseline.zip + manifest (refuses to overwrite)
    python data/supervised/phase4/frontend_snapshot.py verify                    re-hash every file inside the zip against the manifest
    python data/supervised/phase4/frontend_snapshot.py diff [--folder F]         compare frontend/ (or F) with the manifest: added, changed, removed
    python data/supervised/phase4/frontend_snapshot.py restore <folder>          extract into an EMPTY folder and verify every file after extraction
    python data/supervised/phase4/frontend_snapshot.py restore-file <path> [--folder F]   put ONE baseline file back into frontend/ (or F)

`create` only reads frontend/. Nothing here touches git (the frontend folder is untracked and stays so), the production store, the models or any data file.
node_modules/ and dist/ are not part of the snapshot: both are rebuilt from package-lock.json (npm ci, npm run build).
"""
import argparse
import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
FRONT = ROOT / "frontend"
OUT = Path(__file__).resolve().parent / "baseline"
ZIP = OUT / "frontend_baseline.zip"
MANIFEST = OUT / "frontend_baseline.manifest.json"
EXCLUDED_DIRS = {"node_modules", "dist"}


def sha_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha_file(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def live_files(folder: Path = FRONT) -> dict:
    """{relative posix path: absolute path} for everything that belongs in the snapshot."""
    out = {}
    for p in sorted(folder.rglob("*")):
        rel = p.relative_to(folder)
        if p.is_file() and not (set(rel.parts[:-1]) & EXCLUDED_DIRS):
            out[rel.as_posix()] = p
    return out


def tool_version(*cmd) -> str:
    try:
        return subprocess.run(cmd, capture_output=True, text=True, shell=(sys.platform == "win32")).stdout.strip()
    except OSError:
        return "unavailable"


def git(*args) -> str:
    return subprocess.run(["git", *args], cwd=ROOT, capture_output=True, text=True).stdout.strip()


def create() -> None:
    if ZIP.exists() or MANIFEST.exists():
        sys.exit(f"refusing to overwrite an existing baseline: {ZIP} / {MANIFEST}")
    OUT.mkdir(parents=True, exist_ok=True)
    files = live_files()
    entries = {rel: dict(bytes=p.stat().st_size, sha256=sha_file(p)) for rel, p in files.items()}
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for rel, p in files.items():
            zf.write(p, arcname=f"frontend/{rel}")
    manifest = dict(
        purpose="Baseline snapshot of the frontend taken before any Phase 4 edit (stage P4.0).",
        created_utc=datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        source_folder="frontend/",
        excluded_directories=sorted(EXCLUDED_DIRS),
        file_count=len(entries),
        total_bytes=sum(e["bytes"] for e in entries.values()),
        files=entries,
        zip=dict(name=ZIP.name, bytes=ZIP.stat().st_size, sha256=sha_file(ZIP)),
        package_lock_sha256=entries["package-lock.json"]["sha256"],
        node=tool_version("node", "--version"),
        npm=tool_version("npm", "--version"),
        git=dict(branch=git("branch", "--show-current"), head=git("log", "--oneline", "-1"),
                 tracked_files_under_frontend=len([x for x in git("ls-files", "frontend").splitlines() if x]),
                 staged_files=[x for x in git("diff", "--cached", "--name-only").splitlines() if x]),
    )
    MANIFEST.write_text(json.dumps(manifest, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
    (OUT / "frontend_baseline.manifest.sha256").write_text(f"{sha_file(MANIFEST)} *{MANIFEST.name}\n", encoding="utf-8")
    print(f"created {ZIP.name}: {manifest['file_count']} files, {manifest['total_bytes']} bytes, zip {manifest['zip']['bytes']} bytes, sha256 {manifest['zip']['sha256']}")


def load_manifest() -> dict:
    recorded = (OUT / "frontend_baseline.manifest.sha256").read_text(encoding="utf-8").split()[0]
    if sha_file(MANIFEST) != recorded:
        sys.exit("the manifest file does not match its recorded checksum")
    return json.loads(MANIFEST.read_text(encoding="utf-8"))


def verify_zip(manifest: dict) -> list:
    """Problems found re-hashing the zip (empty list = the zip holds exactly the manifest's files, byte for byte)."""
    problems = []
    if sha_file(ZIP) != manifest["zip"]["sha256"]:
        problems.append("zip checksum differs from the manifest")
    with zipfile.ZipFile(ZIP) as zf:
        bad = zf.testzip()
        if bad:
            problems.append(f"zip member fails its CRC: {bad}")
        names = {n[len("frontend/"):]: n for n in zf.namelist() if n.startswith("frontend/") and not n.endswith("/")}
        for extra in sorted(set(names) - set(manifest["files"])):
            problems.append(f"in the zip but not in the manifest: {extra}")
        for rel, info in manifest["files"].items():
            if rel not in names:
                problems.append(f"missing from the zip: {rel}")
            elif sha_bytes(zf.read(names[rel])) != info["sha256"]:
                problems.append(f"content differs from the manifest: {rel}")
    return problems


def diff_live(manifest: dict, folder: Path = FRONT) -> dict:
    live = live_files(folder)
    recorded = manifest["files"]
    return dict(
        added=sorted(set(live) - set(recorded)),
        removed=sorted(set(recorded) - set(live)),
        changed=sorted(rel for rel in set(live) & set(recorded) if sha_file(live[rel]) != recorded[rel]["sha256"]),
        unchanged=len([rel for rel in set(live) & set(recorded) if sha_file(live[rel]) == recorded[rel]["sha256"]]),
    )


def restore(target: Path) -> None:
    manifest = load_manifest()
    problems = verify_zip(manifest)
    if problems:
        sys.exit("refusing to restore from a snapshot that fails verification:\n  " + "\n  ".join(problems))
    if target.exists() and any(target.iterdir()):
        sys.exit(f"refusing to restore into a folder that is not empty: {target}")
    target.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(ZIP) as zf:
        for name in zf.namelist():
            if name.startswith("frontend/") and not name.endswith("/"):
                dest = target / name[len("frontend/"):]
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(zf.read(name))
    after = diff_live(manifest, target)
    if after["added"] or after["removed"] or after["changed"]:
        sys.exit(f"restored folder differs from the manifest: {after}")
    print(f"restored {len(manifest['files'])} files into {target}; every file matches its recorded sha256")


def restore_file(rel: str, folder: Path) -> None:
    """Put one baseline file back (verified against the manifest first); every other file in `folder` is left alone."""
    manifest = load_manifest()
    rel = rel.replace("\\", "/")
    if rel not in manifest["files"]:
        sys.exit(f"{rel} is not part of the baseline (it was added after the snapshot)")
    with zipfile.ZipFile(ZIP) as zf:
        data = zf.read(f"frontend/{rel}")
    if sha_bytes(data) != manifest["files"][rel]["sha256"]:
        sys.exit(f"the copy of {rel} inside the zip does not match the manifest; nothing was written")
    dest = folder / rel
    dest.parent.mkdir(parents=True, exist_ok=True)
    state = "absent" if not dest.exists() else ("identical" if sha_file(dest) == manifest["files"][rel]["sha256"] else "different")
    dest.write_bytes(data)
    print(f"{rel}: was {state} in {folder}; baseline version written")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("create")
    sub.add_parser("verify")
    d = sub.add_parser("diff")
    d.add_argument("--folder", type=Path, default=FRONT)
    r = sub.add_parser("restore")
    r.add_argument("folder", type=Path)
    rf = sub.add_parser("restore-file")
    rf.add_argument("path")
    rf.add_argument("--folder", type=Path, default=FRONT)
    args = ap.parse_args()
    if args.cmd == "create":
        create()
    elif args.cmd == "verify":
        problems = verify_zip(load_manifest())
        print("zip verified: every file matches the manifest" if not problems else "\n".join(problems))
        sys.exit(1 if problems else 0)
    elif args.cmd == "diff":
        print(json.dumps(diff_live(load_manifest(), args.folder), indent=1))
    elif args.cmd == "restore":
        restore(args.folder)
    elif args.cmd == "restore-file":
        restore_file(args.path, args.folder)


if __name__ == "__main__":
    main()
