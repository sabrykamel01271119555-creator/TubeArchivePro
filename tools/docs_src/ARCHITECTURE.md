# Architecture

## Layers
- **Engine** (`app/`): `paths`, `settings`, `i18n`, `downloader` (yt-dlp commands), `dlqueue` (the queue), `history`, `favorites`, `sync`,
  `ads` (online folder), `stats` / `feedback` (numbers and rating), `toolupdate`, `secure`. No window code.
- **Screens** (`app/ui/`): `main_window` owns the pages; pages talk to the engine through `AppContext` (`app/context.py`) and to each other
  through Qt signals (e.g. `history_changed`, `sync_requested`, `tools_check_requested`).
- **Texts**: screens call `ctx.lang.tr(M.SOME_ID, name=value)`; nothing visible is written in the code.

## Start-up
1. `main.py` creates the Qt application and the splash screen (`app/ui/splash.py`) with the numbers of the last online check (`stats.splash_data`).
2. `Loader` (`app/loader.py`, a thread) loads default + user settings, the language, resources (`resources.find_tool` looks in the user
   tools folder first), the history; then starts the online check in another thread: `ads.sync_ads` (ad list, ads, newest version, user
   numbers), `stats.fetch_users_base`, `feedback.register` (frozen program only, setting `share_usage`), `stats.fetch_rating`.
3. When the splash animation is finished the main window opens; it polls `ctx.online_ready`, shows the ads, the new-version question, checks
   the tools once (`update_flow`) and offers the due playlists.

## Downloading
`NewDownloadPage` reads a link (`downloader.fetch_info` through `DownloadManager`). A video link that also carries `list=` first goes
through `_playlist_gate` (new playlist: 4 choices; known playlist: tells if the file was downloaded before). Start puts the video or
playlist in `DownloadQueue` (`dlqueue.py`): one yt-dlp process per video, a limited number at the same time, progress parsed from yt-dlp's output.
Finished downloads become history records (`history.py`) and optionally favorites / sync entries.

## Playlist sync
`sync.SyncManager` keeps schedule data (daily / weekly / monthly / yearly). `SyncController` (`ui/sync_flow.py`) reads the playlist with
`InfoFetcher`, compares it with the videos of the history record (`downloaded`, `skipped`, missing files) and shows `SyncDialog` (new videos)
or `SyncDoneDialog` (nothing new: next date, schedule, on / off). `run_background` does the same without windows for the due playlists.

## Updates
- Program: the online folder lists release `.exe` files; the highest version is offered (`UpdateDialog`, opens the download page).
- Tools: `toolupdate.check_tools` compares the installed yt-dlp with the newest GitHub release (and ffmpeg with the BtbN build date);
  `update_tools` downloads (SHA-256 check for yt-dlp) into `USER_TOOLS_DIR`; `UpdateController` drives `UpdatesDialog` and
  `UpdateProgressDialog` and runs the check at start-up, from Settings and after a failed download.

## Statistics and rating
- The Apps Script (`owner_tools/feedback_apps_script.gs`) keeps one row per `install_id`. The program registers once per version and posts
  the rating (rating, feedback, new_features). `GET ?action=stats` returns `users`, `versions`, `average`, `count`, `stars`.
- Splash users = register users per version + the old numbers of `total_users.txt` (cached in `data/cache/users_base.json`, else
  `data/splash_baseline.json`).

## Online files and encryption
Text files of the online GitHub folder (ad list `TubeArchivePro-YYYY-MM.txt`, `total_users.txt`) are read by `ads.read_text_file`, which
opens encrypted files (`app/secure.py`) as well as plain ones. The owner encrypts with `owner_tools/encrypt_online.py`.

## Window behaviour
- Dialogs derive from `GlassDialog` and run through `exec_blurred` (the main window is dimmed + blurred by a picture overlay, never a
  `QGraphicsBlurEffect` on the translucent window - that caused the Windows "UpdateLayeredWindowIndirect" warning).
- The minimize button hides the window to the system tray (`MainWindow.minimize_to_tray`).

## Quality and codecs
`downloader.VIDEO_HEIGHTS` ends with 1440 (2K), 2160 (4K) and 4320 (8K); the New Download page lists only the heights the video has, with the estimated size
(`size_table`) beside each. For MP4 `engine_options` adds `h264_args(info, quality)` (setting `mp4_h264`): H.264 stream as it is when available, otherwise
download + ffmpeg conversion to H.264 / AAC.

## Reviews
`InfoPage` asks the Apps Script (`?action=reviews`, `stats.fetch_reviews`) for the newest rated rows of the sheet; offline it shows the cached copy.
