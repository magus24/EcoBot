@echo off
cd /d "%~dp0"
python main.py --conf 0.12 --bottle-conf 0.20 --imgsz 960 --box-shrink 0.08
pause
