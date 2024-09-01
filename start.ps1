Set-Location -Path $PSScriptRoot
git pull
git submodule init
git submodule update
git submodule status
python -m venv .venv
.\.venv\Scripts\pip install -r requirements.txt
.\.venv\Scripts\python app.py