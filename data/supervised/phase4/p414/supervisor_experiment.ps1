# Phase 4.14: supervisor behaviour experiment on a PRIVATE port (8123), private copy of the database, private lock/run/log folders, sync disabled.
# The real backend (port 8000) and its scheduler are never touched; production's database is only read once (SQLite backup API) and its hash is compared at the end.
$ErrorActionPreference = 'Continue'
$Root = 'D:\Foot IQ'
$Svc = Join-Path $Root 'scripts\ops\footiq_service.ps1'
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$T = Join-Path $Root 'data\supervised\phase4\p414\work'
if (Test-Path $T) { Remove-Item $T -Recurse -Force }
New-Item -ItemType Directory -Force -Path $T | Out-Null
$Evidence = Join-Path $Root 'data\supervised\phase4\p414\experiment_evidence.txt'
Set-Content $Evidence "Supervisor experiment $(Get-Date -Format u)`n"
function Say($m) { Write-Host $m; Add-Content $Evidence $m }
$prodHash = (Get-FileHash (Join-Path $Root 'data\footiq.sqlite') -Algorithm SHA256).Hash
$prodListener = (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess
$ledger = (Get-Content (Join-Path $Root 'data\snapshots\request_ledger.jsonl')).Count
& $Py -B -c "import sqlite3;s=sqlite3.connect('file:D:/Foot IQ/data/footiq.sqlite?mode=ro',uri=True);d=sqlite3.connect(r'$T\copy.sqlite');s.backup(d);d.close()"
$env:FOOTIQ_PORT = '8123'; $env:FOOTIQ_STORE_PATH = "$T\copy.sqlite"; $env:FOOTIQ_SCHEDULER_LOCK = "$T\scheduler.lock"; $env:FOOTIQ_RUN_DIR = "$T\run"; $env:FOOTIQ_LOG_DIR = "$T\logs"; $env:FOOTIQ_DISABLE_SYNC = '1'
function Health { try { (Invoke-RestMethod -Uri 'http://127.0.0.1:8123/api/health' -TimeoutSec 5).status } catch { 'down' } }
function Listeners { (Get-NetTCPConnection -LocalPort 8123 -State Listen -ErrorAction SilentlyContinue | Measure-Object).Count }
function Svc($a) { & powershell.exe -NoProfile -ExecutionPolicy Bypass -File $Svc $a 2>&1 | Out-String }
function Backends { (Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*uvicorn*' -and $_.CommandLine -like '*--port 8123*' }).Count }
function Wait-Health($sec) { for ($i = 0; $i -lt $sec / 2; $i++) { if ((Health) -eq 'ok') { return $true }; Start-Sleep -Seconds 2 }; return $false }

Say "== 1. an ORPHAN backend (no supervisor) is already running on 8123"
$orphan = Start-Process -FilePath $Py -ArgumentList @('-X', 'utf8', '-m', 'uvicorn', 'main:app', '--app-dir', 'app', '--host', '127.0.0.1', '--port', '8123') -WorkingDirectory $Root -WindowStyle Hidden -PassThru -RedirectStandardOutput "$T\orphan.out" -RedirectStandardError "$T\orphan.err"
Say ("orphan healthy: {0}; listeners: {1}" -f (Wait-Health 90), (Listeners))
Say "status with no supervisor: "; Say (Svc 'status' | Select-String 'Supervisor|Backend' | Out-String)

Say "== 2. the supervisor (what the scheduled task runs: 'run') starts while the orphan is alive"
$sup = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-WindowStyle', 'Hidden', '-ExecutionPolicy', 'Bypass', '-File', "`"$Svc`"", 'run') -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 20
Say ("supervisor pid {0} alive: {1}; backend processes on 8123 (python shim + child count): {2}; listeners: {3}" -f $sup.Id, (-not $sup.HasExited), (Backends), (Listeners))
Say (Get-Content "$T\logs\supervisor.log" | Out-String)
Say "status: "; Say (Svc 'status' | Select-String 'Supervisor|Backend' | Out-String)

Say "== 3. the orphan dies: the supervisor must take over within about 15 s, with ONE backend"
& taskkill.exe /T /F /PID $orphan.Id | Out-Null
$up = Wait-Health 60
Say ("healthy again: {0}; listeners: {1}" -f $up, (Listeners))
Say ((Get-Content "$T\logs\supervisor.log" | Select-Object -Last 4) -join "`n")

Say "== 4. hard-kill ONLY the supervisor (TerminateProcess, no tree), the way the production supervisor disappeared"
$childPid = [int](Get-Content "$T\run\backend-8123.pid")
& taskkill.exe /F /PID $sup.Id | Out-Null
Start-Sleep -Seconds 4
Say ("supervisor alive: {0}; backend still answering: {1}; pid file left behind: {2}; 'supervisor stopped' logged: {3}" -f ((Get-Process -Id $sup.Id -ErrorAction SilentlyContinue) -ne $null), (Health), (Test-Path "$T\run\supervisor-8123.pid"), ((Get-Content "$T\logs\supervisor.log" | Select-String 'supervisor stopped') -ne $null))
Say "status now (the production state seen on 2026-10-28):"; Say (Svc 'status' | Select-String 'Supervisor|Backend' | Out-String)
$exitStart = Svc 'start'; Say ("start while an unsupervised backend runs: " + $exitStart.Trim())

Say "== 5. a NEW supervisor adopts the surviving backend without a duplicate"
$sup2 = Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-WindowStyle', 'Hidden', '-ExecutionPolicy', 'Bypass', '-File', "`"$Svc`"", 'run') -WindowStyle Hidden -PassThru
Start-Sleep -Seconds 25
Say ("supervisor2 alive: {0}; listeners: {1}; backend answering: {2}" -f (-not $sup2.HasExited), (Listeners), (Health))
Say ((Get-Content "$T\logs\supervisor.log" | Select-Object -Last 3) -join "`n")
Say "status: "; Say (Svc 'status' | Select-String 'Supervisor|Backend' | Out-String)

Say "== 6. cleanup (private port only)"
New-Item -ItemType File -Force -Path "$T\run\stop-8123.flag" | Out-Null
Start-Sleep -Seconds 8
foreach ($l in (Get-NetTCPConnection -LocalPort 8123 -State Listen -ErrorAction SilentlyContinue)) { $pp = (Get-CimInstance Win32_Process -Filter "ProcessId=$($l.OwningProcess)").ParentProcessId; $pn = (Get-Process -Id $pp -ErrorAction SilentlyContinue).Name; if ($pn -eq 'python') { & taskkill.exe /T /F /PID $pp | Out-Null }; & taskkill.exe /T /F /PID $l.OwningProcess 2>$null | Out-Null }
Get-Process -Id $sup2.Id -ErrorAction SilentlyContinue | Stop-Process -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 3
Say ("listeners on 8123 after cleanup: {0}" -f (Listeners))

Say "== 7. production untouched"
Say ("production hash unchanged: {0}" -f ($prodHash -eq (Get-FileHash (Join-Path $Root 'data\footiq.sqlite') -Algorithm SHA256).Hash))
Say ("production listener on 8000 unchanged: {0} (was {1}, now {2})" -f ($prodListener -eq (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess), $prodListener, (Get-NetTCPConnection -LocalPort 8000 -State Listen).OwningProcess)
Say ("request ledger lines before/after: {0}/{1}" -f $ledger, (Get-Content (Join-Path $Root 'data\snapshots\request_ledger.jsonl')).Count)
Remove-Item "$T\copy.sqlite*" -Force -ErrorAction SilentlyContinue
