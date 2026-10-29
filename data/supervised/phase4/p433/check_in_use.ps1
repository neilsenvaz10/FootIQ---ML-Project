$root = "D:\Foot IQ"
foreach ($p in @("data\supervised\footiq.before-sync.sqlite", "data\supervised\footiq.before-sync.sqlite-shm", "data\backups\p424_pre_reconcile_20261028\footiq.sqlite", "FootIQ_Dataset_Submission.zip", "logs\uvicorn-20261028-095524.out.log")) {
    $full = Join-Path $root $p
    try {
        $f = [System.IO.File]::Open($full, 'Open', 'ReadWrite', 'None')
        $f.Close()
        "$p : not in use"
    } catch {
        "$p : IN USE or locked: $($_.Exception.Message)"
    }
}
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -match 'pytest|before-sync|p424|FootIQ_Dataset_Submission' -and $_.CommandLine -notmatch 'Get-CimInstance' } | ForEach-Object { "process: $($_.ProcessId) $($_.CommandLine.Substring(0,[Math]::Min(100,$_.CommandLine.Length)))" }
