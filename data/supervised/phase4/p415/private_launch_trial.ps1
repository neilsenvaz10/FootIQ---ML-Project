# Phase 4.15: private trial of the startup-only launch and of retiring the supervisor. Port 8124, private copy of the database, private config/lock/run/log folders.
# The production backend (port 8000), its config and database are not touched; production's database is only read once (SQLite backup API) and its hash is compared at the end.
# The private config enables startup mode with a long minimum gap, so every league counts as "refreshed recently" and the trial makes NO provider request at all.
$ErrorActionPreference = 'Continue'
$Root = 'D:\Foot IQ'
$Svc = Join-Path $Root 'scripts\ops\footiq_service.ps1'
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$T = Join-Path $Root 'data\supervised\phase4\p415\work'
if (Test-Path $T) { Remove-Item $T -Recurse -Force }
New-Item -ItemType Directory -Force -Path $T | Out-Null
$Evidence = Join-Path $Root 'data\supervised\phase4\p415\trial_evidence.txt'
Set-Content $Evidence "Startup-only private trial $(Get-Date -Format u)`n"
function Say($m) { Write-Host $m; Add-Content $Evidence $m }
$prodHash = (Get-FileHash (Join-Path $Root 'data\footiq.sqlite') -Algorithm SHA256).Hash
$prodListener = (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess
$cfgHash = (Get-FileHash (Join-Path $Root 'config\sync.json') -Algorithm SHA256).Hash
$ledger = (Get-Content (Join-Path $Root 'data\snapshots\request_ledger.jsonl')).Count
& $Py -B -c "import sqlite3;s=sqlite3.connect('file:D:/Foot IQ/data/footiq.sqlite?mode=ro',uri=True);d=sqlite3.connect(r'$T\copy.sqlite');s.backup(d);d.close()"
$cfg = Get-Content (Join-Path $Root 'config\sync.json') -Raw | ConvertFrom-Json
$cfg | Add-Member -NotePropertyName sync_mode -NotePropertyValue 'startup' -Force
$cfg | Add-Member -NotePropertyName startup_min_gap_minutes -NotePropertyValue 100000 -Force
$cfg | ConvertTo-Json -Depth 6 | Set-Content "$T\sync.private.json" -Encoding UTF8
$env:FOOTIQ_PORT = '8124'; $env:FOOTIQ_STORE_PATH = "$T\copy.sqlite"; $env:FOOTIQ_SCHEDULER_LOCK = "$T\scheduler.lock"; $env:FOOTIQ_RUN_DIR = "$T\run"; $env:FOOTIQ_LOG_DIR = "$T\logs"; $env:FOOTIQ_SYNC_CONFIG = "$T\sync.private.json"
Remove-Item Env:FOOTIQ_DISABLE_SYNC -ErrorAction SilentlyContinue
function J($p) { try { Invoke-RestMethod -Uri "http://127.0.0.1:8124$p" -TimeoutSec 10 } catch { $null } }
function Wait-Health($sec) { for ($i = 0; $i -lt $sec / 2; $i++) { $h = J '/api/health'; if ($h -and $h.status -eq 'ok') { return $true }; Start-Sleep -Seconds 2 }; return $false }
function Listeners { (Get-NetTCPConnection -LocalPort 8124 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count }
function RunsInCopy { & $Py -B -c "import sqlite3;c=sqlite3.connect(r'$T\copy.sqlite');print(c.execute('select count(*) from sync_runs').fetchone()[0])" }
$runs0 = RunsInCopy

Say "== 1. launch the backend the simple way (plain uvicorn, no supervisor, no task), startup mode from the private config"
$be = Start-Process -FilePath $Py -ArgumentList @('-X', 'utf8', '-m', 'uvicorn', 'main:app', '--app-dir', 'app', '--host', '127.0.0.1', '--port', '8124') -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput "$T\be.out" -RedirectStandardError "$T\be.err"
$t0 = Get-Date
Say ("healthy (the application serves): {0} after about {1:n0} s" -f (Wait-Health 90), ((Get-Date) - $t0).TotalSeconds)
Start-Sleep -Seconds 15
$s = J '/api/sync/status'
Say ("mode: {0} | scheduler status: {1}" -f $s.sync_mode, $s.scheduler.status)
Say ("startup state: {0} | skipped: {1}" -f $s.scheduler.startup.state, (($s.scheduler.startup.skipped | ConvertTo-Json -Compress)))
Say ("scheduler threads: {0} | lock: {1} | enabled: {2} | next scheduled check: {3}" -f $s.scheduler.active_scheduler_threads, $s.scheduler.lock_state, ($s.scheduler.enabled_competitions -join ','), $s.scheduler.next_scheduled_check_utc)
Say ("sync_runs rows in the private copy before/after launch: {0}/{1} (a skipped refresh writes nothing)" -f $runs0, (RunsInCopy))

Say "== 2. 'reload the frontend' ten times: status calls only"
1..10 | ForEach-Object { [void](J '/api/sync/status'); [void](J '/api/health') }
Say ("sync_runs rows after ten reloads: {0}; provider ledger lines before/after: {1}/{2}" -f (RunsInCopy), $ledger, (Get-Content (Join-Path $Root 'data\snapshots\request_ledger.jsonl')).Count)

Say "== 3. the supervisor is not needed; if it is still running it can be retired WITHOUT touching the backend: start one that adopts this backend, then ask it to stop (stop flag)"
$sup = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-WindowStyle', 'Hidden', '-ExecutionPolicy', 'Bypass', '-File', "`"$Svc`"", 'run') -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 20
Say ("supervisor {0} alive: {1}; listeners on 8124: {2}" -f $sup.Id, (-not $sup.HasExited), (Listeners))
New-Item -ItemType File -Force -Path "$T\run\stop-8124.flag" | Out-Null
for ($i = 0; $i -lt 20; $i++) { Start-Sleep -Seconds 2; if ($sup.HasExited) { break } }
Say ("after the stop flag: supervisor exited: {0} (after about {1} s); backend still answering: {2}; listeners: {3}; supervisor log tail: {4}" -f $sup.HasExited, (($i + 1) * 2), (J '/api/health').status, (Listeners), ((Get-Content "$T\logs\supervisor.log" | Select-Object -Last 2) -join ' | '))

Say "== 4. cleanup (private port only)"
foreach ($l in (Get-NetTCPConnection -LocalPort 8124 -State Listen -ErrorAction SilentlyContinue)) { & taskkill.exe /T /F /PID $l.OwningProcess 2>$null | Out-Null }
& taskkill.exe /T /F /PID $be.Id 2>$null | Out-Null
Start-Sleep -Seconds 2
Say ("listeners on 8124: {0}" -f (Listeners))

Say "== 5. production untouched"
Say ("production database hash unchanged: {0}" -f ($prodHash -eq (Get-FileHash (Join-Path $Root 'data\footiq.sqlite') -Algorithm SHA256).Hash))
Say ("production config/sync.json unchanged: {0}" -f ($cfgHash -eq (Get-FileHash (Join-Path $Root 'config\sync.json') -Algorithm SHA256).Hash))
Say ("production backend listener unchanged: {0} (was {1})" -f ($prodListener -eq (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess), $prodListener)
Say ("production supervisor processes: {0}" -f (@(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like '*footiq_service*' -and $_.CommandLine -like '* run*' }).Count))
Remove-Item "$T\copy.sqlite*" -Force -ErrorAction SilentlyContinue
