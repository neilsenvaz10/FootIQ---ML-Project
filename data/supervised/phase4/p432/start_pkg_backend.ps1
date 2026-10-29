$pk = "C:\Users\DELL\AppData\Local\Temp\claude\D--Foot-IQ\005e84e5-f41e-4e30-91b6-409ae0b7c9fc\scratchpad\pkgtest"
Set-Location $pk
Remove-Item Env:FOOTIQ_STORE_PATH -ErrorAction SilentlyContinue
$env:FOOTIQ_DISABLE_SYNC = "1"
"store override: [$env:FOOTIQ_STORE_PATH]"
.\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8002 --timeout-graceful-shutdown 5
