@echo off
cd /d "%~dp0"
python shorts_auto_editor.py --mode single_video_manual_cut --input input --ranges examples\sample_ranges.txt --output-root output --aspect 9:16 --duration 35
pause
