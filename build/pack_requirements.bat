@echo off
rem TubeArchive Pro | Version 2.3.2 | build\pack_requirements.bat
rem Run ONCE on a PC with internet: puts every package of requirements.txt (and what they need) into build\wheels as .whl files.
rem After that build\build.bat installs from build\wheels and downloads NOTHING; copy the project folder (with build\wheels) to any PC.
setlocal
cd /d "%~dp0.."
if not exist build\wheels mkdir build\wheels
py -3 -m pip download -r requirements.txt -d build\wheels --only-binary=:all: || (echo Download failed & pause & exit /b 1)
echo.
echo DONE: build\wheels now holds the packages. Keep this folder with the project.
pause
