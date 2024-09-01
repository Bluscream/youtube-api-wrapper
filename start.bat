@echo off
cd /d %~dp0
git pull
git submodule init
git submodule update
git submodule status
call python -m venv .venv
call .venv\Scripts\pip install -r requirements.txt
call .venv\Scripts\python app.py