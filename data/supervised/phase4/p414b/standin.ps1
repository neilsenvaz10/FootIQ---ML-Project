# Stand-in for the supervisor, used ONLY by the throw-away test task FootIQ-Test-Recovery (Phase 4.14B). Same single-instance rule (a named mutex), no backend, no database, no network.
$log = 'D:\Foot IQ\data\supervised\phase4\p414b\standin.log'
$created = $false
$m = New-Object System.Threading.Mutex($true, 'Local\FootIQ-Test-Standin', [ref]$created)
if (-not $created) { Add-Content $log ('{0} [{1}] another stand-in already runs: exiting' -f (Get-Date).ToUniversalTime().ToString('s'), $PID); exit 3 }
Add-Content $log ('{0} [{1}] stand-in started' -f (Get-Date).ToUniversalTime().ToString('s'), $PID)
$end = (Get-Date).AddMinutes(40)
while ((Get-Date) -lt $end) { Start-Sleep -Seconds 5 }
Add-Content $log ('{0} [{1}] stand-in finished (time limit)' -f (Get-Date).ToUniversalTime().ToString('s'), $PID)
$m.ReleaseMutex()
