@echo off
chcp 65001 > nul
setlocal

cd /d "%~dp0"

for /f "delims=" %%I in ('python -c "import sys; print(sys.prefix)"') do set "PY_PREFIX=%%I"
if not defined PY_PREFIX (
    echo ERROR: Python was not found.
    exit /b 1
)

set "SOURCE_TCL=%PY_PREFIX%\tcl"
set "TK_RUNTIME=%~dp0.tk_runtime_ascii"

if not exist "%SOURCE_TCL%\tcl8.6\init.tcl" (
    echo ERROR: Tcl runtime was not found: "%SOURCE_TCL%\tcl8.6\init.tcl"
    exit /b 1
)

if not exist "%TK_RUNTIME%\tcl8.6\init.tcl" (
    echo Preparing local ASCII-path Tcl/Tk runtime...
    if not exist "%TK_RUNTIME%" mkdir "%TK_RUNTIME%"
    xcopy "%SOURCE_TCL%\tcl8.6" "%TK_RUNTIME%\tcl8.6\" /E /I /Y >nul
    xcopy "%SOURCE_TCL%\tk8.6" "%TK_RUNTIME%\tk8.6\" /E /I /Y >nul
)

set "TCL_LIBRARY=%TK_RUNTIME%\tcl8.6"
set "TK_LIBRARY=%TK_RUNTIME%\tk8.6"

set "FFMPEG_PACKAGE_BIN=Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin"
set "FFMPEG_BIN=%LOCALAPPDATA%\%FFMPEG_PACKAGE_BIN%"
set "FFMPEG_BIN_DETECTED="
for /f "usebackq delims=" %%I in (`powershell -NoProfile -Command "$p = Join-Path $env:LOCALAPPDATA 'Microsoft\WinGet\Packages\Gyan.FFmpeg_Microsoft.Winget.Source_8wekyb3d8bbwe\ffmpeg-8.1-full_build\bin'; if ((Test-Path -LiteralPath (Join-Path $p 'ffmpeg.exe')) -and (Test-Path -LiteralPath (Join-Path $p 'ffprobe.exe'))) { Write-Output $p }"`) do set "FFMPEG_BIN_DETECTED=%%I"
echo ffmpeg_bin_candidate=%FFMPEG_BIN%
set "FFMPEG_BIN_READY=0"
if defined FFMPEG_BIN_DETECTED (
    set "FFMPEG_BIN=%FFMPEG_BIN_DETECTED%"
    set "FFMPEG_BIN_READY=1"
    set "PATH=%FFMPEG_BIN%;%PATH%"
)
if not "%FFMPEG_BIN_READY%"=="1" (
    set "FFMPEG_BIN_READY=0"
    echo WARNING: ffmpeg/ffprobe were not both found in: "%FFMPEG_BIN%"
    echo WARNING: Check whether FFmpeg was moved or reinstalled, then update FFMPEG_PACKAGE_BIN in this launcher.
)
echo ffmpeg_bin_ready=%FFMPEG_BIN_READY%

if /I "%~1"=="--self-test" goto SELF_TEST

python shorts_auto_editor_gui.py
exit /b %ERRORLEVEL%

:SELF_TEST
python -c "import shorts_auto_editor_gui as g; app=g.ShortsAutoEditorGui(); app.update(); print('title=' + app.title()); print('input=' + app.vars['input'].get()); print('candidate_source=' + app.vars['candidate_source'].get()); print('output_root=' + app.vars['output_root'].get()); print('top_n=' + app.vars['top_n'].get()); print('duration=' + app.vars['duration'].get()); print('aspect=' + app.vars['aspect'].get()); print('layout_preset=' + app.vars['layout_preset'].get()); print('recent_run=' + str(app.recent_run_dir)); print('recent_mp4=' + str(app.recent_mp4_path)); print('recent_batch_summary=' + str(app.recent_batch_summary_path)); print('recent_candidate_report=' + str(app.recent_candidate_report_path)); print(g.format_tool_discovery('ffmpeg')); print(g.format_tool_discovery('ffprobe')); app.destroy(); print('gui_self_test=ok')"
exit /b %ERRORLEVEL%
