# git clone https://github.com/Bluscream/youtube-api-wrapper
git pull && git submodule init && git submodule update && git submodule status
python -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python app.py