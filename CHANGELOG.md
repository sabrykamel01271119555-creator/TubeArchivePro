# TubeArchive Pro - change log

Convention: every prompt starts with the version, e.g. `TubeArchive pro version1.0.6`.
Each code file carries a header with its own version history, so you can see which files
changed in which version (JSON files cannot hold comments, so they are listed here instead).

## 2.3.2 (minor)
- **Splash screen**: shown first, the counter and the version bar run evenly from 1 to the number of users in 10 s (every number appears), start-up steps 40 ms instead of 380 ms; the users number is big and coral; the version
  bar uses red -> orange -> yellow -> green colours with a marker. `app/ui/splash.py`, `app/loader.py`.
- **Settings** page fits the frame at any window size. **Sync all** is ONE window (`SyncAllDialog`): progress bar, picture + info of the playlist, and in the work area the same content as the single sync window (`SyncPanel`: new videos with pictures) or the 'nothing new' message; chosen downloads start when it closes. New message MSG_521.
- **Failed videos**: window "N videos cannot be downloaded now" with *Retry now / Later (kept and reminded at the next start) / Cancel (ignored)*.
  `app/failed.py`, `app/dlqueue.py`, `app/ui/new_download_page.py`; new file `data/failed/failed.json`.
- **A video and the same video inside a playlist are one video**: a direct link is recognised as already downloaded when it was downloaded with its playlist
  (`HistoryManager.find_video`), and videos downloaded directly are counted as downloaded by the playlist sync (`absorb_singles`), so nothing is downloaded twice.
  The playlist question keeps its buttons: Download playlist / Check playlist / Download file only / Cancel.
- **Library / Archive**: double-click on a playlist card opens it in the same work area (its videos in order, same cards, pictures fetched in the background, "Back to the list" button). New message MSG_520;
  MSG_510 - MSG_519 translated into all languages.
- **Build scripts**: `build/get_tools.ps1` (downloads yt-dlp, ffmpeg + ffprobe, wizard languages, VC++ runtime when missing), `build/make_icon.py` (creates the .ico),
  `build/build.bat` runs both and has the option `exe` (program folder only); `BUILD_GUIDE.md` updated. `build/pack_requirements.bat` stores the pip packages of requirements.txt in `build/wheels`; `build.bat` then installs them offline (`--no-index`). `.github/workflows/build-setup.yml` builds the offline setup on GitHub (Actions), `.gitignore`, `GitHubRepo` = sabrykamel01271119555-creator/TubeArchivePro. Not run on Windows yet.

## 2.3.1 (minor)
- **Quality list**: 2K (1440p), 4K (2160p) and **8K (4320p)** (shown when the video really offers them, after 1080p), and the **estimated size beside every
  quality** (`1080p  ·  245 MB`). `app/downloader.py`, `app/ui/new_download_page.py`.
- **MP4 = H.264 + AAC** (editors: Premiere, After Effects, DaVinci Resolve; TVs and players): `downloader.h264_args()`. The H.264 stream is taken as it is when the video
  offers it at the best height wanted; YouTube gives 1440p / 4K / 8K only as VP9 / AV1, so those are downloaded and converted with ffmpeg to H.264 (yuv420p) + AAC
  (slower, bigger file). Settings > "MP4 = H.264 + AAC" (`mp4_h264`, default on); off = the old choice. Playlist entries prefer H.264 with the old choice as fallback.
- **Reviews** page = the real ratings / comments of your sheet: Apps Script `GET ?action=reviews` (newest 100, no install id), `stats.fetch_reviews`, cached for
  offline; without an Apps Script address it still reads `reviews.txt` of the online folder. Paste the new script and deploy a new version.
- **About us** = about + contact + donate in one tab (the side links are Reviews, Help, About us); the pale blue frames around e-mail / phone rows are gone.
- **Splash**: counting takes 6 - 10 s, the users frame pulses while it counts 1 -> total, and the number of the version the bar passes counts up too.
- Messages MSG_508 - MSG_509 (all languages). Tests: `H264Quality`, `test_reviews_of_the_sheet`, `AboutMerged`.

## 2.3.0 (minor)
- **Installation counting**: the program registers its install once (`install_id`, installation date, version, Windows OS, language, country) in
  your sheet through the Apps Script; the splash screen's user count = those installs + the old numbers of `total_users.txt`
  (`app/stats.py` `users_data`, `fetch_users_base`, `fetch_rating`). Settings > "Share anonymous usage information" (`share_usage`) switches it off.
  `owner_tools/feedback_apps_script.gs` rewritten: one row per install, columns `install_id, installation_date, version, os, language, country,
  rating_date, rating, feedback, new_features`; `GET ?action=stats` returns `users`, `versions`, `average`, `count`, `stars`.
  NOTE: paste the new script and deploy a NEW VERSION; run `setup` once. `current_settings.json` files saved earlier keep the old field names.
- **Splash / sounds**: users count slowly 1 -> total (label "users"); the bar fills version by version; the corner counter is hidden; new
  generated "glass" sounds, preloaded (no delay).
- **Sync**: "nothing new" window (last sync, next sync, schedule drop-down daily / weekly / monthly / **yearly**, automatic sync on / off);
  the checking window shows playlist, files already there, last sync, quality, folder (and "n of N" for Sync all).
  Files: `app/ui/sync_flow.py`, `app/ui/dialogs.py` (`SyncDoneDialog`, `BusyDialog(info=)`), `app/sync.py`.
