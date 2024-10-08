# git clone https://github.com/Bluscream/youtube-api-wrapper
git pull && git submodule init && git submodule update && git submodule status
python -m venv .venv
.venv/bin/pip install --upgrade pip setuptools wheel
.venv/bin/pip install -r requirements.txt --upgrade
# .venv/bin/python app.py
trap 'kill $(jobs -p)' EXIT; until .venv/bin/python app.py & wait; do
    echo "yt proxy crashed with exit code $?. Respawning.." >&2
    sleep 1
done
# nohup ./start.sh & echo "Script started in background" && tail -f /dev/null &
