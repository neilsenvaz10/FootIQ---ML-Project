$ErrorActionPreference = "Continue"
$pk = "C:\Users\DELL\AppData\Local\Temp\claude\D--Foot-IQ\005e84e5-f41e-4e30-91b6-409ae0b7c9fc\scratchpad\pkgtest"
Set-Location $pk
"== venv"
py -V:Astral/CPython3.12.12 -m venv .venv
.\.venv\Scripts\python.exe --version
"== pip install -r requirements-share.txt"
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -q -r requirements-share.txt
"exit $LASTEXITCODE"
"== pip install -r app\requirements.txt"
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -q -r app\requirements.txt
"exit $LASTEXITCODE"
"== import check without scipy"
.\.venv\Scripts\python.exe -X utf8 -c "import sys; sys.path.insert(0,'app'); import seasonsim.pointbounds" 2>&1 | Select-Object -Last 2
"== pip install scipy==1.17.1 (documented extra step)"
.\.venv\Scripts\python.exe -m pip install --disable-pip-version-check -q scipy==1.17.1
"exit $LASTEXITCODE"
"== npm ci"
Set-Location "$pk\frontend"
npm ci --no-audit --no-fund 2>&1 | Select-Object -Last 3
"exit $LASTEXITCODE"
"== done"
