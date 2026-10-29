<#
.SYNOPSIS
  Run the FootIQ backend (and with it the six-hour Bundesliga scheduler) independently of any editor or preview session.

.DESCRIPTION
  A small supervisor (no extra software): it starts the FastAPI backend, restarts it after a crash (back-off 5, 10, 20, 40, 60 s), writes logs, and allows only ONE supervisor per port.
  The scheduler lives inside the backend. A machine-wide lock (data\run\scheduler.lock, see app\store\sync.py) guarantees that even if a second backend is started (for example a preview
  server on another port) it will NOT start a second scheduler.

  Commands:   start | stop | restart | status | logs | audit | task-plan | task-install -Apply | task-remove -Apply | run (used by start and by the Task Scheduler)
  Examples:   powershell -File scripts\ops\footiq_service.ps1 status
              powershell -File scripts\ops\footiq_service.ps1 start

  Environment (all optional):
    FOOTIQ_PORT            backend port (default 8000)
    FOOTIQ_DISABLE_SYNC=1  start the backend but never the scheduler
    FOOTIQ_STORE_PATH      use another database file (tests use a private copy)
    FOOTIQ_SCHEDULER_LOCK  another scheduler lock file (tests)
    FOOTIQ_RUN_DIR / FOOTIQ_LOG_DIR  where pid/stop files and logs live (default data\run and logs)

  Nothing here changes the synchronisation settings (config\sync.json) and nothing registers a Windows task unless you run task-install -Apply.
#>
param(
    [Parameter(Position = 0)]
    [ValidateSet('start', 'stop', 'restart', 'status', 'logs', 'audit', 'task-plan', 'task-install', 'task-remove', 'run')]
    [string]$Command = 'status',
    [switch]$Apply,
    [int]$Lines = 40
)

$ErrorActionPreference = 'Stop'
$Root = (Resolve-Path (Join-Path $PSScriptRoot '..\..')).Path
$Port = if ($env:FOOTIQ_PORT) { [int]$env:FOOTIQ_PORT } else { 8000 }
$RunDir = if ($env:FOOTIQ_RUN_DIR) { $env:FOOTIQ_RUN_DIR } else { Join-Path $Root 'data\run' }
$LogDir = if ($env:FOOTIQ_LOG_DIR) { $env:FOOTIQ_LOG_DIR } else { Join-Path $Root 'logs' }
$Py = Join-Path $Root '.venv\Scripts\python.exe'
$PidFile = Join-Path $RunDir "supervisor-$Port.pid"
$ChildPidFile = Join-Path $RunDir "backend-$Port.pid"
$StopFile = Join-Path $RunDir "stop-$Port.flag"
$SupLog = Join-Path $LogDir 'supervisor.log'
$MutexName = "Local\FootIQ-Supervisor-$Port"
$TaskName = 'FootIQ-Backend'
New-Item -ItemType Directory -Force -Path $RunDir, $LogDir | Out-Null

function Write-Log([string]$msg) {
    $line = '{0} [{1}] {2}' -f (Get-Date).ToUniversalTime().ToString('yyyy-MM-ddTHH:mm:ssZ'), $PID, $msg
    Add-Content -Path $SupLog -Value $line -Encoding UTF8
    if ($Command -ne 'run') { Write-Host $line }
}

function Test-SupervisorRunning {
    $m = $null
    if ([System.Threading.Mutex]::TryOpenExisting($MutexName, [ref]$m)) { $m.Dispose(); return $true }
    return $false
}

function Get-PortOwner {
    $c = Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1
    if ($c) { return [int]$c.OwningProcess }
    return $null
}

function Get-Json([string]$path) {
    try { return Invoke-RestMethod -Uri ("http://127.0.0.1:{0}{1}" -f $Port, $path) -TimeoutSec 8 } catch { return $null }
}

function Stop-Tree([int]$id) {
    if ($id -gt 0 -and (Get-Process -Id $id -ErrorAction SilentlyContinue)) { & taskkill.exe /T /F /PID $id | Out-Null }
}

function Remove-OldLogs {
    Get-ChildItem -Path $LogDir -Filter 'backend-*.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -Skip 20 | Remove-Item -Force -ErrorAction SilentlyContinue
}

