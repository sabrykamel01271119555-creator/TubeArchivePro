# Building the setup wizard (Windows 11) - TubeArchive Pro 2.3.2

Result: `build\output\TubeArchivePro_Setup_<version>.exe` (the file you attach to your GitHub release).

## 1. What you must install once (preparation)
| What | Why | Where / how |
|---|---|---|
| **Python 3.10+ 64-bit** | you already have it | python.org (tick "Add python.exe to PATH" and "py launcher") |
| **The Python requirements** | PySide6 (interface), psutil (pause/resume), PyInstaller (makes the .exe) | **automatic**: `build\build.bat` runs `pip install -r requirements.txt` inside `.venv` |
| **Inno Setup 6** (free) | makes the wizard | https://jrsoftware.org/isdl.php - install with the default options |
| **yt-dlp.exe** | download engine | https://github.com/yt-dlp/yt-dlp/releases/latest -> `yt-dlp.exe` -> copy to `tools\` |
| **ffmpeg + ffprobe** | join video/audio, convert to MP3... | see section 2 -> copy `ffmpeg.exe` and `ffprobe.exe` to `tools\` |
| **Your icon** `TubeArchivePro.ico` | icon of the program and of the setup | put it in `build\` (an .ico that contains 16, 32, 48, 256 px) |
| *optional* `Arabic.isl` | Arabic wizard language | download https://github.com/jrsoftware/issrc/blob/main/Files/Languages/Unofficial/Arabic.isl (Raw) -> `build\Arabic.isl` |
| *optional* `vc_redist.x64.exe` | Microsoft C++ runtime for a clean Windows without it | https://aka.ms/vs/17/release/vc_redist.x64.exe -> `build\redist\vc_redist.x64.exe` (the setup installs it silently only if it is missing) |

**Automatic (2.3.2):** `build\build.bat` now runs `build\get_tools.ps1`, which downloads whatever is still missing: `yt-dlp.exe`, `ffmpeg.exe` + `ffprobe.exe`
(gyan.dev release essentials), the wizard languages `Arabic.isl`, `ChineseSimplified.isl`, `Hindi.isl` and `redist\vc_redist.x64.exe`; and `build\make_icon.py`, which creates
`build\TubeArchivePro.ico` from the program's own icon when you have not put your own there. Files that already exist are never replaced (put your own icon / newer tools first if you like).
**Python packages without any download:** run `build\pack_requirements.bat` once (needs internet one time) - it stores PySide6, psutil, PyInstaller and their
dependencies as `.whl` files in `build\wheels`. As long as that folder holds `.whl` files, `build\build.bat` installs from it with `pip --no-index` (no download),
so the project folder with `build\wheels` can be copied to any PC. (The packages are about 250 MB, so they are not inside the zip I send.)
Only Python and Inno Setup 6 must be installed by you. Run it alone: `powershell -ExecutionPolicy Bypass -File build\get_tools.ps1`.

No programming skills are needed: you only double-click `build\build.bat`.
`build\check_build.py` also copies `ffmpeg.exe` / `ffprobe.exe` for you if they are still inside the extracted
`ffmpeg-...-full_build\bin` folder under `tools\`.

## 2. ffmpeg: "essentials" or "full" - does it matter for the program?
Both are static Windows builds from https://www.gyan.dev/ffmpeg/builds/ . TubeArchive Pro only uses ffmpeg to:
join the video and audio streams (stream copy), convert audio (MP3, WAV, AAC...), convert to AVI/MKV/MP4, embed thumbnail and metadata.
**Both builds do all of that, so the program runs the same.**

| | essentials | full |
|---|---|---|
| Content | the common encoders / decoders (x264, x265, MP3, AAC, Opus, VP9...) | everything essentials has + many extra libraries (rare codecs, AV1 extras, subtitles/OCR, filters, GPU/Vulkan, ...) |
| Size of each exe (ffmpeg.exe / ffprobe.exe) | about half | about double (your setup becomes ~100+ MB bigger) |
| Needed by us? | **yes, enough** | not needed |
| Type | choose **"release essentials"** (a stable numbered version, e.g. 7.x) | "git" builds (like `ffmpeg-2026-10-19-git-...`) are daily snapshots: newer but less tested |

Recommendation: download **ffmpeg-release-essentials.zip** (not "shared": the shared build needs extra DLL files). Use only `bin\ffmpeg.exe`
and `bin\ffprobe.exe` (not `ffplay.exe`). The `full_build` you already extracted also works - it only makes the setup bigger.

## 3. Build (one click)
1. Put the files of section 1 in place (`tools\yt-dlp.exe`, `tools\ffmpeg.exe`, `tools\ffprobe.exe`, `build\TubeArchivePro.ico`).
2. Open `build\installer_settings.iss` and set `GitHubRepo` to `YourUser/YourRepo` (see section 5).
3. Double-click **`build\build.bat`**. Options: `build\build.bat fast` = skip the automatic tests; `build\build.bat exe` = only the program folder
   `build\dist\TubeArchivePro\TubeArchivePro.exe` (no wizard, no Inno Setup needed). It does:
   virtual environment -> requirements -> get tools / icon / check -> tests -> PyInstaller -> Inno Setup.
4. Result: `build\output\TubeArchivePro_Setup_<version>.exe`.

Build errors are printed in the window; the usual ones: missing tool file (check_build tells which), Inno Setup not installed.

## 4. What the setup installs and where
```
C:\Program Files\TubeArchive Pro\          (or "current user only": %LOCALAPPDATA%\Programs\TubeArchive Pro - the wizard asks)
    TubeArchivePro.exe  _internal\          the program
    tools\yt-dlp.exe  ffmpeg.exe  ffprobe.exe
    assets\info  assets\owner               help / about / contact / donate texts, owner banner
    data\languages  data\config\default_settings.json  data\downloads_baseline.txt
    LICENSES.txt
