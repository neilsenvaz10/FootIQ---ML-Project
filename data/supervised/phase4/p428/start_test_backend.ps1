$env:FOOTIQ_DISABLE_SYNC = "1"
Set-Location "D:\Foot IQ"
.\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8001 --timeout-graceful-shutdown 5
