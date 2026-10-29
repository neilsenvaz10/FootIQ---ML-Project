New-Item -ItemType Directory -Force -Path 'data\supervised\phase4\p45' | Out-Null
Copy-Item 'data\footiq.sqlite' 'data\supervised\phase4\p45\tests.sqlite' -Force
$env:FOOTIQ_STORE_PATH = 'D:\Foot IQ\data\supervised\phase4\p45\tests.sqlite'
& 'D:\Foot IQ\.venv\Scripts\python.exe' -B -X utf8 -m pytest tests -q -p no:cacheprovider
