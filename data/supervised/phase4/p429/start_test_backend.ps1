$env:FOOTIQ_DISABLE_SYNC = "1"
$env:FOOTIQ_STORE_PATH = "C:\Users\DELL\AppData\Local\Temp\claude\D--Foot-IQ\005e84e5-f41e-4e30-91b6-409ae0b7c9fc\scratchpad\ui_copy.sqlite"
Set-Location "D:\Foot IQ"
.\.venv\Scripts\python.exe -X utf8 -m uvicorn main:app --app-dir app --port 8001 --timeout-graceful-shutdown 5
