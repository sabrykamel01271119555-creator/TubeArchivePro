# TubeArchive Pro 2.0.4 - Setup, Update and Code Map

This guide has four parts:
1. Install Qt (PySide6) and run the program on Windows 11, step by step
2. How to update the code file by file without losing your data
3. Folder and file structure (what every file is for)
4. Feature -> file -> function map (for example: where the exit window, the "Submit and Exit" button and the "Skip and Exit" button live)

Line numbers are those of version 2.0.4. If you edit a file they move a little; search for the function name instead.

---------------------------------------------------------------------

## 1. Install Qt (PySide6) and run the program - Windows 11

"Qt" for Python is the package **PySide6**. It is installed with pip together with the other libraries listed in `requirements.txt`.

**Step 1 - Install Python 3.10 or newer**
1. Open https://www.python.org/downloads/windows/ and download "Windows installer (64-bit)".
2. Start the installer. On the first screen tick **"Add python.exe to PATH"**, then click **Install Now**.
3. Open a new Command Prompt (Win key, type `cmd`, Enter) and check:
   ```
   python --version
   ```
   It must print `Python 3.10` or higher. (If `python` is not recognised, use `py --version` and `py` instead of `python` in every command below.)

**Step 2 - Put the program in a folder**
Unzip `TubeArchivePro.zip`. Example: `D:\app-youtubedownloader\TubeArchivePro\TubeArchivePro`
(the folder that contains `main.py`, `app`, `data`, `assets`, `tools`).

**Step 3 - (Recommended) create a virtual environment**
A virtual environment keeps the libraries of this program separate from the rest of the computer.
```
cd /d D:\app-youtubedownloader\TubeArchivePro\TubeArchivePro
python -m venv .venv
.venv\Scripts\activate
```
The prompt now starts with `(.venv)`. Do step 4 and 6 in the same window. Next time you only need `.venv\Scripts\activate` before `python main.py`.

**Step 4 - Install Qt (PySide6) and the other libraries**
```
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```
This installs PySide6 (Qt), psutil (pause / resume / gauges) and PyInstaller (only needed later to make the .exe).
To install only what is needed to run: `python -m pip install PySide6 psutil`

**Step 5 - Check that Qt works**
```
python -c "import PySide6; print(PySide6.__version__)"
```
It must print a version number such as `6.7.2`. If you see "DLL load failed", install the
"Microsoft Visual C++ Redistributable 2015-2022 (x64)" from Microsoft and try again.

**Step 6 - Add the two helper programs to the `tools` folder**
| File | Where to get it |
|---|---|
| `yt-dlp.exe` | https://github.com/yt-dlp/yt-dlp/releases/latest (file `yt-dlp.exe`) |
| `ffmpeg.exe` and `ffprobe.exe` | https://www.gyan.dev/ffmpeg/builds/ -> `ffmpeg-release-essentials.zip` -> open the `bin` folder inside |

