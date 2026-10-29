# Phase 4: frontend baseline and recovery procedure (stage P4.0)

Written and tested 2026-10-26, before the first Phase 4 edit. The `frontend/` folder is **untracked** in git (`?? frontend/`); it stays untracked: nothing here stages, commits or pushes anything.

## What the baseline is

| Item | Value |
|---|---|
| Snapshot | `data/supervised/phase4/baseline/frontend_baseline.zip` (115,502 bytes, 45 files, 369,035 bytes uncompressed) |
| Zip SHA-256 | `542320c6b0118142fb1aa5528778b8234a1b8f921ae2e4edcd37e8ff4d682aa7` |
| Manifest | `data/supervised/phase4/baseline/frontend_baseline.manifest.json`: path, size and SHA-256 of every file, plus the zip hash, Node and npm versions, and the git state when it was taken |
| Manifest SHA-256 | `a7da8add3a2daa45004a7d7f4fcd9e26593d199004cb32a73a53d69f8ddc4847` (also stored in `frontend_baseline.manifest.sha256`) |
| Taken | 2026-10-26 16:10 UTC, branch `feat/club-ml-v2`, HEAD `970f461`, 0 files tracked under `frontend/`, 0 files staged |
| Contents | everything under `frontend/` except `node_modules/` and `dist/`: `src/` (31 files), `tests/` (6 files), `package.json`, `package-lock.json` (SHA-256 `b8346e6c…03e666`), `index.html`, `vite.config.js`, `README.md`, `.env.example`, `.env.local` (only `VITE_API_URL=http://127.0.0.1:8000`), `.gitignore` |
| Not included | `node_modules/` (rebuilt from `package-lock.json` by `npm ci`) and `dist/` (rebuilt by `npm run build`) |
| Location | `data/supervised/` is git-ignored, so the snapshot is local only. It sits on the same disk as the project: **copy `baseline/` elsewhere if you want protection against a disk failure.** |

The tool is `data/supervised/phase4/frontend_snapshot.py` (standard library only). It never writes into `frontend/` except through `restore-file`, which you run on purpose. `create` refuses to overwrite an existing baseline; `restore` refuses a non-empty folder and refuses to restore from a snapshot that fails verification.

The same folder holds `start_manifest.json` and `phase4_integrity.py`: the SHA-256 state of the protected football files, the frozen models, the production store and the 71 backend sources at the start of Phase 4, and the script that compares the current state with it (see "What the baseline does not cover").

## Check the snapshot is intact

```bash
.venv/Scripts/python.exe -X utf8 data/supervised/phase4/frontend_snapshot.py verify
```

Expected: `zip verified: every file matches the manifest`.

Without Python (Windows PowerShell 5.1, run from `D:\Foot IQ`):

```powershell
$snap = "data\supervised\phase4\baseline"
$dest = "$env:TEMP\footiq_baseline_check"
Expand-Archive -LiteralPath "$snap\frontend_baseline.zip" -DestinationPath $dest
$m = Get-Content -LiteralPath "$snap\frontend_baseline.manifest.json" -Raw | ConvertFrom-Json
$bad = 0
foreach ($p in $m.files.PSObject.Properties) {
  $f = Join-Path "$dest\frontend" $p.Name
  if (-not (Test-Path -LiteralPath $f)) { "MISSING $($p.Name)"; $bad++; continue }
  if ((Get-FileHash -LiteralPath $f -Algorithm SHA256).Hash.ToLower() -ne $p.Value.sha256) { "DIFFERENT $($p.Name)"; $bad++ }
}
"checked $($m.file_count) files, problems: $bad"
Remove-Item -LiteralPath $dest -Recurse -Force
```

## See what changed since the baseline

```bash
.venv/Scripts/python.exe -X utf8 data/supervised/phase4/frontend_snapshot.py diff
```

Prints the files `added`, `removed` and `changed` since the snapshot and the number `unchanged`. `node_modules/` and `dist/` are ignored. `--folder <path>` compares another copy.

## Recover one file

```bash
.venv/Scripts/python.exe -X utf8 data/supervised/phase4/frontend_snapshot.py restore-file src/lib/team.js
```

