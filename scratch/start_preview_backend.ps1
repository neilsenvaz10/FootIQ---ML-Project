$env:PYTHONPATH = "D:\Foot IQ\app;D:\Foot IQ"
$env:FOOTIQ_STORE_PATH = 'D:\Foot IQ\data\supervised\phase4\p45\preview.sqlite'
& 'D:\Foot IQ\.venv\Scripts\python.exe' -B -X utf8 -m uvicorn main:app --app-dir 'D:\Foot IQ\app' --port 8000 --host 127.0.0.1
