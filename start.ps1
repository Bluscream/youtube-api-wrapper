Set-Location -Path $PSScriptRoot
git pull
git submodule init
git submodule update
git submodule status
python -m venv .venv
.\.venv\Scripts\pip install --upgrade pip setuptools wheel
.\.venv\Scripts\pip install -r requirements.txt --upgrade
.\.venv\Scripts\python app.py