# ----------------------------------------------------------------------------------------------------------------- the supervisor loop
function Invoke-Run {
    $created = $false
    $mutex = New-Object System.Threading.Mutex($true, $MutexName, [ref]$created)
    if (-not $created) { Write-Log "another supervisor already runs for port ${Port}: exiting"; exit 3 }
    Set-Content -Path $PidFile -Value $PID
    Remove-Item -Path $StopFile -ErrorAction SilentlyContinue
    Write-Log "supervisor started (port $Port, python $Py)"
    $rapid = 0
    try {
        while (-not (Test-Path $StopFile)) {
            $owner = Get-PortOwner
            if ($owner) {
                Write-Log "port $Port is already in use by process ${owner}: not starting a second backend, waiting 15 s"
                Start-Sleep -Seconds 15
                continue
            }
            $stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
            $out = Join-Path $LogDir "backend-$stamp.out.log"
            $err = Join-Path $LogDir "backend-$stamp.err.log"
            $argv = @('-X', 'utf8', '-m', 'uvicorn', 'main:app', '--app-dir', 'app', '--host', '127.0.0.1', '--port', "$Port")
            $p = Start-Process -FilePath $Py -ArgumentList $argv -WorkingDirectory $Root -RedirectStandardOutput $out -RedirectStandardError $err -WindowStyle Hidden -PassThru
            Set-Content -Path $ChildPidFile -Value $p.Id
            Write-Log "backend started (pid $($p.Id)); logs $out"
            $began = Get-Date
            while (-not $p.HasExited -and -not (Test-Path $StopFile)) { Start-Sleep -Seconds 2 }
            if (Test-Path $StopFile) {
                Write-Log 'stop requested: stopping the backend'
                Stop-Tree $p.Id
                break
            }
            $ran = [int]((Get-Date) - $began).TotalSeconds
            $rapid = if ($ran -lt 120) { $rapid + 1 } else { 0 }
            Write-Log "backend exited (code $($p.ExitCode)) after $ran s; consecutive quick exits: $rapid"
            if ($rapid -ge 10) { Write-Log 'ten quick exits in a row: giving up (see the backend logs)'; exit 2 }
            $wait = [Math]::Min(60, 5 * [Math]::Pow(2, [Math]::Max(0, $rapid - 1)))
            Write-Log "restarting in $wait s"
            Start-Sleep -Seconds $wait
            Remove-OldLogs
        }
    }
    finally {
        Remove-Item -Path $PidFile, $ChildPidFile, $StopFile -ErrorAction SilentlyContinue
        Write-Log 'supervisor stopped'
        $mutex.ReleaseMutex()
    }
}

