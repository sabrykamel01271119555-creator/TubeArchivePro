@echo off
rem =============================================================================
rem TubeArchive Pro  |  Version 2.3.2  |  build\build.bat
rem One click: virtual environment -> requirements -> checks -> tests -> PyInstaller -> Inno Setup -> setup .exe
rem Run it by double click (or from a command prompt in the project folder:  build\build.bat   or  build\build.bat fast)
rem   "fast" = skip the automatic tests     "exe" = only the program folder (build\dist\TubeArchivePro\TubeArchivePro.exe), no setup wizard
rem   Missing yt-dlp / ffmpeg / wizard languages / VC++ runtime are downloaded by build\get_tools.ps1; the icon is made by build\make_icon.py
rem =============================================================================
setlocal
cd /d "%~dp0.."

if not exist ".venv\Scripts\python.exe" (
    echo [1/6] Creating the virtual environment .venv ...
    py -3 -m venv .venv || (echo Python 3.10+ ^(64-bit^) is not installed or "py" is not in PATH & goto :fail)
) else (
    echo [1/6] Virtual environment .venv found
)
call ".venv\Scripts\activate.bat"

echo [2/6] Installing the requirements ^(PySide6, psutil, PyInstaller^) ...
python -m pip install --upgrade pip >nul
if exist build\wheels\*.whl (
    echo       using the packages in build\wheels ^(no download^)
    pip install --no-index --find-links build\wheels -r requirements.txt || goto :fail
) else (
    pip install -r requirements.txt || goto :fail
)

echo [3/6] Getting the tools, making the icon, checking the data files ...
powershell -NoProfile -ExecutionPolicy Bypass -File build\get_tools.ps1
python build\make_icon.py || goto :fail
python build\check_build.py || goto :fail

if /i "%1"=="fast" (
    echo [4/6] Tests skipped ^(fast^)
) else if /i "%1"=="exe" (
    echo [4/6] Tests skipped ^(fast^)
) else (
    echo [4/6] Running the automatic tests ...
    python -m unittest discover -s tests || (echo Tests failed - fix them or run: build\build.bat fast & goto :fail)
)

echo [5/6] Building the program with PyInstaller ...
if exist build\dist rmdir /s /q build\dist
if exist build\work rmdir /s /q build\work
pyinstaller --noconfirm --clean --distpath build\dist --workpath build\work build\TubeArchivePro.spec || goto :fail

if /i "%1"=="exe" (
    echo.
    echo DONE: build\dist\TubeArchivePro\TubeArchivePro.exe  ^(copy the tools, assets and data folders next to it to run it, or build the setup^)
    pause
    exit /b 0
)

for /f %%v in ('python -c "from app.paths import APP_VERSION; print(APP_VERSION)"') do set VER=%%v

set "ISCC="
if exist "%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if exist "%ProgramFiles%\Inno Setup 6\ISCC.exe" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe" set "ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe"
if "%ISCC%"=="" (
    echo Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php and run this file again.
    goto :fail
)

echo [6/6] Creating the setup wizard %VER% with Inno Setup ...
"%ISCC%" /Q /DMyAppVersion=%VER% build\installer.iss || goto :fail

echo.
echo ================================================================
echo  DONE:  build\output\TubeArchivePro_Setup_%VER%.exe
echo  Upload this file to your GitHub release (Releases page, "Attach binaries").
echo ================================================================
pause
exit /b 0

:fail
echo.
echo *** The build stopped. Read the message above. ***
pause
exit /b 1
