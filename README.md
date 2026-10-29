# TubeArchive Pro (v2.3.2)

Windows desktop app (Python + PySide6) that will download YouTube videos/playlists with **yt-dlp.exe**.
Working now: splash screen, main window, exit flow, the **New Download** tab (real downloads) and the **Downloads** tab (history + favorites).
The other tabs are still design-only.

## Versions
See `CHANGELOG.md`. Every code file starts with a header listing its own version history.

## Run
```
pip install -r requirements.txt
python main.py
```

## Start-up flow
1. Splash screen appears (name, icon, "Loading...", progress).
2. `StartupLoader` (background thread) loads, in order: default settings -> current settings ->
   language files -> resources -> history.
3. Main window opens, splash closes.

## Structure
```
main.py                     entry point
app/
  paths.py                  every path + app name/version
  msg.py                    message IDs (M.APP_NAME = "MSG_001" ...)
  i18n.py                   LanguageManager (discovers data/languages/*.json, tr(id))
  settings.py               default + current settings
  history.py                download history
  resources.py              ad GIFs, owner banner, yt-dlp.exe lookup
  loader.py                 start-up loader thread
  context.py                holds all of the above
  ui/ splash.py main_window.py pages.py widgets.py icons.py theme.py
data/
  languages/en.json ar.json     one file per language (new file = new language)
  config/default_settings.json  factory defaults
  config/current_settings.json  user settings (created on first run)
  history/history.json          old downloads (created on first run), history/thumbs/ = their pictures
  favorites/favorites.json      favorite categories and the videos in them
assets/ads/*.gif            partner animated GIFs (rotate in the footer frame)
assets/owner/banner.jpg|png|gif owner banner in the header (replace the file to change it; a placeholder is drawn if missing)
tools/yt-dlp.exe            downloader engine (required)
tools/ffmpeg.exe (+ffprobe) merge video+audio, convert to MP3/WAV/AVI (required)
tests/                      python -m unittest discover -s tests   (fake yt-dlp, no internet)
```

## Adding a language
Copy `en.json` to `fr.json`, change `meta` (`code`, `name`, `direction` = `ltr`/`rtl`) and translate
the messages. Keep the same `MSG_xxx` ids. Set `"language": "fr"` in current_settings.json.

## History record format
`id, url, title, file_name, save_dir, extension, quality, date` + `format, quality_value, size, duration, is_audio, is_playlist, count, thumb`

## Closing the app
Close button / Alt+F4 -> if downloads are running: red warning dialog (Back / Abort Downloads);
otherwise: 'Before You Go!' rating dialog (Skip & Exit / Submit & Exit; X stays in the app).
Ratings are saved to `data/feedback/feedback.json`. Set `"demo_downloads": false` in
`data/config/current_settings.json` to remove the demo rows of the Downloader tab.
Only real downloads (New Download tab) count as "active" when closing.

## New Download tab
Paste a link -> the program reads it (thumbnail, title, estimated size). Pick file type + quality, press Start.
Pause = process suspended (nothing is lost). Cancel = yt-dlp is killed and all partial files are deleted.
Files are first written in a hidden folder `.tubearchive_tmp_*` inside the save folder and moved to the save
folder only when finished. A video link that also contains `&list=` downloads just that video; a
`/playlist?list=` link downloads the whole playlist. To see the "File Successfully Downloaded!" window again
after ticking "Don't show again", set `"show_success_dialog": true` in `data/config/current_settings.json`.

## Menu
New Download | Downloads (current + queued downloads) | Library (history, newest first, vault folders) |
Archive (favorites) | Playlist Sync (synchronized playlists: ON/OFF, schedule, sync now; data in data/sync/sync.json) | Settings.
Library / Archive cards: Play, Open Folder, Download again (fills New Download with the same link / folder / format /
quality; you can change them), Favorite star, Delete. The success window also has "Add to Favorite" (categories are free text).
Demo history (12 samples) is created on the first start; delete them in the Library or edit data/history/history.json.

## Notes
- Rows, gauges and the system log on the Downloader page are DEMO data (`# DEMO` in code) and move
  on a timer so the design can be reviewed. Remove when real downloads are wired in.
- Analytical Monitor, Dashboard and Archive Queue are placeholders until their designs are drawn.


## Settings, gauges, language and ads (1.0.12)
* Settings are in `data/config/current_settings.json` (yours) and `data/config/default_settings.json` (factory values, used by
  *Restore Defaults*). Useful keys: `online_folder_url` (Google Drive folder with the new .exe, the ad gifs and their .txt links), `ads_prefix`, `ads_check_minutes`, `ads_rotate_seconds`.
* Ads are named `tubearchivepro-YYYY-MM_<x>.gif` and are downloaded to `assets/ads/` from `online_folder_url`.
* The globe icon in the title bar changes the interface language. New languages: add `data/languages/<code>.json`.

## Version 2.0.1 - queue, glass style, info pages
- Queue: `app/dlqueue.py` (no Qt) + `app/download_manager.py` (signals). Settings `max_concurrent` (3) and `speed_limit_mb` (0 = none).
- Pages: `app/ui/downloads_page.py` (queue), `app/ui/info_page.py` + `app/infodoc.py` (Reviews / Help / About / Contact / Donate from `assets/info/*.txt`).
- Online folder files: `tubearchivepro_vX.Y.Z.exe`, `tubearchivepro-YYYY-MM.txt` (allowed ads), `tubearchivepro-YYYY-MM_N.gif` (+ `.txt` = link),
  `downloads_counter.txt`, `reviews.txt`. Results are cached in `data/cache`.
- Progress of the work of this version: see `PROGRESS_2.0.1.md`.

## Version 2.0.2
- See CHANGELOG.md. Exit rating: `app/feedback.py` (data/feedback/my_rating.json); Google form: settings `feedback_form_url`,
  `feedback_form_fields` {"rating": "entry.NNN", "comment": "entry.NNN", "version": "entry.NNN"}.
- Progress record of the work: `PROGRESS_2.0.2.md`.

## Version 2.0.3
- See CHANGELOG.md and PROGRESS_2.0.3.md.

## Version 2.2.0
GitHub can be the online folder (ads, texts, versions from Releases, downloads counter from release download counts): see GITHUB_SETUP.md.

## Version 2.3.0
Setup wizard + exe build (folder `build\`, read `build\BUILD_GUIDE.md`); program data lives in `%APPDATA%\TubeArchivePro` when installed.

## Version 2.1.0
Message windows have no X button; the exit window has a Cancel button (see CHANGELOG.md).

## Version 2.0.5
Language change keeps the open work area; close/min/max buttons forget a stale hover after resizing; Settings uses one font
size and fits the work area; ffmpeg / yt-dlp are found in `tools\` or any sub-folder of it (see CHANGELOG.md).

## Version 2.0.4
- Button labels with '&' (mnemonic_safe) and Qt warning log (main.py `_install_qt_log`). See CHANGELOG.md.
