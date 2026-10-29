# Phase 4.14B: recovery test on a THROW-AWAY task (FootIQ-Test-Recovery) that runs a stand-in with the supervisor's single-instance rule. The production task is not touched here.
$ErrorActionPreference = 'Continue'
$D = 'D:\Foot IQ\data\supervised\phase4\p414b'
$Evidence = "$D\test_evidence.txt"
Set-Content $Evidence "Recovery test $(Get-Date -Format u)`n"
function Say($m) { Write-Host $m; Add-Content $Evidence $m }
$name = 'FootIQ-Test-Recovery'
Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue
Remove-Item "$D\standin.log" -ErrorAction SilentlyContinue
function Standins { @(Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like '*standin.ps1*' }) }
$action = New-ScheduledTaskAction -Execute 'powershell.exe' -Argument "-NoProfile -WindowStyle Hidden -ExecutionPolicy Bypass -File `"$D\standin.ps1`"" -WorkingDirectory 'D:\Foot IQ'
$logon = New-ScheduledTaskTrigger -AtLogOn -User ("{0}\{1}" -f $env:USERDOMAIN, $env:USERNAME)
$settings = New-ScheduledTaskSettingsSet -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1) -MultipleInstances IgnoreNew -ExecutionTimeLimit ([TimeSpan]::Zero) -StartWhenAvailable -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
Register-ScheduledTask -TaskName $name -Action $action -Trigger $logon -Settings $settings | Out-Null
Say "== 1. task created like the production one (log-on trigger only); started"
Start-ScheduledTask -TaskName $name
Start-Sleep -Seconds 8
$a = Standins
Say ("state: {0}; stand-in processes: {1} (pid {2})" -f (Get-ScheduledTask -TaskName $name).State, $a.Count, ($a.ProcessId -join ','))
$pid1 = $a[0].ProcessId

Say "== 2. add the repeating trigger WHILE it runs (Set-ScheduledTask, trigger list = existing log-on + repetition)"
$t = Get-ScheduledTask -TaskName $name
$rep = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 1)      # the test uses 1 minute so it finishes quickly; production uses 5
Set-ScheduledTask -TaskName $name -Trigger @($t.Triggers[0], $rep) | Out-Null
Start-Sleep -Seconds 3
$a = Standins
Say ("after the update: state {0}; same stand-in alive: {1} (pid {2}); processes: {3}" -f (Get-ScheduledTask -TaskName $name).State, ($a.ProcessId -contains $pid1), ($a.ProcessId -join ','), $a.Count)
$xml = Export-ScheduledTask -TaskName $name
Say ("definition now: triggers: {0}; repetition interval: {1}; repetition duration element present: {2}; MultipleInstances: {3}; logon trigger kept: {4}; principal logon type: {5}" -f (([xml]$xml).Task.Triggers.ChildNodes.Count), (([xml]$xml).Task.Triggers.TimeTrigger.Repetition.Interval), ($xml -match '<Duration>'), (([xml]$xml).Task.Settings.MultipleInstancesPolicy), ($xml -match '<LogonTrigger>'), (([xml]$xml).Task.Principals.Principal.LogonType))

Say "== 3. wait through two repetition fires while the stand-in is alive: no second instance may start (IgnoreNew + mutex)"
Start-Sleep -Seconds 130
$a = Standins
Say ("stand-in processes: {0} (pid {1}); still the original: {2}" -f $a.Count, ($a.ProcessId -join ','), ($a.ProcessId -contains $pid1))
Say ("log: " + ((Get-Content "$D\standin.log") -join ' | '))

Say "== 4. kill the stand-in hard (as the production supervisor was killed); the repetition trigger must bring one back within the interval"
& taskkill.exe /F /PID $pid1 | Out-Null
Start-Sleep -Seconds 3
Say ("killed; stand-in processes now: {0}; task state {1}" -f (Standins).Count, (Get-ScheduledTask -TaskName $name).State)
$back = $false
for ($i = 0; $i -lt 40; $i++) { Start-Sleep -Seconds 5; $a = Standins; if ($a.Count -ge 1) { $back = $true; break } }
Say ("revived: {0} after about {1} s; new pid {2}; processes: {3}" -f $back, (($i + 1) * 5 + 3), ($a.ProcessId -join ','), $a.Count)
Start-Sleep -Seconds 70
Say ("another minute later: stand-in processes {0}" -f (Standins).Count)
Say ("log: " + ((Get-Content "$D\standin.log") -join ' | '))

Say "== 5. cleanup of the throw-away task and its stand-in"
Get-ScheduledTask -TaskName $name | Stop-ScheduledTask
Start-Sleep -Seconds 2
foreach ($s in (Standins)) { & taskkill.exe /F /PID $s.ProcessId | Out-Null }
Unregister-ScheduledTask -TaskName $name -Confirm:$false
Say ("test task exists: {0}; stand-ins left: {1}" -f ([bool](Get-ScheduledTask -TaskName $name -ErrorAction SilentlyContinue)), (Standins).Count)
Say ("production supervisor untouched: " + ((Get-CimInstance Win32_Process -Filter "Name='powershell.exe'" | Where-Object { $_.CommandLine -like '*footiq_service*' -and $_.CommandLine -like '* run*' }).ProcessId -join ','))
