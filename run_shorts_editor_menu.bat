@echo off
chcp 65001 > nul
cd /d "%~dp0"
set INPUT_PATH=input
set RANGES_PATH=ranges\ranges.txt
set OUTPUT_ROOT=output

:MODE_MENU
cls
set MODE=
set MODE_LABEL=
set DURATION=
set ASPECT=
set ASPECT_LABEL=
set LAYOUT=
set LAYOUT_LABEL=
set FOREGROUND_SCALE=
set FOREGROUND_SCALE_LABEL=
set PRE_CROP=none
set PRE_CROP_LABEL=none / 일반 영상
set COMMAND=
set mode_choice=
echo ========================================
echo shorts_auto_editor v0.5 menu
echo ========================================
echo.
echo Select mode.
echo.
echo 1. dry_run
echo 2. multi_clip_join
echo 3. manual_cut
echo 4. exit
echo.
echo Candidate workflow guide:
echo - candidate_scan: create the base candidate report.
echo - combined_candidates: create an integrated candidate report with recommendation display.
echo - apply_candidate_ranges: apply the user-selected candidate to ranges.txt.
echo - manual_cut: create the final rough cut from ranges.txt.
echo - Not automatic best cut. Review candidates before choosing.
echo.
set /p mode_choice=Enter number: 

if "%mode_choice%"=="1" (
  set MODE=dry_run
  set MODE_LABEL=dry_run
  goto DURATION_MENU
)
if "%mode_choice%"=="2" (
  set MODE=multi_clip_join
  set MODE_LABEL=multi_clip_join
  goto DURATION_MENU
)
if "%mode_choice%"=="3" (
  set MODE=single_video_manual_cut
  set MODE_LABEL=manual_cut
  goto DURATION_MENU
)
if "%mode_choice%"=="4" goto END

echo.
echo Invalid selection. Returning to mode menu.
goto MODE_MENU

:DURATION_MENU
cls
set duration_choice=
echo ========================================
echo Select duration
echo ========================================
echo.
echo 1. 35s
echo 2. 50s
echo 3. 60s
echo.
set /p duration_choice=Enter number: 

if "%duration_choice%"=="1" (
  set DURATION=35
  goto ASPECT_MENU
)
if "%duration_choice%"=="2" (
  set DURATION=50
  goto ASPECT_MENU
)
if "%duration_choice%"=="3" (
  set DURATION=60
  goto ASPECT_MENU
)

echo.
echo Invalid selection. Returning to duration menu.
goto DURATION_MENU

:ASPECT_MENU
cls
set aspect_choice=
echo ========================================
echo Select aspect ratio
echo ========================================
echo.
echo 1. 9:16 vertical
echo 2. 16:9 horizontal
echo.
set /p aspect_choice=Enter number: 

if "%aspect_choice%"=="1" (
  set ASPECT=9:16
  set ASPECT_LABEL=9:16 vertical
  goto LAYOUT_MENU
)
if "%aspect_choice%"=="2" (
  set ASPECT=16:9
  set ASPECT_LABEL=16:9 horizontal
  set LAYOUT=crop
  set LAYOUT_LABEL=not applied for 16:9
  set FOREGROUND_SCALE=1.00
  set FOREGROUND_SCALE_LABEL=not applied for 16:9
  goto PRE_CROP_MENU
)

echo.
echo Invalid selection. Returning to aspect menu.
goto ASPECT_MENU

:LAYOUT_MENU
cls
set layout_choice=
echo ========================================
echo Select 9:16 layout
echo ========================================
echo.
echo 1. fit_blur  - preserve source with blurred background
echo 2. crop      - fill screen, may crop left/right
echo 3. fit_black - preserve source with black background
echo.
set /p layout_choice=Enter number: 

if "%layout_choice%"=="1" (
  set LAYOUT=fit_blur
  set LAYOUT_LABEL=fit_blur - source + blurred background
  goto FOREGROUND_SCALE_MENU
)
if "%layout_choice%"=="2" (
  set LAYOUT=crop
  set LAYOUT_LABEL=crop - fill screen, may crop left/right
  set FOREGROUND_SCALE=1.00
  set FOREGROUND_SCALE_LABEL=not applied for crop
  goto PRE_CROP_MENU
)
if "%layout_choice%"=="3" (
  set LAYOUT=fit_black
  set LAYOUT_LABEL=fit_black - source + black background
  goto FOREGROUND_SCALE_MENU
)

echo.
echo Invalid selection. Returning to layout menu.
goto LAYOUT_MENU

:FOREGROUND_SCALE_MENU
cls
set foreground_scale_choice=
echo ========================================
echo Select foreground scale
echo ========================================
echo.
echo 1. 1.00 safe / preserve full foreground
echo 2. 1.10 larger / improved readability
echo 3. 1.20 largest / edge cropping possible
echo.
set /p foreground_scale_choice=Enter number: 

