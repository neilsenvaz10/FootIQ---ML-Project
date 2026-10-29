# Passive liveness log for the FootIQ supervisor (Phase 4.14). Reads only; changes nothing. One line a minute for 8 hours.
$log = 'D:\Foot IQ\data\supervised\phase4\p414\liveness.log'
$end = (Get-Date).AddHours(8)
while ((Get-Date) -lt $end) {
    $sup = Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like '*footiq_service*' -and $_.CommandLine -like '* run*' }
    $mutex = $null
    $has = [System.Threading.Mutex]::TryOpenExisting('Local\FootIQ-Supervisor-8000', [ref]$mutex); if ($has) { $mutex.Dispose() }
    $listener = (Get-NetTCPConnection -LocalPort 8000 -State Listen -ErrorAction SilentlyContinue | Select-Object -First 1).OwningProcess
    $claude = (Get-Process claude -ErrorAction SilentlyContinue | Measure-Object).Count
    $ps = (Get-Process powershell -ErrorAction SilentlyContinue | Measure-Object).Count
    $idle = [int]((Get-Date) - (Get-CimInstance Win32_OperatingSystem).LastBootUpTime).TotalMinutes
    Add-Content $log ('{0} supervisor_pids={1} mutex={2} backend_listener={3} claude_procs={4} powershell_procs={5}' -f (Get-Date).ToUniversalTime().ToString('s'), (($sup.ProcessId) -join ','), $has, $listener, $claude, $ps)
    Start-Sleep -Seconds 60
}