%APPDATA%\TubeArchivePro\                  YOUR DATA (kept on upgrade and ask on uninstall)
    data\config\current_settings.json  data\history  data\favorites  data\sync  data\feedback  data\cache  data\*.log
    assets\ads                              the ads downloaded from GitHub
```
* **Upgrade**: run a newer setup: it installs over the old version (same AppId) and your data stays.
* **First start after an older "portable" copy**: its settings / history / favorites / sync / ads are copied once to `%APPDATA%\TubeArchivePro`.
* **Portable use**: create an empty file `portable.txt` next to `TubeArchivePro.exe` -> the data stays next to the exe.
* **Uninstall**: removes the program; asks whether to delete `%APPDATA%\TubeArchivePro` (downloaded videos are never touched).

## 5. Update check when the setup starts
`installer.iss` asks `https://api.github.com/repos/<GitHubRepo>/releases/latest` (no login, 1 request). If its tag (e.g. `v2.3.1`)
is newer than the setup's version, a message offers to open the download page (Yes) or to go on (No). Offline or no release yet = silently skipped.
Skip it by `TubeArchivePro_Setup_x.exe /SKIPUPDATECHECK`. The release must be **public** and not a draft / pre-release.
The program itself checks for updates at every start (GITHUB_SETUP.md).

## 6. Publishing a version
1. `build\build.bat` -> setup .exe.
2. GitHub -> your repository -> Releases -> *Draft a new release* -> tag `v2.3.2` -> attach `TubeArchivePro_Setup_2.3.2.exe` -> Publish.
   The number of downloads of this file is the counter shown in the program (only `.exe` files are counted).
3. Test the setup on another PC or a Windows virtual machine before you announce it.

## 7. Known points
* **No code-signing certificate**: Windows SmartScreen shows "unknown publisher" on first run (More info -> Run anyway). Normal for a new,
  unsigned program; it fades as more people download it. Some antivirus programs may warn about PyInstaller programs: submit the file to
  the antivirus vendor as a false positive if it happens (the one-folder build used here triggers far fewer warnings than the one-file build).
* **yt-dlp becomes old** when YouTube changes: put a newer `tools\yt-dlp.exe` and build again (or later we can make the program update it).
* I (the assistant) cannot run Windows tools here, so the build scripts are written carefully but first tested by you: send me the
  messages of `build.bat` if anything stops.

## 8. Build it on GitHub (no Windows tools on your PC) - 2.3.2
The repository `sabrykamel01271119555-creator/TubeArchivePro` carries `.github/workflows/build-setup.yml`. It builds the **fully offline setup**
(`TubeArchivePro_Setup_<version>.exe`: Python, PySide6, psutil, yt-dlp, ffmpeg, ffprobe and all texts / languages are INSIDE the file; nothing is downloaded
when the user installs or starts the program) on a Windows machine of GitHub.
1. Upload the project folder to the repository (the `.gitignore` keeps tools, caches and your own data out).
2. GitHub -> **Actions** -> *Build setup* -> **Run workflow**; after about 10-15 minutes the setup is under **Artifacts** (a zip containing the .exe).
3. For a public release: create the tag `v2.3.2` (Releases -> Draft a new release -> new tag) - the workflow attaches the .exe to that release by itself.