if "%foreground_scale_choice%"=="1" (
  set FOREGROUND_SCALE=1.00
  set FOREGROUND_SCALE_LABEL=safe / preserve full foreground
  goto PRE_CROP_MENU
)
if "%foreground_scale_choice%"=="2" (
  set FOREGROUND_SCALE=1.10
  set FOREGROUND_SCALE_LABEL=larger / improved readability
  goto PRE_CROP_MENU
)
if "%foreground_scale_choice%"=="3" (
  set FOREGROUND_SCALE=1.20
  set FOREGROUND_SCALE_LABEL=largest / edge cropping possible
  goto PRE_CROP_MENU
)

echo.
echo Invalid selection. Returning to foreground scale menu.
goto FOREGROUND_SCALE_MENU

:PRE_CROP_MENU
cls
set pre_crop_choice=
echo ========================================
echo Select pre-crop
echo ========================================
echo.
echo 1. none / 일반 영상
echo 2. crop=1440:1080:240:0 / 좌우 검은 여백 제거 추천
echo.
set /p pre_crop_choice=Enter number: 

if "%pre_crop_choice%"=="1" (
  set PRE_CROP=none
  set PRE_CROP_LABEL=none / 일반 영상
  goto CONFIRM
)
if "%pre_crop_choice%"=="2" (
  set PRE_CROP=crop=1440:1080:240:0
  set PRE_CROP_LABEL=좌우 검은 여백 제거 추천
  goto CONFIRM
)

echo.
echo Invalid selection. Returning to pre-crop menu.
goto PRE_CROP_MENU

:CONFIRM
cls
set run_choice=
set COMMAND=python shorts_auto_editor.py --mode %MODE% --input %INPUT_PATH% --output-root %OUTPUT_ROOT% --aspect %ASPECT% --duration %DURATION% --layout %LAYOUT% --foreground-scale %FOREGROUND_SCALE% --pre-crop %PRE_CROP%
if "%MODE%"=="single_video_manual_cut" (
  set COMMAND=python shorts_auto_editor.py --mode %MODE% --input %INPUT_PATH% --ranges %RANGES_PATH% --output-root %OUTPUT_ROOT% --aspect %ASPECT% --duration %DURATION% --layout %LAYOUT% --foreground-scale %FOREGROUND_SCALE% --pre-crop %PRE_CROP%
)
echo ========================================
echo Confirm command
echo ========================================
echo.
echo mode: %MODE_LABEL%
echo duration: %DURATION%s
echo aspect: %ASPECT_LABEL%
echo layout: %LAYOUT% (%LAYOUT_LABEL%)
echo foreground_scale: %FOREGROUND_SCALE% (%FOREGROUND_SCALE_LABEL%)
echo pre_crop: %PRE_CROP% (%PRE_CROP_LABEL%)
if "%ASPECT%"=="16:9" (
  echo note: layout and foreground scale are not applied to 16:9 output; pre-crop can still be applied before 16:9 layout.
)
if "%LAYOUT%"=="crop" (
  echo note: foreground scale is not applied to crop layout.
)
if not "%FOREGROUND_SCALE%"=="1.00" (
  echo warning: foreground scale may crop edge information.
)
if not "%PRE_CROP%"=="none" (
  echo warning: pre-crop may remove edge information.
)
echo input: %INPUT_PATH%
if "%MODE%"=="single_video_manual_cut" (
  echo ranges: %RANGES_PATH%
  echo candidate flow note: run candidate_scan and combined_candidates first if you need candidate reports, then apply_candidate_ranges before manual_cut.
  echo selection note: this menu does not auto-confirm a best cut; use ranges.txt only after reviewing the candidate.
  if not "%DURATION%"=="35" (
    echo.
    echo Warning: current default ranges file was prepared for 35s tests. 50s/60s manual_cut can fail if ranges are too short.
  )
) else (
  echo ranges: not used
)
echo.
echo Command:
echo %COMMAND%
echo.
set /p run_choice=Run this command? (Y/N): 
if /I "%run_choice%"=="Y" goto RUN_COMMAND
if /I "%run_choice%"=="N" goto MODE_MENU

echo.
echo Invalid selection. Returning to confirmation screen.
goto CONFIRM

:RUN_COMMAND
echo.
echo Running command...
%COMMAND%
echo.
echo Command finished.
echo Press Enter to return to the menu.
echo Any non-empty input exits. This prevents piped test input from triggering another run.
set return_choice=
set /p return_choice=Return: 
if "%return_choice%"=="" goto MODE_MENU
goto END

:END
echo.
echo Exiting shorts_auto_editor menu.