Copy all three files into `TubeArchivePro\tools\`. Without them the program starts, but downloads show an error.

**Step 7 - Run**
```
python main.py
```
The first start creates `data\config\current_settings.json` and the other data files by itself.

**Step 8 - (Optional) run the automatic tests**
```
python -m unittest discover -s tests
```
All tests should end with `OK` (about 1.5 minutes).

**If something goes wrong**
* The program writes errors to `data\error.log` and the update/ads check to `data\updates.log`. Send me those files.
* `QFont::setPointSize: Point size <= 0 (-1)` in the console: harmless; version 2.0.4 writes the place that causes it to `data\error.log`.
* "pip is not recognized": use `python -m pip ...` (as in the commands above).

---------------------------------------------------------------------

## 2. Updating the code file by file

**Never overwrite these (they hold YOUR data and settings):**

| Path | Contains |
|---|---|
| `data\config\current_settings.json` | your saved settings |
| `data\history\` | download history + thumbnails |
| `data\favorites\`, `data\sync\`, `data\feedback\` | favorites, playlist sync list, ratings |
| `data\cache\` | last copies of online files (counter, reviews) |
| `assets\ads\` | downloaded advertisements |
| `tools\` | yt-dlp.exe, ffmpeg.exe, ffprobe.exe |
| `.venv\` | the Python libraries |

**Safe update procedure**
1. Close the program. Copy the whole program folder somewhere as a backup.
2. Unzip the new `TubeArchivePro.zip` into a temporary folder.
3. Copy these into your program folder and choose "Replace": `main.py`, the folders `app`, `assets\info`, `assets\owner`, `data\languages`, `data\config\default_settings.json`, `tests`, and the `.md` / `.txt` documents.
4. Delete every folder named `__pycache__` (they are rebuilt automatically).
5. Run `python main.py`.

**To update only the files that changed in a version**
* `CHANGELOG.md` lists what changed in each version.
* Every code file starts with a header that lists the versions in which THAT file changed. To list the files that changed in version 2.0.4:
  ```
  findstr /s /m /c:"2.0.4 -" app\*.py main.py
  ```
* `data\languages\en.json` / `ar.json` (texts) and `data\config\default_settings.json` (factory settings) are not Python files; they are listed in the CHANGELOG instead.
* When a Python file changes it must be replaced as a whole file. Files that belong together: a new text needs `app\msg.py` + `data\languages\en.json` + `data\languages\ar.json` (all three).

**Changing a text yourself** - open `data\languages\en.json` (or `ar.json`), find the message (for example `"MSG_082": "Submit and Exit"`) and edit the text on the right. No Python change is needed. Keep the `{name}` placeholders.

**Adding a new text** - run `python tools\dev_addmsg.py spec.json` (explained at the top of that file). It adds the constant to `app\msg.py` and the English and Arabic texts with the next free number.

---------------------------------------------------------------------

## 3. Folder and file structure

```
TubeArchivePro\
|  main.py                  Entry point: error log, Qt font/style, splash, loader, main window, language rebuild
|  requirements.txt         Libraries to install (PySide6, psutil, pyinstaller)
|  README.md                Short description
|  CHANGELOG.md             What changed in every version
|  PROGRESS_2.0.x.md        Work records (for continuing a session)
|  PROJECT_GUIDE.md         This file
|
+--app\                     ALL the Python code of the program
|  |  paths.py              Every path of the program + APP_NAME + APP_VERSION
|  |  msg.py                Message ids: M.BTN_SUBMIT = "MSG_082" (every visible text has a number)
|  |  i18n.py               LanguageManager: loads data\languages\*.json, tr(M.X) returns the text
|  |  settings.py           SettingsManager: default + current settings, get / set / save / reset
|  |  context.py            AppContext: one object holding settings, language, history, favorites, sync, feedback, downloads
|  |  loader.py             StartupLoader: runs during the splash screen (settings, language, history, online check)
|  |  resources.py          Finds ads, logo, yt-dlp.exe and ffmpeg
|  |  history.py            Download history (history.json), thumbnails, delete_files() for deleting from disk
|  |  favorites.py          Favorite categories (+ icons) and which video is in which category
|  |  sync.py               Playlist sync schedule (daily / weekly / monthly)
|  |  feedback.py           Exit-window rating: local file + sending to the Google form
|  |  ads.py                Online folder (Google Drive): new version, this month's ads, links, counter, reviews
|  |  infodoc.py            Turns the help / about / contact / donate / reviews text into formatted pages; links in descriptions
|  |  downloader.py         Download engine WITHOUT Qt: yt-dlp command line, progress parsing, sizes, space check, numbering 01/001
|  |  dlqueue.py            Download queue WITHOUT Qt: max concurrent downloads, playlists as one task per video, skip, pause, cancel
|  |  download_manager.py   Qt bridge: runs the engine in threads and sends signals to the screens
|  |  sysmon.py             Numbers for the gauges (network, disk, free space) using psutil
|  |  demo.py               Sample data (only used when demo_mode is on)
|  |
|  +--ui\                   Everything you SEE (screens, windows, widgets)
|     |  main_window.py     Main window: title bar, header + ad space, side menu, work area stack, gauges, closing the program
|     |  new_download_page.py   "New Download" screen
|     |  downloads_page.py  "Downloads" screen (queue, playlist cards, playlist details window)
|     |  library_page.py    "Archive" and "Library" screens (same class, two modes) + video cards
|     |  sync_page.py       "Playlist Sync" screen
|     |  settings_page.py   "Settings" screen
|     |  info_page.py       Reviews / Help / About us / Contact us / Donate screen
|     |  sync_flow.py       The "Sync now" workflow (reads the playlist, shows the sync window, starts the download)
|     |  dialogs.py         ALL pop-up windows: exit windows, success, errors, choices, details, category, sync, update
|     |  widgets.py         Hand-drawn widgets: gauges, nav buttons, ad banner, toggle switch, window buttons, page-change fade
|     |  icons.py           Every icon is drawn in code (app icon, folder, star, trash, globe ...)
|     |  theme.py           Colours and the global style sheet (STYLE); font scaling helpers
|     |  splash.py          Splash (loading) screen
|     |  actions.py         Small shared actions (reveal file, blur background, add to favorites)
|     |  pages.py           Old placeholder pages (kept for the demo rows)
|
+--assets\
|  +--ads\                  Downloaded advertisement gifs (+ ads_links.json, ads_allowed.json)
|  +--info\                 Texts of Help / About us / Contact us / Donate (aboutus.en.txt, aboutus.ar.txt ...) and icons\ (InstaPay, Vodafone Cash ...)
|  +--owner\                banner.jpg (not used in the header any more), channel_logo.png (optional round logo)
|
+--data\
|  |  downloads_baseline.txt Download counter known when the setup was built
|  +--config\               default_settings.json (factory) and current_settings.json (yours)
|  +--languages\            en.json, ar.json (every text of the program)
|  +--history\              history.json + thumbs\
|  +--favorites\ +--sync\ +--feedback\   favorites.json, sync.json, feedback.json + my_rating.json
|  +--cache\                last online copies (downloads_counter, reviews)
|  |  error.log, updates.log (created when needed)
|
+--tools\                   yt-dlp.exe, ffmpeg.exe, ffprobe.exe (you put them here); dev_addmsg.py (developer helper)
+--tests\                   Automatic tests (test_downloader, test_queue, test_ads, test_feedback ...) and a fake yt-dlp
```

Rule of the design: **files without Qt** (`downloader.py`, `dlqueue.py`, `ads.py`, `infodoc.py`, `feedback.py`, `history.py`, `sysmon.py` ...) hold the logic and can be tested alone; **files in `ui\`** only draw screens and call that logic.

---------------------------------------------------------------------

## 4. Feature -> file -> function map

### 4.1 Exit window (what you asked for)

When you close the program (X button, Alt+F4) the same chain always runs:

| Step | File | Function | What it does |
|---|---|---|---|
| 1 | `app\ui\main_window.py` | `MainWindow.closeEvent` (line ~628) | Qt calls it when the window is closing. Calls `request_exit()`; if it returns False the program stays open. |
| 2 | `app\ui\main_window.py` | `MainWindow.request_exit` (line ~593) | Decides which exit window to show: downloads running -> warning window; otherwise -> rating window. |
| 3a | `app\ui\dialogs.py` | `class ExitWarningDialog` (line ~111) | The window "downloads are still running" (Abort / Back). If you abort: `MainWindow.abort_all_downloads` (line ~581) stops all downloads and deletes partial files. |
| 3b | `app\ui\dialogs.py` | `class RatingDialog` (line ~234) | **The UI of the rating exit window**: logo, title, five stars (`StarRating`, line ~171), comment box, the two buttons. Already-given rating is shown again (parameter `previous`). |
| 4 | `app\ui\dialogs.py` | `RatingDialog._skip` (line ~327) | **Code of the "Skip and Exit" button**: sets `self.action = "skip"` and closes the dialog. Nothing is saved or sent. |
| 5 | `app\ui\dialogs.py` | `RatingDialog._submit` (line ~331) | **Code of the "Submit and Exit" button**: sets `self.action = "submit"` and closes the dialog. (The saving is done by step 6.) |
| 6 | `app\ui\main_window.py` | back in `request_exit` | If action is "submit" and a star was chosen: `FeedbackManager.save_rating(...)`. For "submit" or "skip": `_send_rating()`. Then the program closes (the X button of the dialog = stay open). |
| 7 | `app\feedback.py` | `FeedbackManager.save_rating` (line ~77) | Saves the rating to `data\feedback\my_rating.json` (shown again at the next exit) and to the history `feedback.json`. Returns True when it is new or changed. |
| 8 | `app\ui\main_window.py` | `MainWindow._send_rating` (line ~616) | If the rating is new/changed and a Google form is configured: sends it in a thread (waits 6 seconds at most). |
| 9 | `app\feedback.py` | `FeedbackManager.send` (line ~105) -> `post_form` (line ~36) | POSTs the answer to the Google form (`feedback_form_url` + `feedback_form_fields` in the settings) and marks it as sent. |

Button texts: `app\msg.py` -> `BTN_SKIP = "MSG_081"`, `BTN_SUBMIT = "MSG_082"`; the words are in `data\languages\en.json` and `ar.json`.
Where the buttons are created: `RatingDialog.__init__` in `dialogs.py` (`skip = QPushButton(...)`, `submit = QPushButton(...)`, connected to `self._skip` / `self._submit`).
The Google form link and field numbers go in `data\config\default_settings.json` (`feedback_form_url`, `feedback_form_fields`).

### 4.2 Main window and screens

| What you see | File | Where |
|---|---|---|
| Window background, title bar, language globe, download counter | `ui\main_window.py` | `Shell.paintEvent`, `TitleBar`, `TitleBar.set_counter` |
| Header: icon, name, version, advertisement space | `ui\main_window.py` | `MainWindow._build_header` (line ~200); the ad frame is `AdBanner` in `ui\widgets.py` |
| Side menu (New Download, Downloads, Archive, Library, Playlist Sync, Settings) | `ui\main_window.py` | `MainWindow.NAV`, `_build_sidebar` (line ~230) |
| Corner: "Powered by Let's Have Fun" + 5 links | `ui\main_window.py` | `_build_sidebar`, `INFO_LINKS`, `show_info` (line ~377) |
| Which screen opens at start | `ui\main_window.py` | `select_page(self.page_index("new"))` in `MainWindow.__init__` |
| Page change animation (fade) | `ui\widgets.py` | `class MorphStack` |
| Gauges panel | `ui\main_window.py` / `ui\widgets.py` | `_build_gauges` (line ~311), `_sample_gauges_impl` (line ~405) / `MiniGauge`, `SpeedGauge`, `draw_gauge_title` |
| Gauge numbers (network, disk, free space) | `app\sysmon.py` | `SysMonitor.sample` |

### 4.3 Downloading

| Feature | File | Function |
|---|---|---|
| Paste link, "Check" button, formats and sizes | `ui\new_download_page.py` | `_fetch` (line ~319), `_info_ready`, `_rebuild_quality` |
| Free-space check before download | `ui\new_download_page.py` / `app\downloader.py` | `_space_ok` (line ~476) / `free_bytes`, `space_needed`, `drive_name` |
| Start download button | `ui\new_download_page.py` | `_start` (line ~611) -> `_enqueue_video` / `_enqueue_playlist` |
| Pause / Cancel buttons of the page | `ui\new_download_page.py` | `_pause_clicked` (line ~551), `_cancel_clicked` (line ~564) |
| The queue (3 at a time, waiting list) | `app\dlqueue.py` | `DownloadQueue.add_video`, `add_playlist`, `pump`, `_start`, `skip`, `cancel_task`, `pause_task` |
| yt-dlp command line, progress, real size | `app\downloader.py` | `build_download_cmd`, `engine_options`, `DownloadJob`, `parse_progress_line`, `format_sizes` |
| Numbering 01 / 001 | `app\downloader.py` | `pad_width`, `index_text` |
| Bandwidth limit, concurrent downloads | `app\dlqueue.py` | `max_concurrent`, `bandwidth_mb`, `playlist_limit` (settings: `max_concurrent`, `speed_limit_mb`, `playlist_concurrent`) |
| Downloads screen rows, playlist card, details window, Skip this one | `ui\downloads_page.py` | `TaskRow`, `GroupRow`, `PlaylistDetailsDialog` |

### 4.4 Archive, Library, Sync

| Feature | File | Function |
|---|---|---|
| Archive (3 vaults) and Library (favorites by category) | `ui\library_page.py` | `LibraryPage(mode="archive"/"library")`, `FolderTile`, `_fill_filter` |
| Video card buttons: play, folder, sync, again, details, favorite, delete | `ui\library_page.py` | `VideoCard._play ... _delete` (delete at line ~277) |
| Delete also from the disk | `app\history.py` | `delete_files` |
| Details window (description, clickable folder / link) | `ui\dialogs.py` | `class DetailsDialog`; links in descriptions: `infodoc.description_html` |
| Playlist Sync screen | `ui\sync_page.py` | `SyncPage._row` |
| "Sync now" workflow | `ui\sync_flow.py` | `SyncController.run` (line ~66) |
| Favorite categories (add / edit / delete, icons) | `app\favorites.py`, `ui\settings_page.py`, `ui\dialogs.py` | `FavoritesManager`, `SettingsPage._add_category`, `CategoryDialog` |

### 4.5 Settings

| Feature | File | Function |
|---|---|---|
| Settings screen layout, fitting to the work area | `ui\settings_page.py` | `__init__`, `_fit` (line ~255), `_rescale` |
| Buttons "Apply and Save", "Reset to Default", "Cancel" | `ui\settings_page.py` | button row (line ~215); `save` (line ~446), `restore_defaults` (line ~489), `discard` (line ~501), `_done` (line ~506) |
| Button texts | `app\msg.py` / `data\languages\en.json` | `ST_APPLY` = MSG_297, `ST_RESET` = MSG_298, `BTN_CANCEL1` = MSG_109 |
| Saving to the config file | `app\settings.py` | `SettingsManager.set`, `save`, `reset_to_defaults` |
| Applying after Apply and Save (language, queue, ads) | `ui\main_window.py` | `_settings_saved` (line ~431), `change_language` (line ~444) |
| "Don't show again" tick <-> Settings tick | `app\settings.py` / `ui\settings_page.py` | `subscribe`, `_notify` / `_on_setting` |

### 4.6 Online folder, ads, update, info pages

| Feature | File | Function |
|---|---|---|
| Check at start (during the splash) | `app\loader.py` | `StartupLoader._online_work` |
| Read the Drive folder, download ads, allowed list, links | `app\ads.py` | `list_drive`, `sync_ads`, `parse_allowed`, `parse_links` |
| New-version question (Yes / No / don't show) | `ui\main_window.py` / `ui\dialogs.py` | `_check_done` (line ~487) / `UpdateDialog` |
| Ad frame (fit the gif, click opens link) | `ui\widgets.py` | `AdBanner` |
| Help / About / Contact / Donate text | `assets\info\*.txt` | edit the text files; format rules are at the top of `app\infodoc.py` |
| Reviews (downloaded `reviews.txt`) | `ui\info_page.py` / `app\ads.py` | `InfoPage._load_reviews` / `fetch_remote_text` |

### 4.7 Look and texts

| Change | Where |
|---|---|
| Colours, fonts of buttons and cards | `app\ui\theme.py` -> `STYLE` (style sheet) |
| Window background colours | `app\ui\main_window.py` -> `Shell.paintEvent` |
| Any visible word | `data\languages\en.json` / `ar.json` (id from `app\msg.py`) |
| Factory settings | `data\config\default_settings.json` (your own: `current_settings.json`) |
| Version number | `app\paths.py` -> `APP_VERSION` |
| Start-up order | `app\loader.py` -> `StartupLoader.run`; `main.py` -> `main` |

### 4.8 Start-up flow

`main.py: main()` -> error log + Qt style -> `SplashScreen` -> `StartupLoader.run` (default settings -> current settings -> languages -> resources -> history -> online check) -> `MainWindow(ctx)` opens on **New Download** -> splash closes.
Changing the language rebuilds the window: `main.py: change_language` + `MainWindow.change_language`.