The baseline version is checked against the manifest and written over the current file (or recreated if it was deleted). Files added after the snapshot are not in the baseline; delete them by hand. Use `--folder <path>` to restore into another copy.

## Recover the whole frontend

1. Stop the Vite dev server and anything else that holds files open in `frontend/` (Windows will not move a folder in use).
2. Keep the current state aside; nothing is deleted:
   ```powershell
   Rename-Item "D:\Foot IQ\frontend" "frontend_phase4_wip_$(Get-Date -Format yyyyMMdd_HHmm)"
   ```
3. Restore the baseline into a fresh `frontend/` (the tool verifies every file after extraction):
   ```bash
   .venv/Scripts/python.exe -X utf8 data/supervised/phase4/frontend_snapshot.py restore frontend
   ```
4. Rebuild the ignored folders and check:
   ```bash
   cd frontend
   npm ci
   npm run build
   FOOTIQ_LIVE_API=http://127.0.0.1:8000 npx vitest run --no-file-parallelism
   ```
   (The live-contract tests need a backend on port 8000; leave `FOOTIQ_LIVE_API` unset to skip those 9 tests and run the other 56.)
5. When satisfied, delete the `frontend_phase4_wip_*` folder yourself. It is the only copy of the Phase 4 work.

## What was tested (2026-10-26, on scratch copies; the real `frontend/` was not touched by any test)

| Check | Result |
|---|---|
| Tool `verify` on the new zip | passed: 45 of 45 files match the manifest, zip CRC clean |
| Tool `diff` against the live `frontend/` immediately after the snapshot | 0 added, 0 removed, 0 changed, 45 unchanged |
| Independent PowerShell procedure above (`Expand-Archive` + `Get-FileHash`) | 45 files checked, 0 problems, 0 extra files; zip hash equals the manifest |
| Tool `restore` into an empty scratch folder | 45 files written, every hash equal |
| Safeguards | `restore` into a non-empty folder: exit 1; `create` over an existing baseline: exit 1; `restore-file` of a file that is not in the baseline: exit 1 |
| Damage drill on a scratch copy (edit one file, delete one, add one) | `diff` reported exactly the three; `restore-file` repaired the edit and the deletion; after removing the stray file `diff` was clean |
| Whole-frontend drill (steps 2 to 4 above, on the scratch copy) | the damaged copy was moved aside, the baseline restored, `npm ci` installed 159 packages in 14 s, `npm run build` passed in 2.1 s, **65 of 65 tests passed** (including the 9 live-contract tests against the backend on the private database copy), final `diff` clean |
| Baseline build (restored copy, built outside `data/supervised/`) | 625 modules; CSS 39.64 kB (7.78 kB gzip); main script 283.24 kB (90.05 kB gzip); largest chunk (Recharts bars) 352.18 kB (102.36 kB gzip); JavaScript in total 805.62 kB (247.00 kB gzip) |

**Correction (2026-10-26).** The first version of this note gave the baseline stylesheet as 71.12 kB (13.30 kB gzip). That build ran inside `data/supervised/`, which git ignores: Tailwind 4 reads the git-ignore rules when it looks for class names, and in that location it produced 528 extra utility classes that appear nowhere in FootIQ's source (for example `mask-radial-*`, `bg-red-500`). The same 45 files built outside the ignored folder give 39.64 kB, the figure above. **Build restored copies outside `data/supervised/`** (any ordinary folder) or the sizes you compare will be wrong. The tests and the build itself passed in both places; only the stylesheet size differed.

## What the baseline does not cover

* Backend, configuration and football data. Phase 4 stages P4.0 and P4.1 do not change them; `phase4_integrity.py check` proves it by comparing 17 protected files (production store, original CSV, sync settings, frozen models, prospective-evaluation files) and 71 backend sources with the state recorded at the start.
* A later stage that adds a backend endpoint (P4.2) needs its own recovery note; none has been started.
* The snapshot is the state *before* Phase 4. Intermediate states between stages are not saved unless a checkpoint report says so.