- **Pasted video link that belongs to a playlist** (`new_download_page._playlist_gate`): playlist new -> Download playlist / Check playlist /
  Download file only / Cancel; playlist in the history -> says if THIS file was downloaded before + list info, Sync playlist.
- **Windows warning "UpdateLayeredWindowIndirect failed"** fixed: the blurred background is a scaled picture (`main_window._blur_background`)
  instead of `QGraphicsBlurEffect` on the translucent window.
- **Tool updates** (`app/toolupdate.py`, `app/ui/update_flow.py`, `UpdatesDialog`, `UpdateProgressDialog`): yt-dlp (GitHub release + SHA2-256 check) and
  ffmpeg / ffprobe / ffplay (BtbN build) are installed into `%APPDATA%\TubeArchivePro\tools` (searched before the program's tools folder). Window with
  the app version (up to date) and an UNticked "Update tools"; progress window = percentage + total size, no file names; no update while downloads run.
  Checked at start-up (window only when something is new), by Settings > "Check for updates now", and after a failed download (once per run).
- **System tray**: the minimize button hides the window and shows a tray icon (Open / Exit; click restores). Downloads continue.
- **Encrypted online files**: `app/secure.py` (HMAC-SHA256 stream + MAC); `ads.read_text_file` opens encrypted or plain files; the owner encrypts with
  `owner_tools/encrypt_online.py encrypt <file>` and uploads the result under the original name. (Obfuscation against casual readers only.)
- **Installer** (`build/installer.iss`): wizard language list (English, Arabic, Chinese / Hindi when their .isl are in build\, Spanish, French,
  Portuguese, Russian, German, Turkish); a components page - English + Arabic always, the other program languages optional; the chosen wizard language
  becomes the program language on first install. User data in `%APPDATA%\TubeArchivePro`. The .exe / setup are still NOT built (postponed).
- Help files (`assets/info/help.en.txt`, `help.ar.txt`) rewritten for 2.3.0; `docs/` documentation (separate zip).
- New messages MSG_478 - MSG_507 (English + Arabic; other languages use the English text until translated).
- Tests: `test_toolupdate.py`, `test_secure.py`, new cases in `test_stats.py`, `test_page_flow.py`.

## 2.2.9 (minor)
- **Rating -> your Apps Script**: ONE setting `feedback_form_url` (default = your web app address) and `feedback_form_fields` = the names of the
  sheet columns `date, version, os, rating, feedback, newfeatures`. An Apps Script address is posted as JSON with those keys
  (+ install_id, language); a Google form address is still posted as a form (entry ids). The user sees the stars, the comment box and
  the "new features" box; date, version and OS are filled by the program and stay hidden. `feedback_endpoint_url` (2.2.8) is removed.
- `owner_tools/feedback_apps_script.gs` now finds the columns by the names in row 1 (your sheet layout is kept; `install_id` and
  `language` are added at the end), writes text columns as plain text, and replaces the row of an installation that changes its rating.
  Files: `app/feedback.py`, `app/loader.py`, `app/stats.py`, `app/ui/main_window.py`, `data/config/default_settings.json`.
  NOTE: a `current_settings.json` that was saved earlier keeps its own values - paste the two settings there too.

## 2.2.8 (minor)
- **Splash screen** (`app/ui/splash.py`, new `app/stats.py`): left = users counter counting up from 1; right = rating of the users
  (stars + average + number of ratings) and one bar that fills version after version (label `Version x.y.z   from - to`, the counter
  and the bar run together). The numbers are those of the last online check (cached); the first start uses
  `data/splash_baseline.json`. Users per version = download count of the `.exe` files of each release + the numbers of
  `total_users.txt` (lines `1.0.0 = 25`) for versions that have no `.exe` release file (`ads.parse_user_totals`, `ads.build_user_stats`).
  The corner counter uses the same total.
- **Rating**: new setting `feedback_endpoint_url` (replaced in 2.2.9 by `feedback_form_url`; Google Apps Script web app, `owner_tools/feedback_apps_script.gs`): the program sends
  JSON (anonymous install id, version, OS, language, rating, comment, wanted features); a changed rating replaces the old row;
  `GET ?action=stats` gives the average / count for the splash screen. The rating window has a second box: "Which new features
  would you like?". The old Google form stays as a fallback. `app/feedback.py`, `app/ui/dialogs.py`, `app/loader.py`.
- **Favorites**: the drop-down lists of the categories (Add to Favorites window, Library filter, Settings) show the category icon beside
  the name (`make_emoji_icon`).
- **8 new interface languages** (translated by me - native speakers should proofread): Chinese (Simplified), Hindi, Spanish, French,
  Portuguese, Russian, German, Turkish. Order in the language list (icon in the window and Settings): English, Arabic, Chinese, Hindi,
  Spanish, French, Portuguese, Russian, German, Turkish. A new language = one more JSON file in `data/languages`.
- Language files: `meta.order` sorts the language list; a message missing in a language is shown in English (`app/i18n.py`).
- `owner_tools/feedback_apps_script.gs`: the script for the rating sheet (bound to your sheet by its id).
- New messages MSG_448 - MSG_477 (en + ar). Tests: `tests/test_stats.py`, total_users test in `tests/test_github.py`.

## 2.2.7 (minor)
- **Start-up**: the splash screen is the first thing shown (the big window module is imported after it is visible) and the online
  check (update, ads, counter) runs in the background - the splash no longer waits for it. `main.py`, `app/loader.py`.
- **Playlists due for sync**: the notice is now a window with three buttons - **Sync now** (in the background: only NEW videos are
  added to Downloads; a warning at the end lists downloaded videos whose files are not in the folder), **Let me check** (one window
  per playlist) and **Later** (nothing changes). `app/ui/main_window.py`, `app/ui/sync_flow.py` (`run_background`).
- **Sync window** (`SyncDialog`): compares ALL videos of the playlist - new, skipped before, downloaded but missing from the folder,
  and the ones in the folder - with a summary line. Buttons: **Sync** (everything that is not in the folder), **Download selected**
  (the ticked videos, by their position in the whole playlist), **Skip New**, **Later**. `app/ui/dialogs.py`.
- **Ads** fill the whole ad frame (stretched or shrunk). `app/ui/widgets.py`.
- **Archive / Library**: a click on Video / Audio / Playlist always filters by that kind (no more toggling back to all).
- **Sync buttons** (Archive, Library, Playlist Sync): synchronised = full green button with a lit white sign and glow; not
  synchronised = normal border, no background. `app/ui/icons.py` (`set_sync_button`), `theme.py` (`iconBtnOff`).
- **Sound effects** (new `app/sounds.py`, `assets/sounds/*.wav`): button click, tab change of the side menu, completed
  download / playlist / sync, warning and error windows. Settings > Notifications > "Sound effects" (`sounds_enabled`, default on).
- **Side menu**: the channel banner replaces "Powered by Let'sHaveFun"; a click opens
  https://www.youtube.com/@LetsHaveFun-ActiveMind (`assets/owner/channel_banner.jpg`, `ChannelBanner`).
- New messages MSG_428 - MSG_447 (en + ar). Tests: background sync, sounds, sync window list.

## 2.2.6 (minor)
- **Archive / Library**: the sync button of a synchronised playlist is **completely green** (not only a green border). `app/ui/theme.py`.
- **Side menu**: every item is a glass plate like the design picture (quiet when idle, brighter on hover, glowing with a bright
  edge bar when active). `app/ui/widgets.py` (`NavButton`).
- **Ads list** (`TubeArchivePro-YYYY-MM.txt` in the online folder): one line per ad, `number  source  url` - number = display
  order, source = where the image is downloaded from (GitHub `blob` / Google Drive file pages are converted to direct links),
  url = opened when the user clicks the ad. Separators: spaces, tab, comma, `;` or `|`; lines starting with `#` are ignored.
  A source that cannot be reached keeps the earlier copy. The old format (gif files in the folder) still works.
- **Update check**: the online folder is the GitHub folder `.../TubeArchivePro/blob/main/`; a file named
  `TubeArchivePro x.y.z.exe` (also `TubeArchivePro_Setup_x.y.z.exe`) with a higher version than the installed one starts the update
  notice; its link is the download address. The downloads counter still uses the releases.
- Default `online_folder_url` = that GitHub folder (an old saved Google Drive link is replaced). Files: `app/ads.py`,
  `app/settings.py`, `app/paths.py` (APP_VERSION), `data/config/default_settings.json`.
- Postponed on request: update check / download of yt-dlp, ffmpeg, ffprobe, ffplay, and the setup wizard (the 2.3.0 build scripts stay unused).

## 2.3.0 (major) - installer
- **Setup wizard** (Inno Setup) + PyInstaller build, all in the new folder `build\`: `build.bat` (one click: venv, requirements, checks,
  tests, PyInstaller, Inno Setup), `TubeArchivePro.spec`, `installer.iss`, `installer_settings.iss` (publisher, website, **GitHubRepo**),
  `check_build.py` (checks / copies `yt-dlp.exe`, `ffmpeg.exe`, `ffprobe.exe` into `tools\`), `LICENSES.txt`, `INSTALL_INFO.txt`,
  `BUILD_GUIDE.md` (preparation, ffmpeg essentials vs full, publishing). Output: `build\output\TubeArchivePro_Setup_<version>.exe`.
- **Data location (option B)**: the installed program is read only (`C:\Program Files\TubeArchive Pro`); everything it writes (settings, history,
  favorites, sync, feedback, cache, logs, downloaded ads) goes to `%APPDATA%\TubeArchivePro`. `python main.py` from the source folder works
  exactly as before; `portable.txt` next to the exe = data next to the exe; an older portable copy is migrated once.
  Files: `app/paths.py` (`APP_DIR`, `USER_DIR`, `resolve_user_dir`, `migrate_old_data`), `main.py`, `app/ads.py`, `app/resources.py`,
  `app/settings.py`. Test: `tests/test_paths.py`.
- **Update check at setup start**: the wizard asks GitHub for the newest release of `GitHubRepo` and offers to open its download page.
- `requirements.txt`: PySide6, psutil, PyInstaller (+ the external tools listed).

## 2.2.5
- **Cancel in the Downloads list asks first and then removes.** The X of a video, the X of a playlist and **Cancel all** now open a warning
  window (*Yes, cancel and remove* / *No, continue*). After *Yes* the download is stopped, its unfinished file is deleted and it is
  **removed from the list**; a playlist that is cancelled this way is **not saved in the history** (no success window, no history entry).
  Files already completed inside the playlist stay on the disk (only the unfinished ones are deleted). A *sync* download that is
  cancelled still updates the synchronised playlist with the videos it finished (so they are not offered again), but disappears
  from the list. The Cancel button of New Download is unchanged (it keeps its own confirmation).
  Files: `app/dlqueue.py` (`discard_task/group/all`, `purge_discarded`), `app/ui/downloads_page.py`, `app/ui/new_download_page.py`,
  `app/msg.py`, `data/languages/*.json` (MSG_424-427). Test: `tests/test_queue.py`.

## 2.2.4
- **Resume with no free place**: the paused video now takes the **next free place before the waiting (queued) videos**, so it really
  resumes by itself (before, the waiting videos could take every freed place and it stayed paused). While it waits its row says
  *Paused - resumes when a place is free* (MSG_423). Files: `app/dlqueue.py`, `app/ui/downloads_page.py`, `app/msg.py`,
  `data/languages/*.json`. Test: `tests/test_queue.py`.

## 2.2.3
1. **New Download counters** now have three blocks with icons: **Downloading now** (arrow), **In the queue** (list), **Paused** (pause).
   The title says *Downloading* while any of them is not zero. Every video of a playlist is one file.
2. **Priority**: a paused video no longer holds one of the `max_concurrent` places, so a video you add while others are paused starts
   at once. *Resume* of a paused video when all places are taken keeps it paused and it resumes by itself as soon as a place is free
   (waiting new videos come first). *Pause all* freezes the running videos; the waiting ones stay waiting until a video is added or
   a place is freed. Files: `app/dlqueue.py` (`RUNNING`, `_do_resume`, `counts_by_state`).
3. **Exit**: if paused downloads exist, the exit warning also says how many are paused (they will not be finished).
4. **Downloads page**: check box **Clear completed automatically** (saved as `auto_clear_completed`, default OFF) - a finished video
   or playlist leaves the list 1.5 s after it completed (the same list the *Clear completed* button clears: also failed / cancelled
   rows). The same option is in **Settings** (Advanced Connection & Downloads); both stay in step and are saved in `current_settings.json`.
5. **Completed bar**: in the Downloads list the progress bar turns **green** (and shows a tick, 100%) when the video is completed;
   orange when paused; red when failed / cancelled. A finished playlist bars are green.
Messages MSG_419-422 (en + ar). Files: `dlqueue.py`, `new_download_page.py`, `downloads_page.py`, `settings_page.py`, `dialogs.py`,
`main_window.py`, `icons.py`, `theme.py`, `msg.py`, `default_settings.json`.

## 2.2.2
1. **New Download**: after Start, the frame that showed the file info now shows **big counters**: files downloading now and files in the
   queue. The title above it says **Downloading** while anything is running or waiting; when everything is finished it returns to normal
   and the frame is empty again. (Reading another link shows its info in the frame as before.)
2. **Side menu**: *Downloads (n)* = files downloading now + waiting; refreshes whenever a file starts or finishes.
3. **Archive / Library, playlist card**: the sync button is **lit** (green) when the playlist is set up to synchronise and switched on.
   Pressing it syncs now; a playlist that was not set up is **also added to Playlist Sync** (daily) and the button turns on.
4. **Playlist Sync page**: new **Sync all** button: checks every switched-on playlist now, one after the other (a playlist without new
   videos opens no window), then a summary tells how many were checked and how many have new videos.
5. **Settings**: larger fonts; the text no longer shrinks below 85 % (the page scrolls instead); two columns only on a wide work area.
(Counters count FILES: every video of a playlist is one file, a playlist is never counted as 1; tested in `tests/test_queue.py`.)
Files: `new_download_page.py`, `main_window.py`, `library_page.py`, `sync_flow.py`, `sync_page.py`, `settings_page.py`, `theme.py`, `msg.py`, `data/languages/*.json` (MSG_412-418).

## 2.2.1
- **Ads / GIFs from GitHub, checked at every start**: each ad is compared with the online file by its fingerprint (sha from the GitHub
  contents listing). Different (even with the same size) -> downloaded again; same -> not downloaded. Old ads of past months are removed.
- **Downloads counter = only the setup files (.exe) of the releases** (zip, checksum and text files are no longer counted).
  `ads.COUNT_ASSETS`. Files: `app/ads.py`, `tests/test_github.py`, `GITHUB_SETUP.md`.

## 2.2.0
- **GitHub as the online folder** (ads, update check, downloads counter). `online_folder_url` can be a GitHub repository / folder address.
  Newest version = newest published Release; downloads counter = `download_count` of the release files (+ optional earlier total from
  `downloads_counter.txt`); `file_download_count()` gives the downloads of one file. Google Drive and plain web folders still work.
  Full explanation: `GITHUB_SETUP.md`. File: `app/ads.py`. Test: `tests/test_github.py` (a local server plays the GitHub API).

## 2.1.1
- (withdrawn) a first draft `app/github_source.py` was replaced by the GitHub support inside `app/ads.py` (2.2.0): delete
  `app/github_source.py`, `tests/test_github_source.py` and `ONLINE_SETUP_GITHUB.md` if you copied them.

## 2.1.0 (major)
- **No X button in message windows.** The exit window ("Before You Go"), the success window and the sync window no longer show an X:
  every message window has its own button(s) that do the same job (Cancel / OK / Close). The exit window got a **Cancel** button
  (stay in the application) next to Skip and Exit / Submit and Exit. Esc still closes a window like Cancel.
  Audit of all windows: exit warning (Back), exit rating (Cancel), success (OK), choice windows (Cancel or No), update (No),
  favorite / category / playlist setup / sync (Cancel), busy (Cancel), details (Close), plain messages (OK).
  Files: `app/ui/dialogs.py`, `app/paths.py`.

## 2.0.12
- **Exit window X button**: it was placed once for the design size, so when the main window was maximised (dialog resized) it floated
  away from the corner. It is now re-placed at every resize, inside the top-right corner of the card. File: `app/ui/dialogs.py`.
- Delivery rule agreed: minor updates = changed files only; major updates = the full application zip.

## 2.0.11
- A video that is in the history but whose file is no longer in its folder now shows the same window (picture, all info, "the file is no
  longer in its folder"): **Redownload**, **Play** (dimmed), **Open folder** (opens the folder, window stays), **Cancel**.
  Files: `app/ui/dialogs.py` (ChoiceDialog dimmed / stay-open buttons), `app/ui/new_download_page.py`, `app/msg.py`, `data/languages/*.json`.

## 2.0.10
- The "already downloaded" window now shows the video thumbnail. The file is tested in its saved folder: if it was removed from the
  folder or drive, the old entry is ignored and the link is handled as a new download (a note is written in the log, MSG_410).
  Files: `app/ui/dialogs.py`, `app/ui/new_download_page.py`, `app/msg.py`, `data/languages/*.json`.

## 2.0.9
- **Check button diagnostics**: every Check (command, result, yt-dlp error text) is written to `data/fetch.log`; an unexpected error is
  now shown in a window instead of nothing happening. Files: `app/downloader.py`, `app/download_manager.py`, `app/ui/new_download_page.py`.

## 2.0.8
- The label "Container Format:" on New Download is now **File Type:** (MSG_088 in `data/languages/en.json`; Arabic already said "صيغة الملف").

## 2.0.7
- A redownloaded video now replaces its old history entry (see 2.0.6 below; file `app/ui/new_download_page.py`).

## 2.0.6
- **Check / Start and downloaded videos**: when the link of a single video is already in the history (same video id, whatever form of
  the link) and its file still exists, a window says it was already downloaded (date, title, format, folder) with
  **Redownload / Play / Cancel**. Redownload goes on (the old file is replaced), Play opens the file, Cancel does nothing.
  The finished redownload replaces the old history entry (no duplicate; a favorite stays a favorite).
  A new video (or one whose file was deleted) is checked as before. Files: `app/ui/new_download_page.py`
  (`_duplicate_ok`), `app/history.py` (`video_key`, `find_video`), messages MSG_407-409 (en + ar). Test: `tests/test_history.py`.

## 2.0.5
- **Language change** (language icon or Settings > Apply and Save) keeps you in the same work area (also Reviews/Help/... pages).
  Files: `main.py`, `app/ui/main_window.py` (`page_state`, `restore_page`).
- **Title-bar buttons**: after the window is resized/maximised/restored the highlight (hover) of close/min/max no longer stays
  at the old place. Files: `app/ui/widgets.py` (`WinButton.sync_hover`), `app/ui/main_window.py` (`TitleBar.resizeEvent`).
- **Settings page**: one font size for all texts, boxes, check boxes and buttons; the fit also measures wrapped text and width and
  runs when the page is shown. File: `app/ui/settings_page.py`.
- **tools folder**: `yt-dlp.exe` and `ffmpeg.exe` are searched in `tools\` and in any sub-folder (so the extracted
  `ffmpeg-...-full_build\bin` works as it is; best is still to copy `ffmpeg.exe` and `ffprobe.exe` into `tools\`).
  File: `app/resources.py` (`find_tool`). Test: `tests/test_tools.py`.

## 2.0.4
- **Button labels**: Qt hides a single "&" in a button text (it marks a keyboard shortcut), so the buttons showed "Apply  Save",
  "Skip  Exit", "Submit  Exit". The three buttons now use the word "and" (no "&" at all, so it cannot be swallowed):
  **Apply and Save**, **Reset to Default**, **Cancel** (Settings) and **Skip and Exit**, **Submit and Exit** (exit window).
  Other buttons that contain "&" (e.g. "Download & Sync (n)") are protected by doubling the "&" in the code.
- **Console message** `QFont::setPointSize: Point size <= 0 (-1)`: harmless (a widget styled in pixels has no point size). It is no
  longer printed; it is written ONCE per place to `data/error.log` with the Python line that caused it, so the source can be found.

## 2.0.3
- The program starts on the **New Download** page.
- **Gauges**: the title of every gauge is under it, close to it, in the same font size for all (it follows the window size).
  The **Free space** gauge fills with the USED part of the partition (compared with its total size) and its number is the free space;
  no red warning colour any more.
- **Page change**: no picture of the page is taken and nothing white flashes - the real page fades in softly on the colour of the work area.
- **Settings**: the page measures its content and lowers the size of the components until every card is visible without scrolling, at any
  window size (also maximized).
- **Library**: the favorite-category drop-down shows each category's own icon (the star is kept only for "all favorites").
- **Playlist Sync**: smaller text and a wider date column; "Last sync / Next sync" are no longer cut with "...".
- **Details**: web addresses and e-mail addresses inside a video description are clickable links.

## 2.0.2  (corrections of 2.0.1 + new notes)
- **Look**: the glass-morphism style of 2.0.1 is withdrawn - the window has the 1.0.14 look again (all 2.0.1 functions are kept).
- **Header**: application icon, name (smaller), the version below it (smaller) and the **advertisement space** for the rest of the
  header. The owner banner and the footer ad frame are gone, the work area is taller. The ad picture is fitted to the frame
  (stretched when it is nearly the frame's shape, otherwise shown whole with its own proportions).
- **Gauges**: every gauge is a small measuring meter (tick scale, needle, numbers at both ends). *Downloaded* = downloaded since start
  compared with the free space at start (both numbers shown); *Free space* = free compared with the whole partition (both numbers shown).
- **Ads**: the Drive folder is read from several page variants; if the month's list `tubearchivepro-YYYY-MM.txt` is missing every
  ad of the month is shown (with the list, only the listed ones). If nothing can be read, data/drive_page_debug.html and data/updates.log
  show why. (Not testable without your Drive: please send data/updates.log if the ads stay empty.)
- **Details** window: the folder is a link (opens the folder) and the web address is a link (opens the browser).
- **Work-area scaling**: every page and window follows the size of the work area (Downloads, playlist details, Settings, Playlist Sync, info pages ...).
- **Real size while downloading**: the size shown follows what yt-dlp learns during the download ("downloaded / total").
- **New Download**: the URL box is free again as soon as a video is added; four buttons like 1.0.14 (Start download, Pause, Cancel,
  Open folder) acting on the queue; a **Check** button beside the URL fills the format / quality lists with the values that really exist, keeps the
  estimated sizes and checks the free space of the target drive (needs about double the file size); a warning offers a lower quality or
  another drive; playlists get the total estimated size. The Downloads page keeps every file of this run (also finished ones) until
  **Clear completed**; a new run starts empty.
- **Delete** (video): asks if the file on the disk should be deleted too. **Delete** (playlist): asks if all its files and its subfolder
  should be deleted too.
- **Settings**: "Apply & Save" applies the settings now (language, queue, ads ...) and saves them in current_settings.json. Ticks such
  as "Don't show this message again" and the Settings page always show the same value (and the configuration file).
  New setting *Videos of one playlist at the same time* (default 1).
- **Exit window**: buttons "Skip & Exit" / "Submit & Exit". The last rating is kept in data/feedback/my_rating.json and shown again; a new or
  changed rating is sent to the Google form (settings `feedback_form_url` and `feedback_form_fields` - fill them when the form exists).
- **Info pages**: Donate with InstaPay / Vodafone Cash icons, Contact without the phone number (WhatsApp link + Facebook), About with a fuller
  description and the corrected YouTube link. (Icons in assets/info/icons are simple drawings: replace them with the official logos.)
- Postponed on request: the update check and the downloads counter are unchanged until your next prompt.

## 2.0.1  (major update)
- **Bright glass-morphism style** for the whole window (frosted translucent panels, luminous edges, vivid gradient background).
- **Download queue** (`app/dlqueue.py`): one yt-dlp process per video. At most `max_concurrent` run at once (default **3**, Settings);
  the others wait and start by themselves when a download ends. A single playlist is split into one task per video, so it also
  downloads several files at once. Pause / resume / cancel work for each file.
- **Bandwidth limit** (Settings > Max network bandwidth, MB/s, 0 = no control): shared by all running downloads.
- **Downloads page**: running / waiting counters, one row per video, one card per playlist (file counter, bar of the current file +
  bar of the whole playlist, thumbnail of the newest started file) and a **Details** window with every video, its own bar and
  **Skip this one**. Sizes are shown as "downloaded / total" (stable ratio instead of the changing yt-dlp estimate).
- Playlist files are numbered 01, 02 ... (001 ... when the playlist has 100 or more videos, and so on).
- **Archive** (above Library in the menu) = everything downloaded through the program in three vaults: Videos, Audio, Playlists
  (no favorites drop-down). **Library** = only files put in a favorite category.
- **Details** button on every Archive / Library card shows the description saved with the video (read from yt-dlp).
- Gauges: *Downloaded* = bytes downloaded since the start compared with the free space at the start; *Free space* = free / total of
  the save partition; new gauge beside Disk I/O: files downloading / (downloading + waiting).
- Online check now runs **while the splash screen is shown**. Only the ads listed in `tubearchivepro-YYYY-MM.txt` are shown
  (older / unlisted gifs are ignored). Ads are shrunk / stretched to fit the frame.
- **Downloads counter** in the title bar. Chosen design: the online file `downloads_counter.txt` (old versions + new versions, counted
  by the owner) is read at start, cached in `data/cache`, and `data/downloads_baseline.txt` (shipped with the setup) is used until the first
  successful read. Lines like `v1.0.12 = 320`; `total = N` overrides the sum.
- Corner of the side menu: "Powered by Let's Have Fun" with the channel's round logo and five links: **Reviews** (downloaded from
  `reviews.txt` of the online folder, cached), **Help**, **About us**, **Contact us**, **Donate** (local files in `assets/info`, English and
  Arabic, shown in the work area as styled pages; the texts are drafts to be rewritten later).
- Settings page follows the size of the work area; button caption **Apply & Save**. Playlist Sync: ON/OFF is a green toggle switch.

## 1.0.14
- Online folder is now Google Drive (`online_folder_url` in default_settings.json). It is read ONCE, when the program starts:
  * a file `tubearchivepro_v1.xx.xx.exe` with a higher version than ours -> "new version available" (Yes / No / don't show again);
  * every `tubearchivepro-YYYY-MM_xxx.gif` of the current month is downloaded to assets/ads and shown in turns;
  * the `.txt` file with the same name (`tubearchivepro-2026-10_1.txt`) holds the web address of that ad: clicking the ad opens it.
  The check is written to data/updates.log. The Drive folder must be shared with "anyone with the link".
- Settings page redrawn like the "Advanced Settings" mock-up: Audio Quality Settings (preferred audio format, bitrate + HQ badge,
  convert / extract switches), Default Save Location (Browse, subfolders for playlists, overwrite), Advanced Connection & Downloads
  (max concurrent downloads, speed limit slider, yt-dlp fallback, embed metadata & artwork), Save & Apply / Reset to Default / Cancel.
  Added: Interface & Video Defaults (language, default video format / quality, ads), Favorite Categories and Notifications.
  The options really change the yt-dlp command: -N (concurrent), --limit-rate, --embed-metadata / --embed-thumbnail, retries,
  --force-overwrites, mp3 bitrate (or best quality when "always convert" is off), -k (keep the video when "extract audio" is off).
- Favorite Categories: drop-down with each category's icon, small Edit and Delete buttons, "Add new category" (name + icon chosen from
  a built-in list of 24 emoji icons), and the check box "Don't notify me to add downloaded video to category" (hides the
  "Add to Favorite" button of the success window). The icon is shown on the Library / Archive cards.

## 1.0.13
- Real-data mode: no demo data any more. `demo_mode` (default false) replaces demo_data / demo_downloads; the sample records of
  earlier versions are removed from the history, favorites and sync list at start (your real downloads are never touched);
  the Downloads tab shows no demo rows (`demo_rows`). The zip no longer contains any history / favorites / sync file.
- Online check at start (and every `ads_check_minutes`): the folder link `ads_url` (default: the 4shared TubeArchivePro folder)
  is read.
  * A file `tubearchivepro_v1.xx.xx.exe` with a version higher than ours (now 1.0.13) -> a message "new version available" with
    Yes / No and "Don't show this message again" (setting `update_notify`, also a check box in Settings > Notifications).
    Yes opens the download page of that file in the browser.
  * Every file `tubearchivepro-YYYY-MM_<x>.gif` of the current month is downloaded to assets/ads (changed files are refreshed,
    ads of old months are deleted) and shown in turns in the advertisement frame.
  * 4shared folder pages are supported (links to file pages; the picture address is read from the file page).
  * Every step is written to data/updates.log (open it if ads or updates do not appear); a failure also shows as a line in the log.

## 1.0.12
- Settings page (working): interface language, default save folder (Browse), default format and default quality, show ads,
  and Notifications: file downloaded successfully / playlist updated (sync completed) / playlist has new videos (playlists whose
  next-sync date has come are announced at start). Save writes data/config/current_settings.json; Restore Defaults copies
  data/config/default_settings.json back (after a confirmation). New Download now starts from the default folder / format / quality;
  a folder typed there is used for that download only.
- Gauges panel (real values, once a second): upper = network speed of the computer | speed of this application;
  middle = downloaded since the program started | free space of the partition of the save folder;
  lower = disk I/O (read + write). The scale of every gauge follows the value. (psutil)
- Language icon (globe) in the title bar: choose the language, the window is rebuilt at once (not while a download is running).
- Partner ads: the GIFs named <ads_prefix>-YYYY-MM_<x>.gif (default tubearchivepro-2026-10_1.gif ...) are downloaded from the folder
  link `ads_url` (default_settings.json / current_settings.json) at start and every `ads_check_minutes`; changed files are refreshed
  (ETag / Last-Modified), ads of old months are deleted, your own GIFs in assets/ads are kept; the ads are shown in turns.
  The folder link may be a web page listing the files, or the files are looked for as _1, _2, _3 ... until one is missing.
- Playlist video count ignores private / deleted videos. BusyDialog.cancelled added (sync check could not be cancelled before).

## 1.0.11
- Playlists: when a playlist link is entered the history is checked (by playlist id).
  - NEW playlist -> options window: "create a folder for this playlist" (inside the save directory, or files go straight in it) and
    "add to sync" with Daily / Weekly / Monthly (next sync = +1 day / +7 days / +1 month).
  - Playlist already downloaded -> the app reads the playlist, compares it with the videos stored in the history and shows the
    sync window: "N new videos found", new videos ticked, previously downloaded unticked; Download & Sync (N) / Skip New / Cancel.
  - A "Sync now" button (two arrows in a circle) is on every playlist card in Library and Archive.
- Playlist Sync page: list of synchronized playlists (last sync, next sync, format, quality, frequency, ON/OFF, sync now, open folder, stop).
- New data file data/sync/sync.json; history records of playlists now hold playlist_id, videos {id: title/file/size/date/state}, last_sync.
- Engine: --playlist-items for selected videos, --print-to-file id|path, optional playlist folder; playlist count ignores private/deleted videos.
- Demo data v2: 14 samples (4 playlists, synchronized). Settings demo_data / demo_seed_version replace demo_history.
- Automatic scheduling only marks playlists "Due"; nothing is downloaded without your confirmation.

## 1.0.10
- Fixed the console message "QFont::setPointSize: Point size <= 0 (-1)": the application now has a valid default font (main.py).
- Side menu is now: New Download, Downloads, Library, Archive, Playlist Sync, Settings (Dashboard and Analytical Monitor removed).
  - Downloads = current downloads + downloads waiting in the queue (the former "Downloader"; still demo rows).
  - Library = history of finished downloads, newest first (the cards made in 1.0.9) with "My Digital Vault" folders
    (Videos / Music MP3 / Playlists with counts - click one to filter) and "Recently Archived" (search, sort by date / size / name,
    favorites filter), like the Library & Archive mockup.
  - Archive = the favorites (every category), same cards; filter by category.
  - Playlist Sync = placeholder until its design is drawn.
- Drop-down lists now show an arrow (and a divider) so it is clear they can be clicked.
- Changing the work area is animated: the new page starts small and blurred in the middle, then spreads and becomes sharp over the whole area.
- Demo data: on the first start 12 sample downloads (videos, music, playlists) are written to the history and some are put in
  favorites (Cinema / Music / Science); the Downloads page has two demo queued items. Setting demo_history (true -> false after
  the first start; set it to false in default_settings.json before the first start to skip the samples).
- New files: app/ui/library_page.py (replaces downloads_page.py), app/demo.py. Changed: msg.py, loader.py, paths.py, main.py,
  ui/main_window.py, widgets.py, icons.py, theme.py, dialogs.py, pages.py, new_download_page.py.
  JSON: en.json + ar.json (MSG_182 - 194; MSG_013 "Archive", 014 "Library", 016 "Settings"), default_settings.json (demo_history).

## 1.0.9
- New Download tab: the red round button beside the link is removed (the link is read automatically, or press Enter);
  the Format (type) list now comes before the Quality list; every element (fonts, heights, picture, buttons, log)
  scales with the size of the page; the video frame is EMPTY until a link has been read; Start Download is only
  available when a video is ready, Pause / Cancel only while a download runs.
- NEW "Downloads" menu item: history of every finished download, newest first, as glass cards that fade in
  (thumbnail, quality badge, title, format / quality / date, size, duration) with 5 small buttons:
  Play, Open Folder (selects the file), Download again (opens New Download with the same link, folder, format and
  quality - all can be changed), Add / Remove favorite (star) and Delete (remove from list, or delete the file too).
  Search box + filter (All downloads / All favorites / each favorite category). The card grid re-flows with the window.
- Favorites: categories chosen or typed by the user; saved in data/favorites/favorites.json.
- "File Successfully Downloaded!" window has a new "Add to Favorite" button (choose / create a category).
- Every finished download is written to data/history/history.json (new fields id, format, quality_value, size,
  duration, is_audio, is_playlist, count, thumb) and its thumbnail to data/history/thumbs/.
- New files: app/favorites.py, app/ui/downloads_page.py, app/ui/actions.py, tests/test_history.py (29 tests in total).
- Changed files: app/paths.py, msg.py, history.py, context.py, loader.py, ui/new_download_page.py, dialogs.py,
  icons.py, theme.py, main_window.py. JSON: en.json + ar.json (MSG_151 - MSG_181).
- Side menu order is now: Dashboard, New Download, Downloads, Downloader, Archive Queue, Library, Monitor, Settings.

## 1.0.8
- NEW "New Download" tab (replaces the design-only page) with the real download engine (yt-dlp.exe in the background):
  - URL box (auto-reads the link), Save Directory + Browse, Container Format (MP4, MKV, WEBM, AVI, then the audio
    formats MP3, WAV at the bottom) and Quality list that changes with the container:
    video = Best Quality + 144p ... 1080p, 1440p, 4K (only up to what the video offers),
    MP3 = 320 ... 64 kbps, WAV = 48 / 44.1 / 22.05 kHz.
  - "Ready to download" card: video thumbnail, title, estimated size + duration, then % @ MB/s, ETA, downloaded / total.
  - Start Download / Pause (suspends the process, does not end it; button becomes Resume) / Cancel (kills yt-dlp and
    deletes all partial files) / Open Folder (the Save Directory).
  - System Log: only meaningful messages in the user's language, no raw yt-dlp text; errors are explained
    (unavailable, private, age-restricted, network, disk, missing ffmpeg/yt-dlp, ...) in the log and in an error window.
  - "File Successfully Downloaded!" window: file name, quality, size, location, Play Video / Open Folder / OK,
    "Don't show this message again" (setting show_success_dialog).
  - Playlist links (youtube.com/playlist?list=...) download every video into a folder named after the playlist.
- Closing the program: the warning window now reacts to real downloads; "Abort Downloads" stops them and deletes partial files.
- Speed gauge and graph show the real download speed once a download has started.
- New files: app/downloader.py (engine logic, no Qt), app/download_manager.py (Qt signals), app/ui/new_download_page.py,
  tests/ (22 tests with a fake yt-dlp: python -m unittest discover -s tests).
- Changed files: app/paths.py, app/msg.py, app/resources.py, app/ui/icons.py, widgets.py, theme.py, dialogs.py,
  pages.py, main_window.py, requirements.txt (+ psutil, ffmpeg note).
- JSON: data/languages/en.json + ar.json (MSG_082 - MSG_150), data/config/default_settings.json
  (show_success_dialog, last_format, last_quality; default_format / default_quality removed).

## 1.0.7
- Header banner is now the real Let'sHaveFun picture stored in `assets/owner/banner.jpg`
  (replace that file to change the banner; .png/.gif also work, name it `banner.*`).
- The banner keeps the picture's proportions and, when the window is narrow, crops the right side only.
- Files changed: assets/owner/banner.jpg (new), app/paths.py, app/ui/widgets.py, app/ui/main_window.py.

## 1.0.6
- Responsive interface: header, banner, side menu, gauges panel and footer ad follow the window size.
- Gauges (speed, ring, sparkline) are drawn relative to their size: no overlap at the normal size.
- Side-menu text shrinks to fit its button.
- Version header comments added to every .py file; APP_VERSION = 1.0.6.
- Files changed: app/paths.py, app/ui/widgets.py, app/ui/main_window.py (+ headers everywhere).

## 1.0.0 - 1.0.5
- Splash screen, main window, language/settings/history loading, exit warning + rating dialogs,
  startup crash fix, window-button (X / min / max) fix.
- JSON files: data/languages/en.json, ar.json (exit-dialog messages MSG_064-MSG_081),
  data/config/default_settings.json (demo_downloads).

## Docs (2.0.4)
- Added FEATURE_MAP.md: every screen/button -> handler -> next calls (Part A narrative + Part B generated).
