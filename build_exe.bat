@echo off
setlocal EnableExtensions

set "APP_NAME=autoclicker"
set "BAT_DIR=%~dp0"
set "SCRIPT=%BAT_DIR%roblox_autoclicker.py"
set "OUT_EXE=%BAT_DIR%%APP_NAME%.exe"
set "BUILD_ROOT=%BAT_DIR%build-autoclicker"
set "VENV=%BUILD_ROOT%\venv"
set "VENV_PY=%VENV%\Scripts\python.exe"
set "WORK=%BUILD_ROOT%\pyinstaller"
set "RUNNER=%BUILD_ROOT%\run_build.py"
set "PY_CMD="
set "PY_EXE="
set "PY_KIND="
set "USE_VENV=0"

py -3 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PY_CMD=py -3"

if not defined PY_CMD (
  python -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python"
)

if not defined PY_CMD (
  python3 -c "import sys" >nul 2>nul
  if not errorlevel 1 set "PY_CMD=python3"
)

if not defined PY_CMD (
  echo Python was not found.
  echo.
  echo Install Python from python.org, or install Python from the Microsoft Store.
  echo After installing, close this window, open a new terminal, and run this bat again.
  pause
  exit /b 1
)

for /f "delims=" %%P in ('%PY_CMD% -c "import sys; print(sys.executable)" 2^>nul') do if not defined PY_EXE set "PY_EXE=%%P"

echo %PY_EXE% | find /I "WindowsApps" >nul
if not errorlevel 1 (
  set "PY_KIND=Microsoft Store Python"
) else (
  set "PY_KIND=Desktop Python"
)

if not exist "%SCRIPT%" (
  echo Could not find:
  echo %SCRIPT%
  echo.
  echo Put this bat file in the same folder as roblox_autoclicker.py.
  pause
  exit /b 1
)

echo Using Python command:
echo %PY_CMD%
echo.
echo Python path:
echo %PY_EXE%
echo.
echo Python type:
echo %PY_KIND%
echo.

%PY_CMD% -c "import tkinter; root = tkinter.Tk(); root.withdraw(); root.destroy(); print('tkinter ok')"
if errorlevel 1 (
  echo.
  echo This Python cannot open Tkinter, so it cannot build this UI app correctly.
  echo If this is Microsoft Store Python, open a new terminal and try again.
  echo If it still fails, install Python from python.org with Tcl/Tk enabled.
  pause
  exit /b 1
)

if not exist "%BUILD_ROOT%" mkdir "%BUILD_ROOT%"

if exist "%VENV_PY%" (
  set "USE_VENV=1"
) else (
  %PY_CMD% -m venv "%VENV%"
  if exist "%VENV_PY%" set "USE_VENV=1"
)

if "%USE_VENV%"=="1" goto check_venv_pip
goto install_current

:check_venv_pip
"%VENV_PY%" -m pip --version >nul 2>nul
if not errorlevel 1 goto install_venv
echo pip is missing in the build environment. Installing pip...
"%VENV_PY%" -m ensurepip --upgrade
if errorlevel 1 goto install_current
goto install_venv

:install_venv
"%VENV_PY%" -m pip install --upgrade pip pyinstaller
if errorlevel 1 goto fail
goto remove_old

:install_current
echo.
echo Could not use a local build environment.
echo Trying to install/build with your current Python instead...
%PY_CMD% -m pip --version >nul 2>nul
if errorlevel 1 %PY_CMD% -m ensurepip --upgrade
%PY_CMD% -m pip install --user --upgrade pip pyinstaller
if errorlevel 1 goto fail
set "USE_VENV=0"
goto remove_old

:remove_old
if exist "%OUT_EXE%" (
  del "%OUT_EXE%" >nul 2>nul
  if exist "%OUT_EXE%" (
    echo.
    echo Could not replace:
    echo %OUT_EXE%
    echo.
    echo Close Autoclicker if it is running, or end autoclicker.exe in Task Manager, then run this builder again.
    pause
    exit /b 1
  )
)

:write_runner
> "%RUNNER%" echo import os
>> "%RUNNER%" echo import PyInstaller.__main__
>> "%RUNNER%" echo PyInstaller.__main__.run([
>> "%RUNNER%" echo "--noconfirm",
>> "%RUNNER%" echo "--clean",
>> "%RUNNER%" echo "--onefile",
>> "%RUNNER%" echo "--windowed",
>> "%RUNNER%" echo "--name",
>> "%RUNNER%" echo os.environ["APP_NAME"],
>> "%RUNNER%" echo "--distpath",
>> "%RUNNER%" echo os.environ["BAT_DIR"],
>> "%RUNNER%" echo "--workpath",
>> "%RUNNER%" echo os.environ["WORK"],
>> "%RUNNER%" echo "--specpath",
>> "%RUNNER%" echo os.environ["BUILD_ROOT"],
>> "%RUNNER%" echo os.environ["SCRIPT"],
>> "%RUNNER%" echo ])

echo Building:
echo %SCRIPT%
echo.

if "%USE_VENV%"=="1" (
  "%VENV_PY%" "%RUNNER%"
) else (
  %PY_CMD% "%RUNNER%"
)
if errorlevel 1 goto fail
if not exist "%OUT_EXE%" (
  echo.
  echo Build finished, but the exe was not created:
  echo %OUT_EXE%
  goto fail
)
goto done

:done
echo.
echo Built:
echo %OUT_EXE%
pause
exit /b 0

:fail
echo.
echo Build failed. Check the output above for the error.
pause
exit /b 1
