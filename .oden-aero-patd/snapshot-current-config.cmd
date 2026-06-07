@echo off
setlocal

pushd "%~dp0\.."

if not exist ".oden-aero-patd\.venv\Scripts\python.exe" (
  echo ERROR: Missing Python venv at .oden-aero-patd\.venv
  echo Create it first, then re-run this shortcut.
  popd
  exit /b 1
)

set "GREMLIN_DIR=%USERPROFILE%\OneDrive\Documents\FlightSim\Joystick\JoystickGremlin.R14"
set "GREMLIN_USER_DIR=%USERPROFILE%\joystick gremlin"

echo Capturing snapshot with Joystick Gremlin and vJoy validation...
.\.oden-aero-patd\.venv\Scripts\python.exe .\.oden-aero-patd\harness.py snapshot --gremlin-dir "%GREMLIN_DIR%" --gremlin-user-dir "%GREMLIN_USER_DIR%"
set "EXITCODE=%ERRORLEVEL%"

popd
exit /b %EXITCODE%