# ----------------------------------------------------------------------------------------------------------------- user commands
function Invoke-Start {
    if (Test-SupervisorRunning) { Write-Log "already running (supervisor for port $Port); nothing to do"; return }
    $owner = Get-PortOwner
    if ($owner) { Write-Log "port $Port is in use by process $owner (not started by this supervisor): stop it first (for example the editor's preview server)"; exit 4 }
    Start-Process -FilePath 'powershell.exe' -ArgumentList @('-NoProfile', '-WindowStyle', 'Hidden', '-ExecutionPolicy', 'Bypass', '-File', "`"$PSCommandPath`"", 'run') -WindowStyle Hidden | Out-Null
    for ($i = 0; $i -lt 45; $i++) {
        Start-Sleep -Seconds 2
        $h = Get-Json '/api/health'
        if ($h -and $h.status -eq 'ok') { Write-Log "backend is up on port $Port (club models warming: $(-not $h.club_prediction_ready))"; return }
    }
    Write-Log 'the backend did not answer within 90 s: see "logs"'; exit 5
}

function Invoke-Stop {
    if (-not (Test-SupervisorRunning)) { Write-Log 'no supervisor is running'; Remove-Item -Path $StopFile -ErrorAction SilentlyContinue; return }
    New-Item -ItemType File -Force -Path $StopFile | Out-Null
    for ($i = 0; $i -lt 25; $i++) { Start-Sleep -Seconds 1; if (-not (Test-SupervisorRunning)) { break } }
    if (Test-SupervisorRunning) {
        Write-Log 'supervisor did not stop in 25 s: forcing it'
        if (Test-Path $ChildPidFile) { Stop-Tree ([int](Get-Content $ChildPidFile)) }
        if (Test-Path $PidFile) { Stop-Tree ([int](Get-Content $PidFile)) }
    }
    Remove-Item -Path $StopFile, $PidFile, $ChildPidFile -ErrorAction SilentlyContinue
    $owner = Get-PortOwner
    if ($owner) { Write-Log "warning: port $Port is still held by process $owner" } else { Write-Log "stopped; port $Port is free" }
}

function Invoke-Status {
    $sup = Test-SupervisorRunning
    $owner = Get-PortOwner
    $h = Get-Json '/api/health'
    $s = Get-Json '/api/sync/status'
    Write-Host ("Supervisor            : {0}" -f $(if ($sup) { 'running (pid ' + $(if (Test-Path $PidFile) { Get-Content $PidFile } else { '?' }) + ')' } else { 'NOT running' }))
    Write-Host ("Backend on port {0}   : {1}" -f $Port, $(if ($h) { "answering (listener pid $owner), models ready: $($h.club_prediction_ready)" } elseif ($owner) { "port held by pid $owner but not answering" } else { 'NOT running' }))
    if ($s) {
        $sc = $s.scheduler
        Write-Host ("Scheduler             : {0}" -f $sc.status)
        Write-Host ("  live sync / interval: {0} / {1} min, competitions {2}, mode {3}" -f $sc.live_enabled, $sc.interval_minutes, ($sc.enabled_competitions -join ','), $sc.refresh_mode)
        Write-Host ("  scheduler threads   : {0} (lock: {1}), failed cycles in a row: {2}" -f $sc.active_scheduler_threads, $sc.lock_state, $sc.consecutive_failed_cycles)
        Write-Host ("  next scheduled check: {0}" -f $sc.next_scheduled_check_utc)
        $bl = $s.competitions | Where-Object { $_.competition_key -eq 'BUNDESLIGA' }
        if ($bl) { Write-Host ("  last source check   : {0}; {1}" -f $bl.last_successful_external_check_utc, $bl.last_check_summary) }
        Write-Host ("Quarantine            : {0} sync finding(s) need the owner" -f $s.quarantine.needs_operator_review)
    }
    $opsFile = Join-Path $Root 'config\operations.json'
    if (Test-Path $opsFile) { $ops = Get-Content $opsFile -Raw | ConvertFrom-Json; Write-Host ("Operational reviewer  : {0} (daily: scripts\ops\footiq_service.ps1 audit)" -f $ops.operational_reviewer) }
    $latest = Get-ChildItem -Path $LogDir -Filter 'backend-*.err.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($latest) { Write-Host ("Latest backend log    : {0}" -f $latest.FullName) }
    Write-Host ("Supervisor log        : {0}" -f $SupLog)
    if (-not ($sup -and $h)) { exit 1 }
}

function Invoke-Logs {
    Write-Host "--- supervisor.log (last $Lines lines)"
    if (Test-Path $SupLog) { Get-Content $SupLog -Tail $Lines }
    $e = Get-ChildItem -Path $LogDir -Filter 'backend-*.err.log' -ErrorAction SilentlyContinue | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($e) { Write-Host "--- $($e.Name) (last $Lines lines)"; Get-Content $e.FullName -Tail $Lines }
}

function Get-TaskObjects {
    $action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument ('-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File "{0}" run' -f $PSCommandPath) -WorkingDirectory $Root
    $trigger = New-ScheduledTaskTrigger -AtLogOn -User ("{0}\{1}" -f $env:USERDOMAIN, $env:USERNAME)
    $settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
    return @{ Action = $action; Trigger = $trigger; Settings = $settings }
}

function Invoke-TaskPlan {
    $t = Get-TaskObjects
    Write-Host "Task name        : $TaskName (not created)"
    Write-Host ("Runs as          : {0}\{1}, only while logged on (no password stored, no admin rights)" -f $env:USERDOMAIN, $env:USERNAME)
    Write-Host ("Trigger          : at log on of that user")
    Write-Host ("Action           : {0} {1}" -f $t.Action.Execute, $t.Action.Arguments)
    Write-Host ("Restart on fail  : {0} times, every {1}" -f $t.Settings.RestartCount, $t.Settings.RestartInterval)
    Write-Host ("Second instance  : {0} (the supervisor mutex and the scheduler lock also refuse duplicates)" -f $t.Settings.MultipleInstances)
    Write-Host "Existing task    : $(if (Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue) { 'YES' } else { 'none' })"
    Write-Host "To create it     : powershell -File scripts\ops\footiq_service.ps1 task-install -Apply"
}

function Invoke-TaskInstall {
    if (-not $Apply) { Write-Host 'Refusing without -Apply. This command would register the scheduled task shown by task-plan. Nothing was created.'; Invoke-TaskPlan; exit 6 }
    $t = Get-TaskObjects
    Register-ScheduledTask -TaskName $TaskName -Action $t.Action -Trigger $t.Trigger -Settings $t.Settings -Description 'Runs the FootIQ backend and its six-hour Bundesliga scheduler (supervisor script).' | Out-Null
    Write-Log "scheduled task $TaskName registered (at log on)"
}

function Invoke-TaskRemove {
    if (-not $Apply) { Write-Host 'Refusing without -Apply. Nothing was removed.'; exit 6 }
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    Write-Log "scheduled task $TaskName removed"
}

switch ($Command) {
    'run' { Invoke-Run }
    'start' { Invoke-Start }
    'stop' { Invoke-Stop }
    'restart' { Invoke-Stop; Invoke-Start }
    'status' { Invoke-Status }
    'logs' { Invoke-Logs }
    'audit' { & $Py -B -X utf8 (Join-Path $Root 'app\store\daily_audit.py'); exit $LASTEXITCODE }
    'task-plan' { Invoke-TaskPlan }
    'task-install' { Invoke-TaskInstall }
    'task-remove' { Invoke-TaskRemove }
}
