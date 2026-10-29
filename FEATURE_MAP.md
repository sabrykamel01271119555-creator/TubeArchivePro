# TubeArchive Pro - Complete Feature Map (every screen, window, button and function)

Generated from the real code of version 2.0.4 (line numbers are exact for that version; if you edit a file, search the function name).

## How to read this file
* **Window / screen** = one class. Its file and line are in the heading; the first line says what it is.
* **Controls table** = every button / switch / box that does something: *the text it shows* (from `data/languages/en.json`, id in `app/msg.py`),
  *the signal* (`clicked` = pressed, `toggled` = switched, `currentIndexChanged` = another item chosen ...), the *handler* function that runs
  (with its file line), and the *functions that handler calls next* (this is the chain, like the exit-window example).
* **Opened by** = where in the code the window is created (so you can find who shows it).
* **Texts** = every message id used by that screen with its English words: change the words only in `data/languages/en.json` / `ar.json`.
* **Files used** = data files read or written by that module (paths are in `app/paths.py`).
* Part A is the narrative for the biggest flows (exit, download, playlist, settings, start-up). Part B is the generated map of ALL files.

---

# PART A - Main flows, step by step

How to read this part: every flow is written as a chain
`what you press → function (file:line) → what it calls → what you see / what file is written`.
Line numbers are for version 2.0.4 (they are re-generated in PART B, which is exact).
"UI file" = builds the widgets. "Logic" = the function that runs when you press.

---------------------------------------------------------------------
## A1. Start-up (python main.py)
1. `main.py` `main()` (92) creates QApplication, loads settings (`app/settings.py` SettingsManager.load_current) and language (`app/i18n.py` LanguageManager.load).
2. `app/ui/splash.py` SplashScreen shows the logo and a progress bar; messages come from `set_progress(percent, msg_id)` (40).
3. `app/loader.py` StartupLoader.run (72) runs in a thread: `_load_language` (36) → `_load_history` (40) → `_online_work` (49) which calls `_online_check` (65) → `app/ads.py sync_ads` (494) (ads gifs, links, allowed list `tubearchivepro-YYYY-MM.txt`, version check, downloads counter, reviews.txt).
4. When finished `main.py on_done` (130) calls `open_window` (105) → `app/ui/main_window.py MainWindow.__init__` (122) which calls `_build_header` (200), `_build_sidebar` (230), `_build_center` (282), `_build_gauges` (311), then selects page "new" (`page_index`, 359).
5. If the loader fails: `on_failed` (141) → `show_error` (78). Python errors go to `data/error.log` (`_install_error_log` 30); Qt warnings too (`_install_qt_log` 48).

## A2. Main window (app/ui/main_window.py)
- UI: `Shell` (57) paints the rounded window, `TitleBar` (74) = title, minimize/maximize/close buttons, downloads counter (`set_counter` 102), language button.
- Sidebar buttons (`_build_sidebar` 230): each NavButton → `select_page(i)` (372) → MorphStack fade to the page. Pages: New Download, Downloads, Library, Archive, Playlist Sync, Settings.
- Bottom-left "Powered by Let's Have Fun" and the 5 links (reviews, help, about us, contact us, donate) → `show_info(kind)` (377) → `info_page.py InfoPage.show_kind` (75).
- Header (`_build_header` 200): logo, name, version, `self.ad_banner` (AdBanner widget). Updated by `_ads_updated` (460).
- Gauges (`_build_gauges` 311): g_net, g_app, g_total, g_free, g_disk, g_queue. Refreshed by `_sample_gauges` (398) → `_sample_gauges_impl` (405) using `app/sysmon.py` and the DownloadManager.
- Close (X on title bar / Alt+F4) → `closeEvent` (628) → `request_exit` (593) — see A3.
- Language button → `show_language_menu` (437) → `change_language` (444) → `main.py change_language` (116) which rebuilds the window in the new language.
- Window size change → `resizeEvent` (537) → `_apply_scale` (544) scales fonts/pages (FontScaler).
- Settings saved elsewhere → `_settings_saved` (431).
- Timers: `_poll_online` (466) (every while: update/ads), `_notify_due_playlists` (508) (sync schedule due).

## A3. Exit window chain (example of the style)
X button → `MainWindow.closeEvent` (main_window.py 628) → `request_exit` (593):
 a. If downloads are running → `ExitWarningDialog` (dialogs.py 111) (UI + its buttons in same class). "Exit" → `abort_all_downloads` (581).
 b. `RatingDialog(lang, self, previous=fb.current())` (dialogs.py 234): UI built in `__init__` (237); stars = `StarRating` (171) → `_on_rating` (320) / `_on_hover` (324).
    - "Skip and Exit" (MSG_081) → `_skip` (327) → closes dialog without saving.
    - "Submit and Exit" (MSG_082) → `_submit` (331) → accepts; text via `feedback_text` (336).
 c. back in `request_exit`: `FeedbackManager.save_rating` (feedback.py 77) → writes `feedback/my_rating.json` + history `feedback.json` (`add` 56) → `_send_rating` (main_window.py 616) starts a thread (joined max 6 s) → `FeedbackManager.send` (105) → `post_form` (36) POSTs to the Google Form (settings `feedback_form_url`, `feedback_form_fields`) → `mark_sent` (96).
 d. `force_close` (456) closes the window; `closeEvent` accepts.

## A4. New Download page (app/ui/new_download_page.py)
UI is built in `_build` (104) with `_card` (216); signals are connected in `_wire` (227).
- Paste/type URL → `_url_changed` (306) enables Check/Start.
- Format combo → `_format_changed` (297) → `_rebuild_quality` (271); Quality combo → `_quality_changed` (300) → `_update_meta` (441) (estimated size via `estimate_for` 416).
- **Check** → `_fetch` (319) → `DownloadManager.fetch` (download_manager.py 74) → worker `_fetch_worker` (78) runs yt-dlp `--dump-json` (`app/downloader.py`) → result signal → `_info_ready` (331) (thumbnail `_show_thumb` 363, title, size, free-space `_show_space_warning` 466) or `_info_failed` (351) → `_error` (914).
- **Browse** → `_browse` (529) → folder dialog → `_save_folder` (536). **Open folder** → `_open_folder` (709).
- **Start** → `_start` (611): `_check_tools` (589) (yt-dlp/ffmpeg present) → `_folder_ok` (598) → `_space_ok` (476) (free-space check, may show MessageDialog) → `_in_queue` (606) duplicate check → single video: `_enqueue_video` (647) → `DownloadQueue.add_video` (dlqueue.py 148); playlist: `PlaylistSetupDialog` (dialogs.py 762: subfolder, numbering 01/001, sync toggle, schedule `_sync_toggled` 847, `_ok` 854) → `_enqueue_playlist` (655) → `DownloadQueue.add_playlist` (158). Then `_reset_after_enqueue` (664) clears the form so the next URL can be added.
- **Pause/Resume** → `_pause_clicked` (551) → queue `pause_task`/`resume_task` (379/386). **Cancel** → `_cancel_clicked` (564) → `cancel_task` (337)/`cancel_group` (350).
- Events from the queue: `_task_done` (740) → `_save_history` (782) (history.py `new_record` 66 + `add` 55 → data/history) → `_show_success` (872) → SuccessDialog (dialogs.py 376: buttons play/open folder/add favorite via `_choose` 478, `_add_fav` 472). `_task_failed` (751), `_task_cancelled` (759), `_group_done` (763) → `_save_history_group` (799). Sync runs end in `_sync_finished` (840) → `_notify_sync` (858).
- `start_sync` (680) is called by the Playlist Sync flow; `prefill` (720) by Library "download again".
- Defaults from settings: `apply_defaults` (578).

## A5. Download queue engine (app/dlqueue.py + download_manager.py)
`DownloadQueue.pump` (184) → `_start_waiting` (199) → `_allowed` (218) (max_concurrent, playlist_concurrent via `playlist_limit` 210) → `_start` (224) spawns ONE yt-dlp process per video (command built by `app/downloader.py`), bandwidth `speed_limit_mb` is split between running tasks (`bandwidth_mb` 141). Progress lines → `_progress` (251) → `_processing` (261, merge/convert) → `_finished` (266) / `_failed` (275) / `_cancelled` (281) → `_after` (288) → `_check_group` (292) (playlist totals). Skip: `skip` (320). Pause all/resume all/cancel all: 393/396/355. `DownloadManager._event` (download_manager.py 41) turns queue events into Qt signals for the UI.

## A6. Downloads page (app/ui/downloads_page.py)
- `DownloadsPage.__init__` (369) builds toolbar: Pause all → `_pause_all` (484); Resume all → `_resume_all` (481); Cancel all → `_cancel_all` (487); Clear completed → `_clear` (477); Open folder → `_open_folder` (490); Sync → `_sync` (464).
- Rows: `TaskRow` (82) one video: pause `_pause` (128), cancel `_cancel` (132), progress `update_from` (135). `GroupRow` (158) a playlist: pause (217), cancel (227), **Details** → `DownloadsPage.show_details` (473) → `PlaylistDetailsDialog` (261) (per-video list `_row` 309, skip per video, refresh 345).
- Finished items stay until Clear completed. Rows added/updated by `rebuild` (430), `_add_row` (442), `_task_changed` (447), `_group_changed` (456).

## A7. Library and Archive pages (app/ui/library_page.py, same class LibraryPage, mode "library"/"archive")
- Folder tiles (`FolderTile` 49) → click → `_tile_clicked` (369) filters by kind (video/audio/playlist/favorites).
- Search box / filter combo / sort → `_matches` (404), `_sorted` (418), `refresh` (435) → `_layout_cards` (460). Filter list `_fill_filter` (392) uses `favorites.label`.
- Each `VideoCard` (147) has icon buttons created by `_btn` (212):
  - Play (or Sync for playlists) → `_play` (248) → opens file with the OS (`_full_path` 40) / `_sync` (265) → `SyncController.run`.
  - Folder → `_folder` (255) → `actions.reveal_file` (46).
  - Download again → `_again` (268) → `MainWindow._redownload` (367) → NewDownloadPage.prefill.
  - Details → `_details` (271) → `LibraryPage.show_details` (506) → `DetailsDialog` (dialogs.py 1045) (folder/url links open with QDesktopServices, description in QTextBrowser).
  - Favorite → `_fav` (274) → `toggle_favorite` (511) → `FavoriteDialog` (dialogs.py 579, `_ok` 628) → `favorites.add` (49). Star state `refresh_fav` (239).
  - Delete → `_delete` (277) → `delete_record` (520) → ChoiceDialog (dialogs.py 488, `_pick` 524) → `history.delete_files` (history.py 131) deletes the physical files + `history.remove` (110).
- Category edit/delete buttons (in Settings and filter) → `_edit_category`/`_delete_category` → CategoryDialog (dialogs.py 641).

## A8. Playlist Sync page (app/ui/sync_page.py + sync_flow.py)
- `SyncPage._build` (45) header columns; `refresh` (100) builds a row per synced playlist with `_row` (125): ON/OFF toggle → `_set_enabled` (209); schedule combo → `_set_schedule` (204) (`app/sync.py set_schedule` 83); **Sync now** → `_sync` (217) → `SyncController.run` (sync_flow.py 66) → fetch playlist info (InfoFetcher) → `SyncDialog` (dialogs.py 863: new/old videos, checkboxes `_count` 1032, `_done` 1037) → `NewDownloadPage.start_sync` (680); **Folder** → `_folder` (223); **Stop sync** → `_stop` (230) → `sync.remove` (92).
- Due schedule check: `MainWindow._notify_due_playlists` (508) uses `SyncManager.is_due` (97).

## A9. Settings page (app/ui/settings_page.py)
- Left category list → scrolls/switches the work area; `_fit` (255) and `_rescale` (276) auto-fit sizes.
- Cards built with `_card` (314), rows `_stack` (332) / `_toggle` (342); small buttons via `_mini` (350).
- Download folder Browse → `_browse` (440). Quality combos → `_fill_quality` (360).
- **Apply and Save** → `save` (446) → settings.set/save (settings.py 69/75) → `_done` (506) message; language change → `main.py change_language`.
- **Reset to Default** → `restore_defaults` (489) → `settings.reset_to_defaults` (81) → `load` (404).
- **Cancel** → `discard` (501) → `load` (404) (re-read saved values).
- Categories: add `_add_category` (514), edit `_edit_category` (521), delete `_delete_category` (532) → CategoryDialog → favorites.add/edit/delete_category.
- Changes made elsewhere are shown live through `_on_setting` (474).

## A10. Info pages (app/ui/info_page.py, text from app/infodoc.py)
Reviews / Help / About us / Contact us / Donate: `InfoPage.show_kind` (75) → HTML from `infodoc` → `_show_html` (63). Reviews: `_load_reviews` (95) → `ads.TextFetcher.fetch` (reviews.txt on Drive, cached) → `_reviews_done` (101). Links in the page open in the browser. Text is in `data/languages/*.json` (numbered messages).

## A11. Ads, update check, downloads counter
`loader._online_work` at splash and `MainWindow._poll_online` (466) → `AdsFetcher.refresh` (ads.py 708) → `sync_ads` (494): `list_drive` (177) lists the online folder, `pick`/`parse_allowed` choose this month's ads, gifs downloaded to `assets/ads` (`_download_gif` 304), links via `parse_links` (234). Result → `MainWindow._ads_updated` (460) → AdBanner. New version found → `_check_done` (487) → `UpdateDialog` (dialogs.py 529). Counter → `_show_counter` (475) → `TitleBar.set_counter` (102). Diagnostics: `data/updates.log`, `data/drive_page_debug.html`.

## A12. Dialog base and helpers
`GlassDialog` (dialogs.py 43) = blurred glass window; shown with `actions.exec_blurred` (54). `MessageDialog` (341) simple OK; `BusyDialog` (727) with Cancel (`_cancel` 753) while fetching.

## A13. Data files (what writes/reads what)
- `current_settings.json` ← settings.py save; defaults `data/config/default_settings.json`.
- `data/history/*` ← history.py; `favorites` ← favorites.py; `sync` ← sync.py; `feedback/my_rating.json`, `feedback.json` ← feedback.py.
- `data/languages/en.json`, `ar.json` ← i18n.py (messages keyed MSG_xxx; constants in `app/msg.py` class M).
- `assets/ads`, `data/cache` ← ads.py; `data/error.log` ← main.py; `data/updates.log` ← ads.write_log.


---

# PART B - Every file, class, control and function


## `app/ui/__init__.py`  (6 lines)


## `app/ui/actions.py`  (82 lines)

Small actions used by more than one page.

**Functions of the module:**

* `badge_text()` line 24 - Text of the small quality badge (success window).  → calls: `is_audio`
* `card_tag()` line 35 - Badge on the thumbnail of the Downloads page: 4K, 2K, Full HD, HD, 480p, MP3 ...  → calls: `is_audio`
* `reveal_file()` line 47 - Open the folder and select the file (Explorer); other systems just open the folder.
* `exec_blurred()` line 55 - Run a dialog while the main window is blurred (like the other glass windows).
* `add_to_favorites()` line 68 - Ask for a category (existing or new) and put the video in it. True = added.  → calls: `fav.category_of`, `exec_blurred`


## `app/ui/dialogs.py`  (1187 lines)

Exit dialogs (design guides: exit warning + 'Before You Go' rating).

**Functions of the module:**

* `_center_row()` line 112 - -


### class `GlassDialog`  (line 54)

Frameless glowing glass dialog, centred over its parent window.

**Functions:**

* `__init__()` line 57 - -
* `_fit_to_window()` line 66 - 2.0.2: the window follows the size of the main window (smaller window -> smaller dialog and texts, never  → calls: `font_qss`
* `showEvent()` line 81 - -  → calls: `self._fit_to_window`
* `paintEvent()` line 88 - -


### class `ExitWarningDialog`  (line 122)

Shown when downloads are still running. exec() == Accepted -> abort and exit.

**Opened / created by:** `app/ui/main_window.py` → `request_exit()` line 669

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 174 | `back` | QPushButton | “Back” | clicked | `reject` | - |
| 181 | `abort` | QPushButton | “Abort Downloads” | clicked | `accept` | - |

**Functions:**

* `__init__()` line 125 - -  → calls: `sounds.play`, `make_warning_icon`, `_center_row`, `make_exit_icon`

**Texts used (id · constant · English):**

<details><summary>show 8 texts</summary>

* MSG_064 · `M.EXIT_TITLE` · 'Exit TubeArchive Pro?'
* MSG_065 · `M.EXIT_WARN` · 'Warning: Active Downloads in Progress!'
* MSG_066 · `M.EXIT_TEXT` · 'Are you sure you want to exit? Closing the application will abort and cancel all ongoing downloads.'
* MSG_067 · `M.EXIT_ONE` · '{count} active download at {pct}%'
* MSG_068 · `M.EXIT_MANY` · '{count} active downloads, average {pct}%'
* MSG_069 · `M.BTN_BACK` · 'Back'
* MSG_070 · `M.BTN_ABORT` · 'Abort Downloads'
* MSG_420 · `M.EXIT_PAUSED` · '{paused} of them are paused and will not be finished. Closing the application cancels them too.'

</details>


### class `StarRating`  (line 189)

**Opened / created by:** `app/ui/dialogs.py` → `__init__()` line 283

**Functions:**

* `__init__()` line 194 - -
* `_index_at()` line 202 - -
* `mouseMoveEvent()` line 205 - -  → calls: `self._index_at`
* `leaveEvent()` line 210 - -
* `mousePressEvent()` line 215 - -  → calls: `self._index_at`
* `_star()` line 222 - -
* `paintEvent()` line 230 - -  → calls: `self._star`


### class `RatingDialog`  (line 252)

'Before You Go!' dialog. After exec(): .action is 'submit', 'skip' or 'cancel'.

**Opened / created by:** `app/ui/main_window.py` → `request_exit()` line 675

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 289 | `self.stars` | StarRating | - | changed | `_on_rating` (344) | `self._text_for` |
| 290 | `self.stars` | StarRating | - | hovered | `_on_hover` (348) | `self._text_for` |
| 325 | `back` | QPushButton | “Cancel” | clicked | `reject` | - |
| 325 | `skip` | QPushButton | “Skip and Exit” | clicked | `_skip` (351) | - |
| 325 | `submit` | QPushButton | “Submit and Exit” | clicked | `_submit` (355) | - |

**Functions:**

* `__init__()` line 255 - -  → calls: `make_app_icon`, `_center_row`, `mnemonic_safe`, `self._on_rating`
* `_text_for()` line 340 - -
* `_on_rating()` line 344 - -  → calls: `self._text_for`
* `_on_hover()` line 348 - -  → calls: `self._text_for`
* `_skip()` line 351 - -
* `_submit()` line 355 - -
* `feedback_text()` line 360 - -
* `features_text()` line 364 - -

**Texts used (id · constant · English):**

<details><summary>show 15 texts</summary>

* MSG_001 · `M.APP_NAME` · 'TubeArchive Pro'
* MSG_071 · `M.RATE_TITLE` · 'Before You Go!'
* MSG_072 · `M.RATE_SUB` · "We'd love to know about your experience. Please rate us below:"
* MSG_073 · `M.RATE_1` · 'Poor'
* MSG_074 · `M.RATE_2` · 'Fair'
* MSG_075 · `M.RATE_3` · 'Good'
* MSG_076 · `M.RATE_4` · 'Excellent!'
* MSG_077 · `M.RATE_5` · 'Outstanding!'
* MSG_078 · `M.RATE_HINT` · 'Select a star rating'
* MSG_079 · `M.RATE_PLACEHOLDER` · 'Write your feedback or suggest a feature (optional)...'
* MSG_080 · `M.BTN_DETAILED` · 'Share Detailed Feedback'
* MSG_081 · `M.BTN_SKIP` · 'Skip and Exit'
* MSG_082 · `M.BTN_SUBMIT` · 'Submit and Exit'
* MSG_109 · `M.BTN_CANCEL1` · 'Cancel'
* MSG_473 · `M.RATE_FEATURES_PH` · 'Which new features would you like us to add? (optional)'

</details>


### class `MessageDialog`  (line 369)

One-button message window used for download errors (red glass).

**Opened / created by:** `app/ui/library_page.py` → `message()` line 539; `app/ui/main_window.py` → `change_language()` line 507; `app/ui/new_download_page.py` → `_error()` line 1042; `app/ui/new_download_page.py` → `_notify_sync()` line 980; `app/ui/sync_flow.py` → `_bg_finish()` line 216; `app/ui/sync_flow.py` → `run()` line 108

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 401 | `ok` | QPushButton | “OK” | clicked | `accept` | - |

**Functions:**

* `__init__()` line 372 - -  → calls: `sounds.play`, `_center_row`, `make_sync_icon`, `make_warning_icon`

**Texts used (id · constant · English):**

<details><summary>show 1 texts</summary>

* MSG_150 · `M.BTN_OK` · 'OK'

</details>


### class `SuccessDialog`  (line 406)

'File Successfully Downloaded!' window.

**Opened / created by:** `app/ui/new_download_page.py` → `_show_success()` line 1009

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 484 | `ok` | QPushButton | “OK” | clicked | `_choose` (505) | - |
| 484 | `opn` | QPushButton | “Open Folder” | clicked | `_choose` (505) | - |
| 484 | `play` | QPushButton | “Play Audio”, “Play Video” | clicked | `_choose` (505) | - |
| 495 | `self.fav` | QPushButton | “Add to Favorite” | clicked | `_add_fav` (499) | `make_star_icon` |

**Functions:**

* `__init__()` line 411 - -  → calls: `make_app_icon`, `make_check_icon`, `_center_row`, `make_play_icon`, `make_folder_icon`, `make_info_icon`, `make_star_icon`
* `_add_fav()` line 499 - -  → calls: `make_star_icon`
* `_choose()` line 505 - -
* `dont_show()` line 510 - -

**Texts used (id · constant · English):**

<details><summary>show 8 texts</summary>

* MSG_001 · `M.APP_NAME` · 'TubeArchive Pro'
* MSG_110 · `M.BTN_FOLDER1` · 'Open Folder'
* MSG_147 · `M.OK_DONT_SHOW` · "Don't show this message again"
* MSG_148 · `M.BTN_PLAY_VIDEO` · 'Play Video'
* MSG_149 · `M.BTN_PLAY_AUDIO` · 'Play Audio'
* MSG_150 · `M.BTN_OK` · 'OK'
* MSG_172 · `M.BTN_FAV` · 'Add to Favorite'
* MSG_173 · `M.FAV_ADDED` · 'Added to favorites'

</details>


### class `ChoiceDialog`  (line 515)

Message with several buttons. buttons = [(choice id, text, style object name)].

**Opened / created by:** `app/ui/downloads_page.py` → `confirm_cancel()` line 549; `app/ui/library_page.py` → `delete_record()` line 564; `app/ui/main_window.py` → `_notify_due_playlists_impl()` line 582; `app/ui/new_download_page.py` → `_cancel_clicked()` line 671; `app/ui/new_download_page.py` → `_duplicate_ok()` line 402; `app/ui/new_download_page.py` → `_space_ok()` line 598

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 558 | `b` | QPushButton | - | clicked | `_keep` (562) | - |

**Functions:**

* `__init__()` line 519 - -  → calls: `sounds.play`, `make_warning_icon`, `_center_row`, `rounded_pixmap`, `mnemonic_safe`, `self._keep`, `self._pick`
* `_keep()` line 562 - -
* `_pick()` line 566 - -


### class `UpdateDialog`  (line 571)

'A new version is available - update?'  After exec(): .choice is 'yes' or 'no' (closing = no);

**Opened / created by:** `app/ui/main_window.py` → `_check_done()` line 558

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 607 | `b` | QPushButton | - | clicked | `_pick` (611) | - |

**Functions:**

* `__init__()` line 575 - -  → calls: `make_arrow_icon`, `_center_row`, `self._pick`
* `_pick()` line 611 - -
* `reject()` line 616 - -

**Texts used (id · constant · English):**

<details><summary>show 5 texts</summary>

* MSG_275 · `M.UP_TITLE` · 'New version available'
* MSG_276 · `M.UP_TEXT` · 'A new version of TubeArchive Pro is available: {new} (you have {cur}).\nWould you like to update now?'
* MSG_277 · `M.UP_YES` · 'Yes, update'
* MSG_278 · `M.UP_NO` · 'No'
* MSG_279 · `M.UP_DONT` · "Don't show this message again"

</details>


### class `FavoriteDialog`  (line 621)

'Add to Favorites': pick a category from the list or type a new one.

**Opened / created by:** `app/ui/actions.py` → `add_to_favorites()` line 77

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 672 | `add` | QPushButton | “Add” | clicked | `_ok` (676) | - |
| 673 | `cancel` | QPushButton | “Cancel” | clicked | `reject` | - |

**Functions:**

* `__init__()` line 625 - -  → calls: `make_star_icon`, `_center_row`, `make_emoji_icon`
* `_ok()` line 676 - -

**Texts used (id · constant · English):**

<details><summary>show 4 texts</summary>

* MSG_109 · `M.BTN_CANCEL1` · 'Cancel'
* MSG_169 · `M.FAV_TITLE` · 'Add to Favorites'
* MSG_170 · `M.FAV_TEXT` · 'Choose a category or type a new one:'
* MSG_171 · `M.FAV_ADD` · 'Add'

</details>


### class `CategoryDialog`  (line 689)

New / edit a favorites category: its name + one icon from a small list.

**Opened / created by:** `app/ui/settings_page.py` → `_add_category()` line 544; `app/ui/settings_page.py` → `_edit_category()` line 555

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 727 | `b` | QPushButton | - | clicked | `_pick` (758) | - |
| 747 | `ok` | QPushButton | “Save” | clicked | `_ok` (763) | - |
| 748 | `cancel` | QPushButton | “Cancel” | clicked | `reject` | - |
| 750 | `self.edit` | QLineEdit | - | returnPressed | `_ok` (763) | - |

**Functions:**

* `__init__()` line 693 - -  → calls: `make_star_icon`, `_center_row`, `self._label`, `self._pick`
* `_label()` line 753 - -
* `_pick()` line 758 - -
* `_ok()` line 763 - -

**Texts used (id · constant · English):**

<details><summary>show 5 texts</summary>

* MSG_109 · `M.BTN_CANCEL1` · 'Cancel'
* MSG_307 · `M.CAT_NAME` · 'Category name'
* MSG_308 · `M.CAT_ICON` · 'Choose an icon'
* MSG_311 · `M.CAT_EXISTS` · 'A category with this name already exists.'
* MSG_313 · `M.CAT_SAVE` · 'Save'

</details>


### class `BusyDialog`  (line 775)

'Checking the playlist...' with a Cancel button. The caller closes it with finish().

**Opened / created by:** `app/ui/sync_flow.py` → `run()` line 119

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 798 | `cancel` | QPushButton | “Cancel” | clicked | `_cancel` (801) | - |

**Functions:**

* `__init__()` line 778 - -  → calls: `make_sync_icon`, `_center_row`
* `_cancel()` line 801 - -
* `finish()` line 805 - -

**Texts used (id · constant · English):**

<details><summary>show 1 texts</summary>

* MSG_109 · `M.BTN_CANCEL1` · 'Cancel'

</details>


### class `PlaylistSetupDialog`  (line 810)

Asked before a NEW playlist is downloaded: own folder? add to sync (daily / weekly / monthly)?

**Opened / created by:** `app/ui/new_download_page.py` → `_start()` line 738

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 854 | `self.c_sync` | QCheckBox | “Add this playlist to sync (get new videos automatically)” | toggled | `_sync_toggled` (895) | - |
| 867 | `self.combo` | ArrowComboBox | - | currentIndexChanged | `_update_next` (898) | `add_schedule` |
| 890 | `go` | QPushButton | “Start Download” | clicked | `_ok` (902) | - |
| 891 | `cancel` | QPushButton | “Cancel” | clicked | `reject` | - |

**Functions:**

* `__init__()` line 814 - -  → calls: `self._update_next`, `make_play_icon`, `rounded_pixmap`, `make_thumb`
* `_sync_toggled()` line 895 - -
* `_update_next()` line 898 - -  → calls: `add_schedule`
* `_ok()` line 902 - -

**Texts used (id · constant · English):**

<details><summary>show 11 texts</summary>

* MSG_042 · `M.BTN_START` · 'Start Download'
* MSG_105 · `M.ND_PLAYLIST` · 'Playlist · {count} videos'
* MSG_109 · `M.BTN_CANCEL1` · 'Cancel'
* MSG_195 · `M.PS_TITLE` · 'Playlist Download Options'
* MSG_196 · `M.PS_FOLDER` · 'Create a folder for this playlist inside the save directory'
* MSG_197 · `M.PS_SYNC` · 'Add this playlist to sync (get new videos automatically)'
* MSG_198 · `M.PS_SCHEDULE` · 'Sync Schedule'
* MSG_199 · `M.PS_DAILY` · 'Daily'
* MSG_200 · `M.PS_WEEKLY` · 'Weekly'
* MSG_201 · `M.PS_MONTHLY` · 'Monthly'
* MSG_202 · `M.PS_NEXT` · 'Next sync: {date}'

</details>


### class `SyncDialog`  (line 911)

'Playlist Sync Manager' window: new videos (ticked) + previously downloaded videos (not ticked).

**Opened / created by:** `app/ui/sync_flow.py` → `run()` line 138

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 1015 | `self.b_sync` | QPushButton | - | clicked | `_done` (1104) | - |
| 1016 | `self.b_go` | QPushButton | - | clicked | `_done` (1104) | - |
| 1017 | `b_skip` | QPushButton | “Skip New” | clicked | `_done` (1104) | - |
| 1018 | `b_later` | QPushButton | “Later” | clicked | `reject` | - |
| 1054 | `chk` | QCheckBox | - | toggled | `_count` (1099) | `mnemonic_safe` |
| 1095 | `b` | QPushButton | - | clicked | `_on_reveal` | - |
| 1095 | `b` | QPushButton | - | clicked | `_on_play` | - |
| 1095 | `b` | QPushButton | - | clicked | `lambda _=False, c=chk: c.setChecked(n…` | - |

**Functions:**

* `__init__()` line 920 - -  → calls: `self._count`, `make_app_icon`, `make_warning_icon`, `make_sync_icon`, `make_arrow_icon`, `self._section`, `mnemonic_safe`
* `_section()` line 1022 - -
* `_thumb()` line 1027 - -  → calls: `rounded_pixmap`, `make_thumb`
* `_row()` line 1044 - -  → calls: `self._thumb`, `make_folder_icon`, `make_play_icon`, `make_sync_icon`, `fmt_time`, `fmt_size`
* `_count()` line 1099 - -  → calls: `mnemonic_safe`
* `_done()` line 1104 - -

**Texts used (id · constant · English):**

<details><summary>show 23 texts</summary>

* MSG_001 · `M.APP_NAME` · 'TubeArchive Pro'
* MSG_145 · `M.OK_SIZE` · 'Size:'
* MSG_158 · `M.TIP_PLAY` · 'Play'
* MSG_159 · `M.TIP_FOLDER` · 'Open folder'
* MSG_161 · `M.TIP_REDOWNLOAD` · 'Download again'
* MSG_208 · `M.SY_HEADER` · 'Sync Update:'
* MSG_209 · `M.SY_NEW_FOUND` · '{n} New Videos Found'
* MSG_210 · `M.SY_UPTODATE` · 'Everything is up to date'
* MSG_211 · `M.SY_NEW` · 'New Videos'
* MSG_212 · `M.SY_PREV` · 'Previously Downloaded Videos'
* MSG_213 · `M.SY_BADGE_NEW` · 'NEW'
* MSG_214 · `M.SY_PREV_BADGE` · 'Previously Downloaded'
* MSG_216 · `M.SY_SKIP` · 'Skip New'
* MSG_217 · `M.SY_DUR` · 'Duration: {d}'
* MSG_218 · `M.SY_DOWNLOADED` · 'Downloaded: {date}'
* MSG_439 · `M.SY_SEC_SKIPPED` · 'Skipped before'
* MSG_440 · `M.SY_SEC_MISSING` · 'Downloaded before - file is not in the folder'
* MSG_441 · `M.SY_BADGE_SKIPPED` · 'Skipped'
* MSG_442 · `M.SY_BADGE_MISSING` · 'Missing file'
* MSG_443 · `M.SY_SYNC` · 'Sync ({n})'
* MSG_444 · `M.SY_SELECTED` · 'Download selected ({n})'
* MSG_445 · `M.SY_LATER` · 'Later'
* MSG_446 · `M.SY_SUMMARY` · '{total} videos in the playlist: {new} new, {skipped} skipped, {missing} missing from the folder'

</details>


### class `DetailsDialog`  (line 1112)

'Details' of a video (Archive / Library): picture, facts and the description that was saved with it.

**Opened / created by:** `app/ui/library_page.py` → `show_details()` line 542

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 1166 | `lb` | QLabel | - | linkActivated | `lambda link: QDesktopServices.openUrl…` | - |
| 1185 | `close` | QPushButton | “Close” | clicked | `accept` | - |

**Functions:**

* `__init__()` line 1116 - -  → calls: `rounded_pixmap`, `make_thumb`, `description_html`, `fmt_size`, `fmt_time`

**Texts used (id · constant · English):**

<details><summary>show 12 texts</summary>

* MSG_178 · `M.DL_FILES` · '{count} files'
* MSG_343 · `M.DLQ_CLOSE` · 'Close'
* MSG_351 · `M.DET_DESC` · 'Description'
* MSG_352 · `M.DET_NO_DESC` · 'No description was saved for this video.'
* MSG_353 · `M.DET_DATE` · 'Downloaded on'
* MSG_354 · `M.DET_SIZE` · 'Size'
* MSG_355 · `M.DET_DURATION` · 'Duration'
* MSG_356 · `M.DET_FORMAT` · 'Format'
* MSG_357 · `M.DET_FOLDER` · 'Folder'
* MSG_358 · `M.DET_LINK` · 'Link'
* MSG_359 · `M.DET_CATEGORY` · 'Category'
* MSG_360 · `M.DET_VIDEOS` · 'Videos of this playlist'

</details>


## `app/ui/downloads_page.py`  (568 lines)

'Downloads' tab: everything that is running or waiting in the download queue (app/dlqueue.py).

**Functions of the module:**

* `size_ratio()` line 39 - '123 MB / 456 MB' - what came so far and what is expected (the expected size is refined while it downloads).  → calls: `fmt_size`
* `state_text()` line 46 - -
* `task_pixmap()` line 58 - -  → calls: `make_thumb`, `rounded_pixmap`
* `_icon_button()` line 67 - -
* `_bar()` line 77 - -
* `bar_state()` line 86 - Colour of a progress bar by state: "" blue (working), "done" green, "paused" orange, "failed" red (2.2.3).


### class `TaskRow`  (line 95)

One video.

**Opened / created by:** `app/ui/downloads_page.py` → `_add_row()` line 469

**Functions:**

* `__init__()` line 98 - -  → calls: `quality_label`, `_bar`, `_icon_button`, `self.update_from`
* `_pause()` line 141 - -  → calls: `q.resume_task`, `q.pause_task`
* `_cancel()` line 145 - -  → calls: `self.page.confirm_cancel`, `self.page.mgr.queue.discard_task`
* `update_from()` line 149 - -  → calls: `bar_state`, `state_text`, `task_pixmap`, `size_ratio`, `fmt_time`

**Texts used (id · constant · English):**

<details><summary>show 5 texts</summary>

* MSG_018 · `M.BTN_RESUME` · 'Resume All'
* MSG_019 · `M.BTN_PAUSE` · 'Pause All'
* MSG_020 · `M.BTN_CANCEL` · 'Cancel All'
* MSG_029 · `M.UNIT_MBS` · 'MB/s'
* MSG_106 · `M.ND_ETA` · 'ETA {eta}'

</details>


### class `GroupRow`  (line 176)

A playlist: counter, the current file + the whole playlist progress, thumbnail of the newest started file.

**Opened / created by:** `app/ui/downloads_page.py` → `_add_row()` line 469

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 224 | `self.b_details` | QPushButton | “Details” | clicked | `lambda: page.show_details(self.group)` | - |

**Functions:**

* `__init__()` line 179 - -  → calls: `quality_label`, `_bar`, `_icon_button`, `self.update_from`, `page.show_details`
* `_pause()` line 235 - -  → calls: `q.resume_task`, `q.pause_task`
* `_cancel()` line 245 - -  → calls: `self.page.confirm_cancel`, `self.page.mgr.queue.discard_group`
* `update_from()` line 249 - -  → calls: `g.counts`, `bar_state`, `task_pixmap`, `self.cur_line.set_full_text`, `size_ratio`, `index_text`

**Texts used (id · constant · English):**

<details><summary>show 10 texts</summary>

* MSG_019 · `M.BTN_PAUSE` · 'Pause All'
* MSG_020 · `M.BTN_CANCEL` · 'Cancel All'
* MSG_029 · `M.UNIT_MBS` · 'MB/s'
* MSG_331 · `M.DLQ_DONE` · 'Completed'
* MSG_335 · `M.DLQ_FILE_OF` · 'File {i} of {n}'
* MSG_336 · `M.DLQ_CURRENT` · 'Current file'
* MSG_337 · `M.DLQ_TOTAL` · 'Playlist total'
* MSG_338 · `M.DLQ_PL_STATS` · '{done} done  ·  {active} running  ·  {waiting} waiting'
* MSG_339 · `M.DLQ_DETAILS` · 'Details'
* MSG_344 · `M.DLQ_PL_DONE_ROW` · 'Completed: {done} of {n} files'

</details>


### class `PlaylistDetailsDialog`  (line 282)

Every video of the playlist with its own bar; 'Skip this one' for the videos that are not finished.

**Opened / created by:** `app/ui/downloads_page.py` → `show_details()` line 531

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 301 | `self.one` | QCheckBox | “Download one by one (so files can be skipped)” | toggled | `lambda on: mgr.queue.set_sequential(g…` | - |
| 323 | `close` | QPushButton | “Close” | clicked | `accept` | - |
| 358 | `skip` | QPushButton | “Skip this one” | clicked | `lambda _=False, task=task: self.mgr.q…` | - |

**Functions:**

* `__init__()` line 285 - -  → calls: `self._row`, `mgr.queue.set_sequential`
* `_row()` line 330 - -  → calls: `_bar`, `index_text`, `self.mgr.queue.skip`
* `_changed()` line 362 - -
* `refresh()` line 366 - -  → calls: `self.group.counts`, `state_text`, `task_pixmap`, `size_ratio`

**Texts used (id · constant · English):**

<details><summary>show 7 texts</summary>

* MSG_029 · `M.UNIT_MBS` · 'MB/s'
* MSG_335 · `M.DLQ_FILE_OF` · 'File {i} of {n}'
* MSG_338 · `M.DLQ_PL_STATS` · '{done} done  ·  {active} running  ·  {waiting} waiting'
* MSG_340 · `M.DLQ_SKIP` · 'Skip this one'
* MSG_341 · `M.DLQ_ONE_BY_ONE` · 'Download one by one (so files can be skipped)'
* MSG_342 · `M.DLQ_DET_TITLE` · 'Playlist details'
* MSG_343 · `M.DLQ_CLOSE` · 'Close'

</details>


### class `DownloadsPage`  (line 389)

**Opened / created by:** `app/ui/main_window.py` → `_build_center()` line 323

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 408 | `self.clear` | QPushButton | “Clear finished” | clicked | `_clear` (534) | `self.mgr.queue.clear_finished`, `self.rebuild` |
| 411 | `self.auto` | QCheckBox | “Clear completed automatically” | toggled | `_auto_toggled` (473) | `self._auto_clear` |
| 444 | `b` | QPushButton | “Resume All” | clicked | `_resume_all` (538) | `self.mgr.queue.resume_all` |
| 444 | `b` | QPushButton | “Pause All” | clicked | `_pause_all` (541) | `self.mgr.queue.pause_all` |
| 444 | `b` | QPushButton | “Cancel All” | clicked | `_cancel_all` (560) | `self.mgr.queue.counts`, `self.confirm_cancel`, `self.mgr.queue.discard_all` |
| 444 | `b` | QPushButton | “Open Archive Folder” | clicked | `_open_folder` (565) | `self.ctx.settings.download_dir` |

**Functions:**

* `__init__()` line 390 - -  → calls: `ctx.settings.subscribe`, `self.rebuild`
* `rebuild()` line 456 - -  → calls: `self.mgr.queue.top_items`, `self._sync`, `self._add_row`
* `_key()` line 465 - -
* `_add_row()` line 468 - -  → calls: `self._key`
* `_auto_toggled()` line 473 - -  → calls: `self._auto_clear`
* `_on_setting()` line 480 - The Settings page changed the same option: show it here too.  → calls: `self._auto_clear`
* `_auto_clear()` line 491 - Option on: a finished download (or playlist) leaves the list at once.  → calls: `self.mgr.queue.clear_finished`, `self.rebuild`
* `_task_changed()` line 496 - -  → calls: `self._purge`, `row.update_from`, `self._sync`, `self._key`, `self._add_row`
* `_group_changed()` line 509 - -  → calls: `self._purge`, `self._sync`, `self._key`, `self._add_row`, `row.update_from`
* `_sync()` line 521 - -  → calls: `self.mgr.queue.counts`
* `show_details()` line 530 - -  → calls: `exec_blurred`
* `_clear()` line 534 - -  → calls: `self.mgr.queue.clear_finished`, `self.rebuild`
* `_resume_all()` line 538 - -  → calls: `self.mgr.queue.resume_all`
* `_pause_all()` line 541 - -  → calls: `self.mgr.queue.pause_all`
* `confirm_cancel()` line 544 - Warning window of every Cancel of this page; True = the user confirmed (the download is then removed).  → calls: `self.mgr.queue.counts`, `exec_blurred`
* `_purge()` line 554 - -  → calls: `self.mgr.queue.purge_discarded`, `self.rebuild`
* `_cancel_all()` line 560 - -  → calls: `self.mgr.queue.counts`, `self.confirm_cancel`, `self.mgr.queue.discard_all`
* `_open_folder()` line 565 - -  → calls: `self.ctx.settings.download_dir`

**Texts used (id · constant · English):**

<details><summary>show 13 texts</summary>

* MSG_018 · `M.BTN_RESUME` · 'Resume All'
* MSG_019 · `M.BTN_PAUSE` · 'Pause All'
* MSG_020 · `M.BTN_CANCEL` · 'Cancel All'
* MSG_021 · `M.BTN_OPEN_FOLDER` · 'Open Archive Folder'
* MSG_324 · `M.DLQ_STATUS` · 'Running: {running}  ·  Waiting in queue: {waiting}'
* MSG_325 · `M.DLQ_CLEAR` · 'Clear finished'
* MSG_326 · `M.DLQ_EMPTY` · 'Nothing is downloading yet. Paste a link in New Download and press Start.'
* MSG_397 · `M.CF_CANCEL_NO` · 'No, continue'
* MSG_421 · `M.DLQ_AUTO_CLEAR` · 'Clear completed automatically'
* MSG_424 · `M.DLQ_CANCEL_TITLE` · 'Cancel download'
* MSG_425 · `M.DLQ_CANCEL_ONE` · 'Cancel this download?\n{title}\n\nIt is stopped, the unfinished file is deleted and it is removed from the list and from the history.'
* MSG_426 · `M.DLQ_CANCEL_ALL` · 'Cancel ALL downloads ({n} files)?\n\nThey are stopped, the unfinished files are deleted and they are removed from the list and from the history.'
* MSG_427 · `M.DLQ_CANCEL_YES` · 'Yes, cancel and remove'

</details>


## `app/ui/icons.py`  (508 lines)

All icons are drawn in code (no image files needed).

**Functions of the module:**

* `_grad()` line 24 - -
* `make_app_icon()` line 31 - Stacked blue binders + play triangle + red download badge.  → calls: `card`, `_grad`
* `make_app_qicon()` line 69 - -  → calls: `make_app_icon`
* `make_thumb()` line 76 - Placeholder thumbnail (gradient + play button).  → calls: `_grad`
* `draw_nav_icon()` line 97 - Simple line icons for the side menu.
* `make_warning_icon()` line 155 - Red warning triangle with a white exclamation mark.  → calls: `_grad`
* `make_exit_icon()` line 173 - Door bracket with an arrow leaving it.
* `make_arrow_icon()` line 188 - White download arrow (round red button).
* `make_state_icon()` line 202 - Icons of the counters (2.2.3): 'down' = downloading now, 'queue' = waiting list, 'pause' = paused.
* `make_play_icon()` line 229 - -
* `make_folder_icon()` line 242 - -
* `make_check_icon()` line 262 - Glowing check mark inside broken rings (success dialog).
* `make_info_icon()` line 282 - Small icons for the rows of the success dialog: file / badge / size / folder.
* `rounded_pixmap()` line 324 - Fill w x h with the picture (centre crop) and round the corners.
* `make_trash_icon()` line 340 - -
* `make_star_icon()` line 358 - Star for 'add to favorites' (filled gold = already a favorite).
* `make_sync_icon()` line 377 - Two arrows chasing each other in a circle ('Sync now').
* `make_emoji_icon()` line 396 - The icon (one emoji) of a favorite category as a real picture, so every list shows it beside the name.
* `set_sync_button()` line 413 - Sync button of a playlist (Archive / Library / Playlist Sync): synchronised = full green button with a lit sign;  → calls: `make_sync_icon`
* `make_globe_icon()` line 435 - Language button: a globe (circle + meridians + parallels).
* `make_details_icon()` line 455 - Round 'i' icon of the Details button.
* `make_channel_logo()` line 472 - Round logo of the owner's YouTube channel (Let's Have Fun).


## `app/ui/info_page.py`  (117 lines)

One page that shows the text of a link of the side-menu corner as formatted HTML (app/infodoc.py).

**Files used:** `reviews.txt`


### class `InfoPage`  (line 25)

**Opened / created by:** `app/ui/main_window.py` → `_build_center()` line 334

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 42 | `self.refresh_btn` | QPushButton | “Refresh” | clicked | `_load_reviews` (95) | `self._show_html`, `self.fetcher.fetch`, `render_text`, `self._folder_url`, `self._direction` |
| 57 | `self.view` | QTextBrowser | - | anchorClicked | `lambda url: QDesktopServices.openUrl(…` | - |

**Functions:**

* `__init__()` line 26 - -
* `_show_html()` line 63 - -  → calls: `scale_html`
* `on_font_scale()` line 67 - -  → calls: `scale_html`
* `_direction()` line 72 - -
* `show_kind()` line 75 - Called by the main window when a link of the corner is clicked.  → calls: `load_info`, `self._load_reviews`, `self._show_html`, `render_text`, `self._direction`
* `_folder_url()` line 91 - -
* `_load_reviews()` line 95 - -  → calls: `self._show_html`, `self.fetcher.fetch`, `render_text`, `self._folder_url`, `self._direction`
* `_reviews_done()` line 101 - -  → calls: `self._show_html`, `render_reviews`, `parse_reviews`, `self._direction`

**Texts used (id · constant · English):**

<details><summary>show 9 texts</summary>

* MSG_362 · `M.LNK_REVIEWS` · 'Reviews'
* MSG_363 · `M.LNK_HELP` · 'Help'
* MSG_369 · `M.INFO_REFRESH` · 'Refresh'
* MSG_370 · `M.INFO_LOADING` · 'Loading the reviews...'
* MSG_371 · `M.INFO_CACHED` · 'No connection: showing the last saved copy of the reviews.'
* MSG_372 · `M.INFO_FAILED` · 'The reviews could not be loaded. Check your internet connection and press Refresh.'
* MSG_373 · `M.INFO_MISSING` · 'This page is not available.'
* MSG_374 · `M.INFO_REVIEWS_SUMMARY` · '{n} reviews'
* MSG_375 · `M.INFO_REVIEWS_EMPTY` · 'There are no reviews yet.'

</details>


## `app/ui/library_page.py`  (579 lines)

'Library' and 'Archive' tabs (design guide: Library & Archive mockup).

**Functions of the module:**

* `_full_path()` line 42 - -
* `kind_of()` line 46 - -


### class `FolderTile`  (line 51)

Glass folder of the vault (Videos / Music / Playlists). Click = show only that kind.

**Opened / created by:** `app/ui/library_page.py` → `_build()` line 351

**Functions:**

* `__init__()` line 55 - -
* `set_count()` line 62 - -
* `set_selected()` line 66 - -
* `enterEvent()` line 70 - -
* `leaveEvent()` line 74 - -
* `mouseReleaseEvent()` line 78 - -
* `paintEvent()` line 82 - -  → calls: `self._symbol`
* `_symbol()` line 126 - -


### class `VideoCard`  (line 149)

One history record: thumbnail + badge, title, info, size and the five small buttons.

**Opened / created by:** `app/ui/library_page.py` → `refresh()` line 487

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 223 | `b (call line 197)` |  | - | clicked | `_sync` (284) | `self._sync_entry`, `self.refresh_sync`, `playlist_id` |
| 223 | `b (call line 199)` |  | - | clicked | `_play` (267) | `_full_path`, `self.page.message` |
| 223 | `b (call line 200)` |  | - | clicked | `_folder` (274) | `_full_path`, `reveal_file`, `self.page.message` |
| 223 | `b (call line 201)` |  | - | clicked | `_again` (299) | - |
| 223 | `b (call line 202)` |  | - | clicked | `_details` (302) | `self.page.show_details` |
| 223 | `b (call line 203)` |  | - | clicked | `_fav` (305) | `self.page.toggle_favorite` |
| 223 | `b (call line 204)` |  | - | clicked | `_delete` (308) | `self.page.delete_record` |

**Functions:**

* `__init__()` line 152 - -  → calls: `page.thumb_source`, `self._btn`, `self.refresh_fav`, `self.refresh_sync`, `card_tag`, `fmt_size`, `make_folder_icon`
* `_btn()` line 215 - -
* `set_width()` line 226 - Called by the page when the grid is laid out: the picture follows the card width.  → calls: `rounded_pixmap`, `make_thumb`
* `refresh_fav()` line 242 - -  → calls: `self.page.ctx.favorites.category_of`, `make_star_icon`, `self.page.ctx.favorites.label`
* `_sync_entry()` line 250 - The Playlist Sync entry of this playlist (None = not set up for synchronisation).  → calls: `playlist_id`, `self.page.ctx.sync.find`
* `refresh_sync()` line 257 - The sync button of a playlist is lit when the playlist is set up to synchronise (and switched on) (2.2.2).  → calls: `self._sync_entry`, `set_sync_button`
* `_play()` line 267 - -  → calls: `_full_path`, `self.page.message`
* `_folder()` line 274 - -  → calls: `_full_path`, `reveal_file`, `self.page.message`
* `_sync()` line 284 - Sync now. A playlist that is not set up yet is also added to Playlist Sync (daily) and the button turns on.  → calls: `self._sync_entry`, `self.refresh_sync`, `playlist_id`
* `_again()` line 299 - -
* `_details()` line 302 - -  → calls: `self.page.show_details`
* `_fav()` line 305 - -  → calls: `self.page.toggle_favorite`
* `_delete()` line 308 - -  → calls: `self.page.delete_record`

**Texts used (id · constant · English):**

<details><summary>show 12 texts</summary>

* MSG_138 · `M.ERR_NO_FOLDER` · 'The save folder does not exist yet. It will be created when you start a download.'
* MSG_158 · `M.TIP_PLAY` · 'Play'
* MSG_159 · `M.TIP_FOLDER` · 'Open folder'
* MSG_160 · `M.TIP_DELETE` · 'Delete'
* MSG_161 · `M.TIP_REDOWNLOAD` · 'Download again'
* MSG_162 · `M.TIP_FAV_ADD` · 'Add to favorites'
* MSG_163 · `M.TIP_FAV_REMOVE` · 'Remove from favorites'
* MSG_164 · `M.DL_FILE_MISSING` · 'The file was not found. It may have been moved or deleted.'
* MSG_178 · `M.DL_FILES` · '{count} files'
* MSG_238 · `M.TIP_SYNC` · 'Sync now'
* MSG_350 · `M.TIP_DETAILS` · 'Details'
* MSG_418 · `M.TIP_SYNC_ON` · 'Sync now (this playlist is synchronised automatically)'

</details>


### class `LibraryPage`  (line 313)

**Opened / created by:** `app/ui/main_window.py` → `_build_center()` line 324; `app/ui/main_window.py` → `_build_center()` line 325

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 330 | `self.search` | QLineEdit | - | textChanged | `refresh` (470) | `self._fill_filter`, `self._update_tiles`, `self._sorted`, `self._layout_cards`, `self._matches`, `self.ctx.favorites.is_favorite` |
| 331 | `self.filter` | ArrowComboBox | - | currentIndexChanged | `refresh` (470) | `self._fill_filter`, `self._update_tiles`, `self._sorted`, `self._layout_cards`, `self._matches`, `self.ctx.favorites.is_favorite` |
| 332 | `self.sort` | ArrowComboBox | - | currentIndexChanged | `refresh` (470) | `self._fill_filter`, `self._update_tiles`, `self._sorted`, `self._layout_cards`, `self._matches`, `self.ctx.favorites.is_favorite` |
| 352 | `tile` |  | - | clicked | `_tile_clicked` (400) | `tile.set_selected` |

**Functions:**

* `__init__()` line 318 - -  → calls: `self._build`
* `_build()` line 335 - -
* `_tile_clicked()` line 400 - -  → calls: `tile.set_selected`
* `mark_dirty()` line 409 - History or favorites changed somewhere else; reloaded when the page is shown.
* `thumb_source()` line 415 - -  → calls: `self.ctx.history.thumb_path`
* `_fill_filter()` line 423 - -  → calls: `fav.used_categories`, `fav.icon_of`, `make_emoji_icon`
* `_matches()` line 439 - -  → calls: `self.ctx.favorites.category_of`, `kind_of`
* `_sorted()` line 453 - -
* `_update_tiles()` line 461 - -  → calls: `self.tiles['video'].set_count`, `self.tiles['audio'].set_count`, `self.tiles['playlist'].set_count`, `kind_of`
* `refresh()` line 470 - -  → calls: `self._fill_filter`, `self._update_tiles`, `self._sorted`, `self._layout_cards`, `self._matches`, `self.ctx.favorites.is_favorite`
* `_layout_cards()` line 495 - Responsive grid: as many columns as fit, cards share the width.  → calls: `card.set_width`
* `showEvent()` line 515 - -
* `resizeEvent()` line 520 - -  → calls: `self._layout_cards`, `self._apply_style`
* `_apply_style()` line 529 - -
* `message()` line 538 - -  → calls: `exec_blurred`
* `show_details()` line 541 - -  → calls: `exec_blurred`, `self.ctx.favorites.category_of`, `self.ctx.favorites.label`
* `toggle_favorite()` line 546 - -  → calls: `fav.is_favorite`, `add_to_favorites`
* `delete_record()` line 555 - Delete button: asks whether the physical file(s) go too. Yes = the entry AND the file(s) are deleted (for a  → calls: `exec_blurred`, `delete_files`, `self.message`, `self.ctx.settings.download_dir`

**Texts used (id · constant · English):**

<details><summary>show 26 texts</summary>

* MSG_109 · `M.BTN_CANCEL1` · 'Cancel'
* MSG_122 · `M.ERR_TITLE` · 'Download error'
* MSG_153 · `M.DL_SEARCH` · 'Search downloads...'
* MSG_155 · `M.DL_FILTER_FAV` · 'All favorites'
* MSG_156 · `M.DL_EMPTY` · 'Nothing downloaded yet. Your finished downloads will appear here.'
* MSG_157 · `M.DL_EMPTY_FILTER` · 'No downloads match your search.'
* MSG_165 · `M.DEL_TITLE` · 'Delete download'
* MSG_180 · `M.DL_COUNT` · '{n} downloads'
* MSG_183 · `M.LIB_VAULT` · 'My Digital Vault'
* MSG_184 · `M.LIB_RECENT` · 'Recently Archived'
* MSG_185 · `M.LIB_VIDEOS` · 'Videos'
* MSG_186 · `M.LIB_MUSIC` · 'Music MP3'
* MSG_187 · `M.LIB_PLAYLISTS` · 'Playlists'
* MSG_188 · `M.LIB_FILES` · '{n} Files'
* MSG_189 · `M.LIB_PL_COUNT` · '{n} Playlists'
* MSG_190 · `M.SORT_DATE` · 'By Date'
* MSG_191 · `M.SORT_SIZE` · 'By Size'
* MSG_192 · `M.SORT_NAME` · 'By Name'
* MSG_193 · `M.ARCHIVE_TITLE` · 'Favorites Library'
* MSG_361 · `M.LIB_EMPTY_FAV` · 'Your library is empty. Add downloaded videos to a favorite category with the star button in the Archive.'
* MSG_399 · `M.DEL_ASK_FILE` · 'Do you also want to delete the physical file from your computer?'
* MSG_400 · `M.DEL_ASK_PL` · 'Do you also want to delete the physical files of this playlist, and its folder, from your computer?\n({count} files)'
* MSG_401 · `M.DEL_YES_FILE` · 'Yes, delete the file too'
* MSG_402 · `M.DEL_YES_PL` · 'Yes, delete files and folder'
* MSG_403 · `M.DEL_NO_FILE` · 'No, only remove from the list'
* MSG_404 · `M.DEL_PARTIAL` · 'Some files could not be deleted: {detail}'

</details>


## `app/ui/main_window.py`  (720 lines)

Main window (design guide: mainwindow-downloader.jpg).

**Files used:** `APP_VERSION`, `OWNER_DIR`


### class `Shell`  (line 63)

Rounded glass background of the whole window.

**Opened / created by:** `app/ui/main_window.py` → `__init__()` line 182

**Functions:**

* `paintEvent()` line 67 - -


### class `TitleBar`  (line 80)

**Opened / created by:** `app/ui/main_window.py` → `__init__()` line 187

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 101 | `self.lang_btn` | WinButton | - | clicked | `lambda: win.show_language_menu(self.l…` | - |
| 105 | `b` | WinButton | - | clicked | `win.showMinimized` | - |
| 105 | `b` | WinButton | - | clicked | `win.toggle_max` | - |
| 105 | `b` | WinButton | - | clicked | `win.close` | - |

**Functions:**

* `__init__()` line 81 - -  → calls: `make_app_icon`, `win.show_language_menu`
* `set_counter()` line 108 - -
* `resizeEvent()` line 113 - The window size changed (maximise / restore / drag): the buttons are at new places, so forget the old hover.  → calls: `self.refresh_buttons`
* `refresh_buttons()` line 119 - -  → calls: `b.sync_hover`
* `mousePressEvent()` line 123 - -
* `mouseDoubleClickEvent()` line 127 - -  → calls: `self.win.toggle_max`

**Texts used (id · constant · English):**

<details><summary>show 1 texts</summary>

* MSG_259 · `M.TIP_LANGUAGE` · 'Interface language'

</details>


### class `ClickSound`  (line 131)

Application event filter: every click on a button (not a disabled one) plays the click sound (2.2.7).

**Opened / created by:** `app/ui/main_window.py` → `__init__()` line 170

**Functions:**

* `eventFilter()` line 134 - -  → calls: `sounds.play`


### class `MainWindow`  (line 145)

**Opened / created by:** `main.py` → `main()` line 121; `main.py` → `open_window()` line 121

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 210 | `self.library_page` |  | - | changed | `self.archive_page.mark_dirty` | - |
| 211 | `self.archive_page` |  | - | changed | `self.library_page.mark_dirty` | - |
| 213 | `self.library_page` |  | - | changed | `self.sync_page.mark_dirty` | - |
| 214 | `self.archive_page` |  | - | changed | `self.sync_page.mark_dirty` | - |
| 232 | `self.gauge_timer` |  | - | timeout | `_sample_gauges` (456) | `self._sample_gauges_impl` |
| 238 | `self.online_timer` |  | - | timeout | `_poll_online` (524) | `self._check_done` |
| 284 | `b` | NavButton | - | clicked | `select_page` (401) | `b.set_active` |
| 303 | `btn` | QPushButton | - | clicked | `show_info` (434) | `self.info_page.show_kind`, `b.set_active` |
| 499 | `act` |  | - | triggered | `change_language` (502) | `self.active_download_percents`, `exec_blurred` |

**Functions:**

* `__init__()` line 152 - -  → calls: `sounds.attach`, `self.select_page`, `self._apply_scale`, `self._update_nav_count`, `self.title_bar.set_counter`, `self._show_counter`, `make_app_qicon`
* `_build_header()` line 243 - Header: application icon, name, the version below it (smaller) and the advertisement space for the rest.  → calls: `load_links`, `make_app_icon`
* `_build_sidebar()` line 273 - -  → calls: `sounds.play`, `self.select_page`, `self.show_info`
* `_build_center()` line 311 - -
* `_build_gauges()` line 340 - -  → calls: `cap`
* `page_index()` line 388 - -
* `_add_playlist()` line 391 - 'Add Playlist' of the Playlist Sync page: a playlist is added by downloading it once.  → calls: `self.select_page`, `self.new_page._log`, `self.page_index`
* `_redownload()` line 396 - 'Download again' button of the Downloads page -> New Download with the same link / folder.  → calls: `self.select_page`, `self.new_page.prefill`, `self.page_index`
* `select_page()` line 401 - -  → calls: `b.set_active`
* `_update_nav_count()` line 407 - The Downloads label of the side menu shows how many files are downloading now + waiting (2.2.2).  → calls: `self.new_page.mgr.queue.counts`, `self.page_index`, `b.set_text`
* `page_state()` line 420 - Which work area is shown now: (page index, info kind or None). Used to keep the place after a language change.
* `restore_page()` line 424 - Show again the work area saved by page_state() (no fade: the window was just rebuilt).  → calls: `self.show_info`, `self.select_page`
* `show_info()` line 434 - A link of the corner (Reviews, Help, About us, Contact us, Donate): shown in the work area.  → calls: `self.info_page.show_kind`, `b.set_active`
* `_show_app_speed()` line 442 - -  → calls: `auto_max`, `self.g_app.set_state`, `self.downloads_mgr.queue.speed`
* `downloads_mgr()` line 448 - -
* `_size_text()` line 451 - '85 GB' / '700 MB' for the ends of a gauge scale.  → calls: `human_size`
* `_sample_gauges()` line 456 - -  → calls: `self._sample_gauges_impl`
* `_sample_gauges_impl()` line 463 - Once a second: network speed, disk I/O, downloaded size, free space (see app/sysmon.py).  → calls: `self.mon.sample`, `auto_max`, `self.g_net.set_state`, `self._show_app_speed`, `self.downloads_mgr.queue.downloaded_bytes`, `human_size`, `self.g_total.set_state`
* `_settings_saved()` line 489 - Settings page saved / restored the settings.  → calls: `self.new_page.apply_defaults`, `self._ads_updated`, `self.ctx.downloads.queue.pump`, `local_ads`, `load_links`
* `show_language_menu()` line 495 - -  → calls: `self.change_language`
* `change_language()` line 502 - Language icon / Settings: the whole window is rebuilt in the chosen language (main.py).  → calls: `self.active_download_percents`, `exec_blurred`
* `force_close()` line 514 - -
* `_ads_updated()` line 518 - -  → calls: `self.ad_banner.set_paths`, `self.new_page._log`
* `_poll_online()` line 524 - The online check (made while the splash screen was shown) may still be running: wait for it.  → calls: `self._check_done`
* `_show_counter()` line 533 - Corner counter of the downloads of the program (downloads_counter.txt of the online folder).  → calls: `self.title_bar.set_counter`
* `_check_done()` line 545 - The online folder was read: show the allowed ads, the counter, and tell about a higher program version.  → calls: `self._ads_updated`, `self._show_counter`, `self.new_page._log`, `exec_blurred`, `load_counter`
* `_notify_due_playlists()` line 566 - -  → calls: `self._notify_due_playlists_impl`
* `_notify_due_playlists_impl()` line 573 - 'Notify me when a playlist has new videos to sync': playlists whose next sync date has come.  → calls: `exec_blurred`, `self.sync_ctrl.run_background`, `self.ctx.sync.is_due`, `self.ctx.history.find`
* `toggle_max()` line 594 - -
* `changeEvent()` line 597 - -  → calls: `super().changeEvent`
* `resizeEvent()` line 605 - -  → calls: `self._apply_scale`
* `_apply_scale()` line 612 - Make the whole interface follow the window size.  → calls: `b.set_scale`, `make_app_icon`
* `active_download_percents()` line 644 - Progress (%) of every real download that is still running (New Download tab).  → calls: `self.new_page.active_percent`
* `abort_all_downloads()` line 649 - 'Abort Downloads' of the exit window: stop yt-dlp and delete the partial files.  → calls: `self.new_page.cancel_for_exit`
* `_blur_background()` line 653 - -
* `request_exit()` line 661 - True = the application may close.  → calls: `self.active_download_percents`, `self._blur_background`, `fb.save_rating`, `self._send_rating`, `self.new_page.mgr.queue.counts_by_state`, `self.abort_all_downloads`, `fb.current`
* `_send_rating()` line 685 - A new / changed rating (or one that could not be sent before) goes to the Google form. Waits a few seconds at most.  → calls: `self.ctx.feedback.current`
* `closeEvent()` line 701 - -  → calls: `self.request_exit`

**Texts used (id · constant · English):**

<details><summary>show 39 texts</summary>

* MSG_001 · `M.APP_NAME` · 'TubeArchive Pro'
* MSG_009 · `M.VERSION` · 'Version {version}'
* MSG_011 · `M.NAV_NEW` · 'New Download'
* MSG_013 · `M.NAV_QUEUE` · 'Archive'
* MSG_014 · `M.NAV_LIBRARY` · 'Library'
* MSG_016 · `M.NAV_SETTINGS` · 'Settings'
* MSG_023 · `M.ANALYTICS` · 'Active Analytics & Gauges'
* MSG_029 · `M.UNIT_MBS` · 'MB/s'
* MSG_030 · `M.AD_PLACEHOLDER` · 'Advertisement space'
* MSG_151 · `M.NAV_DOWNLOADS` · 'Downloads'
* MSG_182 · `M.NAV_PLAYLIST` · 'Playlist Sync'
* MSG_245 · `M.SYP_ADD_HINT` · 'Paste the playlist link in New Download and press Start.'
* MSG_259 · `M.TIP_LANGUAGE` · 'Interface language'
* MSG_260 · `M.LANG_BUSY` · 'Downloads are running. Finish or cancel them before changing the language.'
* MSG_261 · `M.G_NET` · 'NETWORK SPEED'
* MSG_262 · `M.G_APP` · 'APP SPEED'
* MSG_263 · `M.G_TOTAL` · 'DOWNLOADED'
* MSG_264 · `M.G_FREE` · 'FREE SPACE'
* MSG_265 · `M.G_DISK` · 'DISK I/O'
* MSG_266 · `M.UNIT_GB` · 'GB'
* MSG_267 · `M.UNIT_MB` · 'MB'
* MSG_272 · `M.LG_ADS` · 'Advertisements refreshed: {n} file(s).'
* MSG_281 · `M.LG_UPDATE` · 'New version {v} is available.'
* MSG_282 · `M.LG_ADS_FAIL` · 'Could not read the online folder (updates / ads): {detail}'
* MSG_345 · `M.G_QUEUE` · 'FILES'
* MSG_346 · `M.UNIT_FILES` · 'files'
* MSG_362 · `M.LNK_REVIEWS` · 'Reviews'
* MSG_363 · `M.LNK_HELP` · 'Help'
* MSG_364 · `M.LNK_ABOUT` · 'About us'
* MSG_365 · `M.LNK_CONTACT` · 'Contact us'
* MSG_366 · `M.LNK_DONATE` · 'Donate'
* MSG_368 · `M.CHANNEL_TIP` · 'YouTube channel'
* MSG_377 · `M.CNT_TIP` · 'Downloads of TubeArchive Pro'
* MSG_378 · `M.CNT_OFFLINE` · '(last known value)'
* MSG_428 · `M.DUE_TITLE` · 'Playlists ready for sync'
* MSG_429 · `M.DUE_TEXT` · '{n} playlist(s) need to be synchronised:\n{names}\n\nWhat do you want to do?'
* MSG_430 · `M.DUE_NOW` · 'Sync now'
* MSG_431 · `M.DUE_CHECK` · 'Let me check'
* MSG_432 · `M.DUE_LATER` · 'Later'

</details>


## `app/ui/new_download_page.py`  (1045 lines)

'New Download' tab (design guide: mainwindow-downloader.jpg + file-downloaded dialog).


### class `NewDownloadPage`  (line 79)

**Opened / created by:** `app/ui/main_window.py` → `_build_center()` line 322

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 266 | `self.url` | QLineEdit | - | returnPressed | `_fetch` (358) | `self._fetch_now`, `log_fetch`, `self._set_state`, `self._error` |
| 267 | `self.url` | QLineEdit | - | textChanged | `_url_changed` (344) | `self.mgr.invalidate`, `self.title.set_full_text`, `self._rebuild_quality`, `self._set_state`, `looks_like_url` |
| 268 | `self.browse` | QPushButton | “Browse...” | clicked | `_browse` (629) | `self._save_folder` |
| 269 | `self.folder` | QLineEdit | - | editingFinished | `_save_folder` (636) | `self._show_space_warning` |
| 270 | `self.fmt` | ArrowComboBox | - | currentIndexChanged | `_format_changed` (335) | `self._rebuild_quality` |
| 271 | `self.quality` | ArrowComboBox | - | currentIndexChanged | `_quality_changed` (338) | `self._update_meta` |
| 272 | `self.b_start` | QPushButton | “Start Download” | clicked | `_start` (712) | `self._in_queue`, `is_playlist_url`, `self._reset_after_enqueue`, `looks_like_url`, `self._error`, `self._check_tools` |
| 273 | `self.b_check` | QPushButton | “Check” | clicked | `_fetch` (358) | `self._fetch_now`, `log_fetch`, `self._set_state`, `self._error` |
| 274 | `self.b_pause` | QPushButton | “Pause” | clicked | `_pause_clicked` (652) | `self._sync_buttons`, `q.pause_all`, `self._log`, `q.resume_all` |
| 275 | `self.b_cancel` | QPushButton | “Cancel” | clicked | `_cancel_clicked` (665) | `self.mgr.queue.counts`, `exec_blurred`, `self._sync_buttons`, `self._log`, `self.mgr.queue.cancel_all` |
| 276 | `self.b_folder` | QPushButton | “Open Folder” | clicked | `_open_folder` (813) | `self._log` |

**Functions:**

* `__init__()` line 84 - -  → calls: `self.mgr.sync_tools`, `self._build`, `self._wire`, `self._rescale`, `self._fill_formats`, `self._rebuild_quality`, `self._set_state`
* `_build()` line 114 - -  → calls: `self._card`, `make_play_icon`, `self.ctx.settings.download_dir`
* `_card()` line 254 - -
* `_wire()` line 265 - -  → calls: `self._open_folder`, `self._sync_buttons`
* `_fill_formats()` line 290 - -
* `cur_format()` line 303 - -
* `cur_quality()` line 306 - -
* `_rebuild_quality()` line 309 - Quality list depends on the file type: heights for video, kbps / kHz for audio.  → calls: `is_audio`, `quality_options`, `self._update_meta`, `self.cur_format`, `parse_quality`, `max_height`, `available_heights`
* `_format_changed()` line 335 - -  → calls: `self._rebuild_quality`
* `_quality_changed()` line 338 - -  → calls: `self._update_meta`
* `_url_changed()` line 344 - -  → calls: `self.mgr.invalidate`, `self.title.set_full_text`, `self._rebuild_quality`, `self._set_state`, `looks_like_url`
* `_fetch()` line 358 - -  → calls: `self._fetch_now`, `log_fetch`, `self._set_state`, `self._error`
* `_fetch_now()` line 368 - -  → calls: `self._set_state`, `self._log`, `self.mgr.fetch`, `looks_like_url`, `self._error`, `self._duplicate_ok`
* `_duplicate_ok()` line 382 - Check / Start: a single video found in the history (and its file still there) asks what to do (2.0.5).  → calls: `self.ctx.history.find_video`, `self.ctx.history.thumb_path`, `exec_blurred`, `is_playlist_url`, `self._open_folder`
* `_info_ready()` line 413 - -  → calls: `size_table`, `self.title.set_full_text`, `self._show_thumb`, `self._set_state`, `self._rebuild_quality`, `self._log`, `available_heights`
* `_info_failed()` line 433 - -  → calls: `self._set_state`, `self._error`
* `_thumb_size()` line 440 - -
* `_show_thumb()` line 445 - Picture of the video (or a plain placeholder when the site gave none), at the current scale.  → calls: `self._thumb_size`, `rounded_pixmap`, `make_thumb`
* `_sync_card()` line 454 - The frame shows the link that was read; when nothing is read and downloads are running or waiting it shows the  → calls: `self.mgr.queue.counts_by_state`
* `resizeEvent()` line 470 - -  → calls: `self._rescale`
* `_rescale()` line 476 - -  → calls: `self._thumb_size`, `self._show_thumb`, `r`, `make_state_icon`
* `estimate_for()` line 515 - Estimated bytes of this video / playlist for a format + quality: the table kept in memory, or the playlist sum.  → calls: `estimate_size`, `estimate_playlist_size`
* `space_needed_for()` line 526 - Free bytes that a download of `est` bytes needs: twice the size (parts + final file); a playlist keeps its  → calls: `space_needed`
* `_update_meta()` line 540 - 'Estimated size: 850 MB | Duration: 12:30' under the title + the free-space warning.  → calls: `self._show_space_warning`, `self.estimate_for`, `self.cur_format`, `self.cur_quality`, `fmt_size`, `fmt_time`
* `_folder_path()` line 562 - -  → calls: `self.ctx.settings.download_dir`
* `_show_space_warning()` line 565 - -  → calls: `self.space_needed_for`, `free_bytes`, `self._folder_path`, `drive_name`, `fmt_size`
* `_space_ok()` line 575 - Before a download starts: is there room on the partition of the folder? When not, the user may lower the  → calls: `self.estimate_for`, `self.space_needed_for`, `self._folder_path`, `free_bytes`, `self.cur_format`, `exec_blurred`, `self._log`
* `_set_state()` line 613 - -  → calls: `self._sync_card`
* `active_percent()` line 622 - Used by the exit check of the main window: progress of every unfinished link / playlist.  → calls: `self.mgr.queue.active_percents`
* `_browse()` line 629 - -  → calls: `self._save_folder`
* `_save_folder()` line 636 - The folder chosen here is for this download only; the default folder is set in Settings.  → calls: `self._show_space_warning`
* `_sync_buttons()` line 642 - -  → calls: `q.counts`, `self._sync_card`
* `_pause_clicked()` line 652 - -  → calls: `self._sync_buttons`, `q.pause_all`, `self._log`, `q.resume_all`
* `_cancel_clicked()` line 665 - -  → calls: `self.mgr.queue.counts`, `exec_blurred`, `self._sync_buttons`, `self._log`, `self.mgr.queue.cancel_all`
* `apply_defaults()` line 679 - Settings were saved / restored: show the new default folder, format and quality.  → calls: `self._fill_formats`, `self._rebuild_quality`, `self.ctx.settings.download_dir`
* `_check_tools()` line 690 - -  → calls: `self._error`
* `_folder_ok()` line 699 - -  → calls: `self._error`
* `_in_queue()` line 707 - -
* `_start()` line 712 - -  → calls: `self._in_queue`, `is_playlist_url`, `self._reset_after_enqueue`, `looks_like_url`, `self._error`, `self._check_tools`, `self._folder_ok`
* `_enqueue_video()` line 750 - -  → calls: `self.mgr.queue.add_video`, `self._log`, `self.cur_format`, `self.cur_quality`
* `_enqueue_playlist()` line 759 - -  → calls: `self.mgr.queue.add_playlist`, `self._log`
* `_reset_after_enqueue()` line 768 - The page is free for the next link (progress is on the Downloads page).  → calls: `self.mgr.invalidate`, `self.title.set_full_text`, `self._rebuild_quality`, `self._set_state`, `self._sync_card`
* `start_sync()` line 784 - Download the chosen new videos of an already downloaded playlist into its folder.  → calls: `self._in_queue`, `self.ctx.history.thumb_path`, `self._log`, `self._enqueue_playlist`, `self._check_tools`, `self._folder_ok`
* `cancel_for_exit()` line 809 - Called by the main window when the user chooses 'Abort Downloads'.  → calls: `self.mgr.queue.cancel_all`
* `_open_folder()` line 813 - -  → calls: `self._log`
* `_reveal()` line 821 - -  → calls: `reveal_file`
* `prefill()` line 824 - 'Download again' of the Library / Archive: same link, folder, format and quality; the user may change them.  → calls: `self._save_folder`, `self._rebuild_quality`, `self._log`, `self._url_changed`, `looks_like_url`, `self._fetch`
* `_task_done()` line 844 - -  → calls: `fmt_size`, `self._log`, `sounds.play`, `self._save_history`, `self._show_success`
* `_task_failed()` line 856 - -  → calls: `self._error`, `self._log`
* `_task_cancelled()` line 864 - -  → calls: `self._log`
* `_group_done()` line 868 - -  → calls: `sounds.play`, `self._save_history_group`, `self._log`, `self._sync_finished`, `fmt_size`, `self._show_success`, `self._notify_sync`
* `_save_history()` line 891 - Put the finished download in history.json (+ its thumbnail + the description). Never breaks the success flow.  → calls: `self.ctx.history.new_record`, `self.ctx.history.same_file`, `self.ctx.favorites.category_of`
* `_save_history_group()` line 917 - -  → calls: `self._videos_from`, `now_text`, `self.ctx.history.new_record`, `self._log`, `self._schedule_name`
* `_videos_from()` line 939 - {video id: {...}} of the videos that this download put on the disk (needed by 'Sync now').  → calls: `now_text`
* `_schedule_name()` line 955 - -
* `_sync_finished()` line 958 - 'Download & Sync' ended: remember the new videos, schedule the next sync.  → calls: `self._videos_from`, `now_text`, `self._log`, `self.ctx.sync.synced_now`
* `_notify_sync()` line 976 - 'Notify me when a playlist has been updated' (Settings > Notifications).  → calls: `exec_blurred`
* `_fav_from_dialog()` line 983 - -  → calls: `add_to_favorites`, `self._log`, `self.ctx.favorites.category_of`
* `_show_success()` line 990 - -  → calls: `self._reveal`, `self._fav_from_dialog`
* `_log()` line 1027 - -
* `_error()` line 1032 - Error line in the system log + an error window.  → calls: `self._log`

**Texts used (id · constant · English):**

<details><summary>show 85 texts</summary>

* MSG_022 · `M.SYSTEM_LOG` · 'System Log :'
* MSG_041 · `M.BTN_BROWSE` · 'Browse...'
* MSG_042 · `M.BTN_START` · 'Start Download'
* MSG_083 · `M.ND_URL` · 'Video or Playlist URL:'
* MSG_084 · `M.ND_URL_PH` · 'Paste Video or Playlist URL here...'
* MSG_085 · `M.ND_SAVE_DIR` · 'Save Directory:'
* MSG_086 · `M.ND_QUALITY` · 'Resolution Quality:'
* MSG_087 · `M.ND_QUALITY_AUDIO` · 'Audio Quality:'
* MSG_088 · `M.ND_FORMAT` · 'File Type:'
* MSG_089 · `M.ND_VIDEO_TAG` · 'Video'
* MSG_090 · `M.ND_AUDIO_TAG` · 'Audio'
* MSG_091 · `M.ND_BEST` · 'Best Quality'
* MSG_092 · `M.ND_BROWSE_TITLE` · 'Select the download folder'
* MSG_093 · `M.ND_READY` · 'Ready to download'
* MSG_094 · `M.ND_FETCHING` · 'Reading video information...'
* MSG_102 · `M.ND_EST` · 'Estimated size: {size}'
* MSG_103 · `M.ND_EST_UNKNOWN` · 'Estimated size: unknown'
* MSG_104 · `M.ND_DURATION` · 'Duration: {duration}'
* MSG_105 · `M.ND_PLAYLIST` · 'Playlist · {count} videos'
* MSG_107 · `M.BTN_PAUSE1` · 'Pause'
* MSG_108 · `M.BTN_RESUME1` · 'Resume'
* MSG_109 · `M.BTN_CANCEL1` · 'Cancel'
* MSG_110 · `M.BTN_FOLDER1` · 'Open Folder'
* MSG_111 · `M.LG_READY` · 'System ready. Powered by yt-dlp.'
* MSG_112 · `M.LG_FETCH` · 'Reading information from the link...'
* MSG_113 · `M.LG_FOUND` · 'Video found: {title}'
* MSG_114 · `M.LG_FOUND_PL` · 'Playlist found: {title} ({count} videos)'
* MSG_119 · `M.LG_CANCEL` · 'Download cancelled. Partial files were deleted.'
* MSG_120 · `M.LG_DONE` · 'Download completed: {name} ({size})'
* MSG_121 · `M.LG_PL_DONE` · 'Playlist finished: {count} files saved in {folder}'
* MSG_122 · `M.ERR_TITLE` · 'Download error'
* MSG_136 · `M.ERR_UNKNOWN` · 'An unexpected error occurred: {detail}'
* MSG_138 · `M.ERR_NO_FOLDER` · 'The save folder does not exist yet. It will be created when you start a download.'
* MSG_140 · `M.OK_TITLE` · 'File Successfully Downloaded!'
* MSG_141 · `M.OK_TITLE_PL` · 'Playlist Successfully Downloaded!'
* MSG_142 · `M.OK_FILE` · 'File Name:'
* MSG_143 · `M.OK_FILES` · 'Files:'
* MSG_144 · `M.OK_QUALITY` · 'Quality:'
* MSG_145 · `M.OK_SIZE` · 'Size:'
* MSG_146 · `M.OK_LOCATION` · 'Location:'
* MSG_158 · `M.TIP_PLAY` · 'Play'
* MSG_175 · `M.LG_FAV_ADDED` · 'Added to favorites ({category}).'
* MSG_177 · `M.LG_PREFILLED` · 'Link loaded from your history. You can change the folder, format and quality.'
* MSG_199 · `M.PS_DAILY` · 'Daily'
* MSG_200 · `M.PS_WEEKLY` · 'Weekly'
* MSG_201 · `M.PS_MONTHLY` · 'Monthly'
* MSG_219 · `M.LG_SYNC_START` · "Sync started: {n} video(s) of '{title}'."
* MSG_220 · `M.LG_SYNC_DONE` · "Sync completed: {n} new video(s) added to '{title}'."
* MSG_222 · `M.LG_SYNC_ADDED` · 'Playlist added to sync ({schedule}). Next sync: {date}.'
* MSG_268 · `M.NT_SYNC_TITLE` · 'Playlist updated'
* MSG_269 · `M.NT_SYNC_TEXT` · "'{title}': {n} new video(s) were downloaded."
* MSG_316 · `M.LG_QUEUED` · 'Added to the download queue: {title}'
* MSG_317 · `M.LG_QUEUED_PL` · 'Playlist added to the queue: {title} ({count} videos)'
* MSG_320 · `M.LG_IN_QUEUE` · 'This link is already in the download queue.'
* MSG_321 · `M.LG_TASK_FAIL` · 'Failed: {title} - {error}'
* MSG_322 · `M.LG_PL_PARTIAL` · 'Playlist finished: {count} downloaded, {skipped} skipped, {failed} failed.'
* MSG_323 · `M.LG_PL_NOTHING` · 'Nothing was downloaded from the playlist: {title}'
* MSG_380 · `M.ND_ANALYZE` · 'Check'
* MSG_381 · `M.ND_ANALYZE_TIP` · 'Read the link: fills the format and quality lists with the values that are really available, keeps the estimated sizes and checks the free space of the target drive'
* MSG_382 · `M.LG_ANALYZED` · 'Link read. Available resolutions: {list}'
* MSG_383 · `M.SP_WARN_LINE` · '⚠ Not enough free space on {drive}: free {free}, needed about {need}'
* MSG_384 · `M.SP_TITLE` · 'Not enough free space'
* MSG_385 · `M.SP_TEXT` · 'This download cannot be saved on {drive}.\n\nFree space: {free}\nNeeded: about {need}\n(estimated size {size}; the downloader needs extra working space to build the final file)\n\nLower the quality or choose a folder on a drive with more free space.'
* MSG_386 · `M.SP_LOWER` · 'Lower quality: {q}'
* MSG_387 · `M.SP_FOLDER` · 'Choose another folder'
* MSG_388 · `M.SP_CANCEL` · 'Cancel'
* MSG_389 · `M.SP_NONE_FITS` · 'Even the lowest quality does not fit on this drive.'
* MSG_390 · `M.LG_SPACE_LOW` · 'Not enough free space on {drive} - the download was not started.'
* MSG_391 · `M.LG_PAUSED_ALL` · 'All running downloads were paused.'
* MSG_392 · `M.LG_RESUMED_ALL` · 'Paused downloads were resumed.'
* MSG_393 · `M.LG_CANCELLED_ALL` · 'All downloads were cancelled. Partial files were deleted.'
* MSG_394 · `M.CF_CANCEL_TITLE` · 'Cancel all downloads?'
* MSG_395 · `M.CF_CANCEL_TEXT` · 'Running and waiting downloads will be stopped and their partial files deleted.'
* MSG_396 · `M.CF_CANCEL_YES` · 'Yes, cancel them'
* MSG_397 · `M.CF_CANCEL_NO` · 'No, continue'
* MSG_398 · `M.LG_NO_ACTIVE` · 'There is no running download.'
* MSG_407 · `M.DUP_TITLE` · 'Already downloaded'
* MSG_408 · `M.DUP_TEXT` · 'This video was already downloaded on {date}:\n{title}\n({format} {quality}) in {folder}\n\nWhat do you want to do?'
* MSG_409 · `M.DUP_REDOWNLOAD` · 'Redownload'
* MSG_410 · `M.DUP_TEXT_GONE` · 'This video was downloaded on {date}:\n{title}\n({format} {quality})\n\nBut the file is no longer in its folder:\n{folder}\n\nWhat do you want to do?'
* MSG_411 · `M.DUP_OPEN_FOLDER` · 'Open folder'
* MSG_412 · `M.ND_DL_TITLE` · 'Downloading'
* MSG_413 · `M.ND_CNT_RUNNING` · 'Downloading now'
* MSG_414 · `M.ND_CNT_QUEUE` · 'In the queue'
* MSG_419 · `M.ND_CNT_PAUSED` · 'Paused'

</details>


## `app/ui/pages.py`  (124 lines)

Work-area pages. INTERFACE ONLY: no button has a function yet.

**Functions of the module:**

* `_title()` line 27 - -


### class `PlaceholderPage`  (line 34)

Used for sections whose design is not drawn yet.

**Functions:**

* `__init__()` line 37 - -  → calls: `_title`

**Texts used (id · constant · English):**

<details><summary>show 1 texts</summary>

* MSG_031 · `M.COMING_SOON` · 'This section is coming soon'

</details>


### class `DownloaderPage`  (line 50)

Download list + action buttons + system log (see mainwindow-downloader.jpg).

**Functions:**

* `__init__()` line 68 - -  → calls: `it.set_progress`, `make_thumb`
* `demo_tick()` line 117 - DEMO only: moves the progress bars so the interface looks alive.  → calls: `it.set_progress`

**Texts used (id · constant · English):**

<details><summary>show 11 texts</summary>

* MSG_018 · `M.BTN_RESUME` · 'Resume All'
* MSG_019 · `M.BTN_PAUSE` · 'Pause All'
* MSG_020 · `M.BTN_CANCEL` · 'Cancel All'
* MSG_021 · `M.BTN_OPEN_FOLDER` · 'Open Archive Folder'
* MSG_022 · `M.SYSTEM_LOG` · 'System Log :'
* MSG_028 · `M.ACTIVE_DOWNLOAD` · 'Active Download'
* MSG_029 · `M.UNIT_MBS` · 'MB/s'
* MSG_056 · `M.LOG_1` · '[TubeArchive Pro] Multi-thread downloading active.'
* MSG_057 · `M.LOG_2` · '[System] Powered by yt-dlp. Queue running at {speed} MB/s.'
* MSG_058 · `M.LOG_3` · '[Archive] Metadata matched for {count} active streams.'
* MSG_194 · `M.QUEUED` · 'Waiting in queue'

</details>


## `app/ui/settings_page.py`  (571 lines)

Settings: saved in data/config/current_settings.json; the factory values are in default_settings.json.
Favorite categories are saved at once in the favorites file (not by Save & Apply).


### class `_Collector`  (line 44)

Collects the cards of one column; SettingsPage._relayout() puts them into the real layouts.

**Opened / created by:** `app/ui/settings_page.py` → `__init__()` line 89; `app/ui/settings_page.py` → `__init__()` line 90

**Functions:**

* `__init__()` line 47 - -
* `addWidget()` line 50 - -
* `addStretch()` line 53 - -


### class `SettingsPage`  (line 57)

**Opened / created by:** `app/ui/main_window.py` → `_build_center()` line 332

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 97 | `self.audio_fmt` | ArrowComboBox | - | currentIndexChanged | `_fill_audio_quality` (388) | `self._fill_quality`, `self._hq` |
| 99 | `self.audio_q` | ArrowComboBox | - | currentIndexChanged | `_hq` (397) | - |
| 120 | `self.fmt` | ArrowComboBox | - | currentIndexChanged | `_fill_video_quality` (393) | `self._fill_quality` |
| 143 | `add` | QPushButton | “Add new category” | clicked | `_add_category` (542) | `fav.add_category`, `self.refresh_categories`, `exec_blurred` |
| 157 | `browse` | QPushButton | “Browse” | clicked | `_browse` (464) | - |
| 179 | `self.speed` | QSlider | - | valueChanged | `_speed_text` (402) | - |
| 232 | `b` | QPushButton | “Apply and Save” | clicked | `save` (470) | `self._done` |
| 232 | `b` | QPushButton | “Reset to Default” | clicked | `restore_defaults` (517) | `exec_blurred`, `self.ctx.settings.reset_to_defaults`, `self._done` |
| 232 | `b` | QPushButton | “Cancel” | clicked | `discard` (529) | - |
| 374 | `b (call line 130)` |  | - | clicked | `_edit_category` (549) | `fav.icon_of`, `fav.edit_category`, `self.refresh_categories`, `exec_blurred` |
| 374 | `b (call line 131)` |  | - | clicked | `_delete_category` (560) | `exec_blurred`, `fav.delete_category`, `self.refresh_categories` |

**Functions:**

* `__init__()` line 62 - -  → calls: `self._card`, `self._stack`, `self._toggle`, `self._mini`, `self._relayout`, `ctx.settings.subscribe`, `make_trash_icon`
* `_relayout()` line 243 - Two columns (like the mock-up) while there is room, one column in a narrow work area.
* `resizeEvent()` line 261 - -  → calls: `self._fit`
* `showEvent()` line 265 - -
* `_fit()` line 269 - Every card must be visible at any window size: the page starts from the scale that suits the size of the  → calls: `self._relayout`, `self._rescale`
* `_rescale()` line 295 - Fonts, spacing and control heights follow the size of the work area.  → calls: `r`
* `_card()` line 332 - -
* `_stack()` line 350 - Label above a drop-down (like the mock-up); `extra` sits at the right of the drop-down.
* `_toggle()` line 360 - -
* `_mini()` line 368 - -
* `_fill_quality()` line 378 - -  → calls: `quality_options`, `quality_label`
* `_fill_audio_quality()` line 388 - -  → calls: `self._fill_quality`, `self._hq`
* `_fill_video_quality()` line 393 - -  → calls: `self._fill_quality`
* `_hq()` line 397 - -
* `_speed_text()` line 402 - -
* `refresh_categories()` line 406 - -  → calls: `fav.icon_of`, `make_emoji_icon`
* `load()` line 426 - Show the saved settings in the controls.  → calls: `self._fill_video_quality`, `self._fill_audio_quality`, `self._speed_text`, `self.refresh_categories`, `parse_quality`, `st.download_dir`
* `_browse()` line 464 - -
* `save()` line 470 - -  → calls: `self._done`
* `_on_setting()` line 500 - A setting was changed by another screen (e.g. 'Don't show this message again' in a window): show the same
* `restore_defaults()` line 517 - -  → calls: `exec_blurred`, `self.ctx.settings.reset_to_defaults`, `self._done`
* `discard()` line 529 - Cancel: the controls show the saved settings again.
* `_done()` line 534 - -
* `_add_category()` line 542 - -  → calls: `fav.add_category`, `self.refresh_categories`, `exec_blurred`
* `_edit_category()` line 549 - -  → calls: `fav.icon_of`, `fav.edit_category`, `self.refresh_categories`, `exec_blurred`
* `_delete_category()` line 560 - -  → calls: `exec_blurred`, `fav.delete_category`, `self.refresh_categories`

**Texts used (id · constant · English):**

<details><summary>show 51 texts</summary>

* MSG_049 · `M.SET_LANGUAGE` · 'Language'
* MSG_053 · `M.SET_ADS` · 'Show partner advertisements'
* MSG_061 · `M.SET_TITLE` · 'Application Settings'
* MSG_089 · `M.ND_VIDEO_TAG` · 'Video'
* MSG_091 · `M.ND_BEST` · 'Best Quality'
* MSG_092 · `M.ND_BROWSE_TITLE` · 'Select the download folder'
* MSG_109 · `M.BTN_CANCEL1` · 'Cancel'
* MSG_249 · `M.ST_DEF_FORMAT` · 'Default format'
* MSG_250 · `M.ST_DEF_QUALITY` · 'Default quality'
* MSG_251 · `M.ST_NOTIFY` · 'Notifications'
* MSG_252 · `M.ST_NOTIFY_SUCCESS` · 'Notify me when a file is downloaded successfully'
* MSG_253 · `M.ST_NOTIFY_SYNC` · 'Notify me when a playlist has been updated (sync completed)'
* MSG_254 · `M.ST_NOTIFY_NEW` · 'Notify me when a playlist has new videos to sync'
* MSG_255 · `M.ST_BROWSE` · 'Browse'
* MSG_256 · `M.ST_SAVED` · 'Settings saved.'
* MSG_257 · `M.ST_RESTORED` · 'Default settings restored.'
* MSG_258 · `M.ST_RESTORE_ASK` · 'Restore all settings to their default values?'
* MSG_280 · `M.ST_NOTIFY_UPDATE` · 'Notify me when a new version is available'
* MSG_283 · `M.ST_AUDIO` · 'Audio Quality Settings'
* MSG_284 · `M.ST_AUDIO_FMT` · 'Preferred Audio Format'
* MSG_285 · `M.ST_AUDIO_BR` · 'Audio Bitrate'
* MSG_286 · `M.ST_CONVERT` · 'Always convert to selected bitrate'
* MSG_287 · `M.ST_EXTRACT` · 'Extract audio from video file'
* MSG_288 · `M.ST_SAVE_LOC` · 'Default Save Location'
* MSG_289 · `M.ST_SUBFOLDERS` · 'Create subfolders for playlists'
* MSG_290 · `M.ST_OVERWRITE` · 'Overwrite existing files'
* MSG_291 · `M.ST_CONN` · 'Advanced Connection & Downloads'
* MSG_292 · `M.ST_CONCURRENT` · 'Max Concurrent Downloads'
* MSG_293 · `M.ST_SPEED` · 'Max Network Bandwidth'
* MSG_294 · `M.ST_NOLIMIT` · 'No Limit'
* MSG_295 · `M.ST_FALLBACK` · 'Enable yt-dlp fallback (retry on errors)'
* MSG_296 · `M.ST_EMBED` · 'Embed metadata & artwork'
* MSG_297 · `M.ST_APPLY` · 'Apply and Save'
* MSG_298 · `M.ST_RESET` · 'Reset to Default'
* MSG_299 · `M.ST_INTERFACE` · 'Interface & Video Defaults'
* MSG_300 · `M.ST_FAV` · 'Favorite Categories'
* MSG_301 · `M.ST_FAV_ADD` · 'Add new category'
* MSG_302 · `M.ST_FAV_EDIT` · 'Edit category'
* MSG_303 · `M.ST_FAV_DEL` · 'Delete category'
* MSG_304 · `M.ST_FAV_NOTIFY` · "Don't notify me to add downloaded video to category"
* MSG_305 · `M.CAT_TITLE` · 'New category'
* MSG_306 · `M.CAT_EDIT_TITLE` · 'Edit category'
* MSG_309 · `M.CAT_DEL_ASK` · "Delete the category '{name}'?\nIts videos stay in the Library but leave the favorites."
* MSG_310 · `M.CAT_DEL_BTN` · 'Delete'
* MSG_312 · `M.CAT_NONE` · 'No categories yet'
* MSG_314 · `M.ST_DISCARDED` · 'Changes discarded.'
* MSG_315 · `M.ST_MBS` · '{n} MB/s'
* MSG_405 · `M.ST_PL_CONCURRENT` · 'Videos of one playlist at the same time'
* MSG_406 · `M.ST_PL_CONCURRENT_TIP` · 'How many videos of a single playlist are downloaded together (never more than the maximum concurrent downloads). Default 1 = one by one.'
* MSG_422 · `M.ST_AUTO_CLEAR` · 'Clear completed downloads automatically from the Downloads list'
* MSG_447 · `M.ST_SOUNDS` · 'Sound effects (clicks, tabs, completed tasks, warnings)'

</details>


## `app/ui/splash.py`  (273 lines)

Splash screen (design guide: tubearchive_pro_loading_screen.jpg).


### class `SplashScreen`  (line 23)

**Opened / created by:** `main.py` → `main()` line 112

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 42 | `self.timer` |  | - | timeout | `_animate` (52) | - |

**Functions:**

* `__init__()` line 27 - -  → calls: `make_app_icon`, `make_app_qicon`
* `set_progress()` line 48 - -
* `_animate()` line 52 - -
* `paintEvent()` line 58 - -  → calls: `self._paint_users`, `self._paint_rating_and_versions`
* `_value()` line 143 - The number the counter / bar show now: 1 -> total, fast at first, slower at the end.
* `_glass()` line 153 - -
* `_paint_users()` line 158 - Left side: the number of users, counting up.  → calls: `self._glass`, `self._value`
* `_star()` line 181 - -
* `_paint_rating_and_versions()` line 189 - Right side: rating of the users (stars + average) and the bar that fills version after version.  → calls: `self._glass`, `self._value`, `self._star`

**Texts used (id · constant · English):**

<details><summary>show 6 texts</summary>

* MSG_001 · `M.APP_NAME` · 'TubeArchive Pro'
* MSG_002 · `M.LOADING` · 'Loading'
* MSG_474 · `M.SPL_USERS` · 'Users'
* MSG_475 · `M.SPL_RATING` · "Users' rating"
* MSG_476 · `M.SPL_RATED_BY` · '{n} ratings'
* MSG_477 · `M.SPL_VERSION` · 'Version {v}'

</details>


## `app/ui/sync_flow.py`  (240 lines)

Sync flow (one object for the whole application, used by the New Download page, Library, Archive and
the Playlist Sync page).


### class `SyncController`  (line 34)

**Opened / created by:** `app/ui/main_window.py` → `__init__()` line 216

**Functions:**

* `__init__()` line 37 - -
* `_on_ready()` line 51 - -  → calls: `self._bg_result`, `self._busy.finish`
* `_on_failed()` line 60 - -  → calls: `self._bg_failed`, `self._busy.finish`
* `_thumb_ids()` line 69 - Pictures are read for the first new videos and a few old ones only (keeps the window quick).
* `run_all()` line 76 - 'Sync all' (Playlist Sync page): check every playlist that is switched on, one after the other. A playlist  → calls: `exec_blurred`, `page._log`, `ctx.history.find`
* `run()` line 101 - Check one playlist. Returns 'busy' / 'error' / 'cancelled' / 'none' (no new videos) / 'new'.  → calls: `page._log`, `self._fetcher.fetch`, `exec_blurred`, `self._old_rows`, `page._error`, `ctx.sync.synced_now`, `page.start_sync`
* `_old_rows()` line 149 - Every video the history knows: kind = 'have' (file is in the folder), 'missing' (downloaded, but the file is not  → calls: `self._path`
* `run_background()` line 164 - Check the playlists one after the other without any window: only the NEW videos are added to the downloads;  → calls: `page._log`, `self._bg_next`, `page._error`
* `_bg_next()` line 177 - -  → calls: `self._fetcher.fetch`, `self._bg_finish`
* `_bg_result()` line 188 - -  → calls: `self._old_rows`, `page.start_sync`, `page._log`, `ctx.sync.synced_now`
* `_bg_failed()` line 206 - -  → calls: `self.page._log`
* `_bg_finish()` line 210 - -  → calls: `exec_blurred`
* `_path()` line 220 - -
* `_play()` line 225 - -
* `_skip()` line 229 - 'Skip New': remember the new videos as skipped so they are not offered again.  → calls: `now_text`, `self.page._log`, `self.ctx.sync.synced_now`

**Texts used (id · constant · English):**

<details><summary>show 15 texts</summary>

* MSG_122 · `M.ERR_TITLE` · 'Download error'
* MSG_176 · `M.LG_BUSY` · 'A download is already running. Wait for it to finish or cancel it first.'
* MSG_207 · `M.SY_CHECKING` · 'Checking the playlist for new videos...'
* MSG_221 · `M.LG_SYNC_SKIP` · '{n} new video(s) skipped.'
* MSG_223 · `M.LG_SYNC_CHECK` · "Checking '{title}' for new videos..."
* MSG_247 · `M.LG_SYNC_FOUND` · "'{title}': {total} videos in the playlist, {done} already downloaded, {new} new."
* MSG_415 · `M.SYP_ALL` · 'Sync all'
* MSG_416 · `M.SYP_ALL_NONE` · 'There are no synchronized playlists that are switched on.'
* MSG_417 · `M.SYP_ALL_DONE` · 'Checked {n} playlists: {new} with new videos.'
* MSG_433 · `M.LG_DUE_BG` · 'Background sync of {n} playlist(s) started'
* MSG_434 · `M.LG_DUE_ADDED` · '{title}: {n} new video(s) added to Downloads'
* MSG_435 · `M.LG_DUE_NONE` · '{title}: nothing new'
* MSG_436 · `M.LG_DUE_FAIL` · '{title}: could not be checked ({detail})'
* MSG_437 · `M.DUE_MISSING_TITLE` · 'Files missing from the folder'
* MSG_438 · `M.DUE_MISSING_TEXT` · 'These videos were downloaded before, but their files are not in the folder any more:\n\n{list}'

</details>


## `app/ui/sync_page.py`  (252 lines)

'Playlist Sync' tab (design guide: Playlist Sync Manager).


### class `SyncPage`  (line 34)

**Opened / created by:** `app/ui/main_window.py` → `_build_center()` line 330

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 61 | `add` | QPushButton | “Add Playlist” | clicked | `self.add_requested.emit` | - |
| 66 | `sync_all` | QPushButton | “Sync all” | clicked | `self.sync_all_requested.emit` | - |
| 187 | `combo` | ArrowComboBox | - | currentIndexChanged | `_set_schedule` (216) | `self.ctx.sync.set_schedule` |
| 192 | `tg` | ToggleSwitch | - | toggled | `_set_enabled` (221) | - |
| 207 | `b` | QPushButton | - | clicked | `_sync` (230) | `self._message` |
| 207 | `b` | QPushButton | - | clicked | `_folder` (236) | `self._message` |
| 207 | `b` | QPushButton | - | clicked | `_stop` (243) | `exec_blurred` |

**Functions:**

* `__init__()` line 41 - -  → calls: `self._build`
* `_build()` line 49 - -  → calls: `mnemonic_safe`
* `mark_dirty()` line 100 - -
* `showEvent()` line 105 - -
* `refresh()` line 110 - -  → calls: `self._row`
* `_status()` line 125 - -  → calls: `SyncManager.is_due`
* `_row()` line 135 - -  → calls: `self.ctx.history.find`, `self._status`, `self.ctx.history.thumb_path`, `rounded_pixmap`, `make_thumb`, `self._set_schedule`, `self._set_enabled`
* `_set_schedule()` line 216 - -  → calls: `self.ctx.sync.set_schedule`
* `_set_enabled()` line 221 - -
* `_message()` line 227 - -  → calls: `exec_blurred`
* `_sync()` line 230 - -  → calls: `self._message`
* `_folder()` line 236 - -  → calls: `self._message`
* `_stop()` line 243 - -  → calls: `exec_blurred`

**Texts used (id · constant · English):**

<details><summary>show 27 texts</summary>

* MSG_091 · `M.ND_BEST` · 'Best Quality'
* MSG_109 · `M.BTN_CANCEL1` · 'Cancel'
* MSG_122 · `M.ERR_TITLE` · 'Download error'
* MSG_138 · `M.ERR_NO_FOLDER` · 'The save folder does not exist yet. It will be created when you start a download.'
* MSG_159 · `M.TIP_FOLDER` · 'Open folder'
* MSG_224 · `M.SYP_TITLE` · 'Synchronized Playlists ({n})'
* MSG_225 · `M.SYP_COL_NAME` · 'Playlist Name'
* MSG_227 · `M.SYP_COL_LAST` · 'Last Sync'
* MSG_228 · `M.SYP_COL_NEXT` · 'Next Sync'
* MSG_229 · `M.SYP_COL_FREQ` · 'Frequency'
* MSG_230 · `M.SYP_COL_ACT` · 'Actions'
* MSG_231 · `M.SYP_SYNCED` · 'Synchronized'
* MSG_232 · `M.SYP_IDLE` · 'Idle'
* MSG_233 · `M.SYP_PAUSED` · 'Paused'
* MSG_234 · `M.SYP_DUE` · 'Due'
* MSG_235 · `M.SYP_ADD` · 'Add Playlist'
* MSG_236 · `M.SYP_EMPTY` · 'No synchronized playlists yet.\nDownload a playlist in New Download and tick "Add this playlist to sync".'
* MSG_237 · `M.SYP_NEVER` · 'Never'
* MSG_238 · `M.TIP_SYNC` · 'Sync now'
* MSG_239 · `M.TIP_SYNC_DEL` · 'Stop syncing this playlist'
* MSG_240 · `M.SYP_DEL_TEXT` · 'Stop syncing this playlist?\nThe downloaded files stay on your disk.'
* MSG_241 · `M.SYP_ON` · 'ON'
* MSG_242 · `M.SYP_OFF` · 'OFF'
* MSG_243 · `M.SYP_STOP` · 'Stop Syncing'
* MSG_244 · `M.SYP_NOREC` · 'The downloaded playlist was removed from the Library, so it cannot be synchronized.'
* MSG_246 · `M.SYP_COL_FMT` · 'Format / Quality'
* MSG_415 · `M.SYP_ALL` · 'Sync all'

</details>


## `app/ui/theme.py`  (275 lines)

Colours and the global style sheet.

**Functions of the module:**

* `glow()` line 29 - -
* `_action_button()` line 37 - -
* `font_qss()` line 256 - The font sizes of the global style sheet multiplied by `scale`: a page / window that sets this style sheet
* `area_scale()` line 271 - Scale of an area compared with its design size (steps of 0.05).


## `app/ui/widgets.py`  (797 lines)

Reusable custom-painted widgets.

**Functions of the module:**

* `mnemonic_safe()` line 38 - Qt buttons treat a single '&' as a keyboard-shortcut mark and hide it ('Apply & Save' -> 'Apply  Save').
* `_font()` line 44 - -
* `draw_gauge_title()` line 215 - Draws the title of a gauge at the BOTTOM of `area`, close to the gauge; returns the height it uses.  → calls: `_font`


### class `FontScaler`  (line 52)

Mixin for the pages of the work area: the texts follow the size of the page (width AND height), so

**Functions:**

* `apply_font_scale()` line 58 - -  → calls: `area_scale`, `self.on_font_scale`, `font_qss`
* `on_font_scale()` line 66 - Pages override this to scale fixed sizes (pictures, buttons, margins).
* `resizeEvent()` line 69 - -  → calls: `self.apply_font_scale`


### class `WinButton`  (line 74)

Minimise / maximise / close button drawn by hand.

**Opened / created by:** `app/ui/main_window.py` → `__init__()` line 99; `app/ui/main_window.py` → `__init__()` line 104

**Functions:**

* `__init__()` line 78 - -
* `enterEvent()` line 85 - -
* `leaveEvent()` line 89 - -
* `sync_hover()` line 93 - After the window was resized the mouse may be elsewhere without a leave event: look at the real position.
* `mousePressEvent()` line 101 - -
* `mouseReleaseEvent()` line 106 - -
* `paintEvent()` line 110 - -  → calls: `make_globe_icon`


### class `NavButton`  (line 131)

**Opened / created by:** `app/ui/main_window.py` → `_build_sidebar()` line 283

**Functions:**

* `__init__()` line 134 - -
* `set_scale()` line 141 - -
* `set_active()` line 146 - -
* `set_text()` line 150 - -
* `enterEvent()` line 154 - -
* `leaveEvent()` line 158 - -
* `mouseReleaseEvent()` line 162 - -
* `paintEvent()` line 166 - -  → calls: `draw_nav_icon`, `_font`


### class `SpeedGauge`  (line 225)

Semi-circular speedometer (Network ingest). Everything is drawn relative to the

**Opened / created by:** `app/ui/main_window.py` → `_build_gauges()` line 372

**Functions:**

* `__init__()` line 229 - -
* `set_value()` line 236 - -
* `paintEvent()` line 240 - -  → calls: `draw_gauge_title`, `_font`


### class `RingGauge`  (line 280)

Circular gauge with animated side bars (Disk write / thread load). Size-relative.

**Functions:**

* `__init__()` line 283 - -
* `set_value()` line 290 - -
* `paintEvent()` line 295 - -  → calls: `_font`


### class `Sparkline`  (line 323)

**Functions:**

* `__init__()` line 324 - -
* `push()` line 329 - -
* `paintEvent()` line 333 - -


### class `DownloadItem`  (line 368)

One row in the downloader list.

**Opened / created by:** `app/ui/pages.py` → `__init__()` line 86; `app/ui/pages.py` → `__init__()` line 91

**Functions:**

* `__init__()` line 371 - -  → calls: `thumb.size`
* `_size()` line 412 - -
* `set_progress()` line 415 - -  → calls: `self._size`


### class `AdBanner`  (line 423)

Banner frame used for the owner banner (header) and the partner ads (footer).

**Opened / created by:** `app/ui/main_window.py` → `_build_header()` line 267

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 443 | `self.timer` |  | - | timeout | `_next` (482) | `self._cursor` |

**Functions:**

* `__init__()` line 430 - -  → calls: `self._next`
* `current_link()` line 449 - -
* `mouseReleaseEvent()` line 452 - -  → calls: `self.current_link`, `super().mouseReleaseEvent`
* `set_paths()` line 458 - New list of ads (after a refresh from the web): the show goes on in turns while the program runs.  → calls: `self._next`, `self._cursor`
* `_next()` line 482 - -  → calls: `self._cursor`
* `_cursor()` line 502 - -  → calls: `self.current_link`
* `paintEvent()` line 506 - -  → calls: `box.size`, `self.size`, `self._paint_brand`, `_font`
* `_paint_brand()` line 546 - -  → calls: `_font`


### class `ChannelBanner`  (line 565)

The owner's channel banner (side menu, bottom): the picture fills the width, a click opens the channel address.

**Opened / created by:** `app/ui/main_window.py` → `_build_sidebar()` line 289

**Functions:**

* `__init__()` line 568 - -
* `resizeEvent()` line 577 - -
* `paintEvent()` line 584 - -
* `mouseReleaseEvent()` line 599 - -  → calls: `super().mouseReleaseEvent`


### class `MiniGauge`  (line 605)

Small round measuring meter (270 degree arc with a scale of ticks and a needle).

**Opened / created by:** `app/ui/main_window.py` → `_build_gauges()` line 360; `app/ui/main_window.py` → `_build_gauges()` line 361; `app/ui/main_window.py` → `_build_gauges()` line 363; `app/ui/main_window.py` → `_build_gauges()` line 364; `app/ui/main_window.py` → `_build_gauges()` line 373

**Functions:**

* `__init__()` line 610 - -
* `set_state()` line 619 - -
* `set_title()` line 624 - -
* `paintEvent()` line 628 - -  → calls: `draw_gauge_title`, `_font`


### class `ToggleSwitch`  (line 676)

On / off switch (pill with a round knob), like the Settings design.

**Opened / created by:** `app/ui/settings_page.py` → `__init__()` line 104; `app/ui/settings_page.py` → `__init__()` line 105; `app/ui/settings_page.py` → `__init__()` line 180; `app/ui/settings_page.py` → `__init__()` line 181; `app/ui/sync_page.py` → `_row()` line 190

**Functions:**

* `__init__()` line 679 - -
* `paintEvent()` line 687 - -


### class `ElidedLabel`  (line 707)

Label that shortens long text with '...' instead of widening the layout.

**Opened / created by:** `app/ui/dialogs.py` → `__init__()` line 456; `app/ui/dialogs.py` → `__init__()` line 837; `app/ui/dialogs.py` → `__init__()` line 939; `app/ui/dialogs.py` → `_row()` line 1060; `app/ui/downloads_page.py` → `__init__()` line 112; `app/ui/downloads_page.py` → `__init__()` line 193

**Functions:**

* `__init__()` line 710 - -  → calls: `self.set_full_text`
* `set_full_text()` line 716 - -  → calls: `self._elide`
* `_elide()` line 721 - -
* `resizeEvent()` line 725 - -  → calls: `self._elide`


### class `ArrowComboBox`  (line 731)

Combo box that draws a clear drop-down arrow, so the user sees it can be clicked.

**Opened / created by:** `app/ui/dialogs.py` → `__init__()` line 647; `app/ui/dialogs.py` → `__init__()` line 863; `app/ui/library_page.py` → `_build()` line 368; `app/ui/library_page.py` → `_build()` line 371; `app/ui/new_download_page.py` → `_build()` line 152; `app/ui/new_download_page.py` → `_build()` line 157

**Functions:**

* `paintEvent()` line 734 - -


### class `MorphStack`  (line 753)

QStackedWidget whose page change is a soft fade-in of the real new page on the panel's own colour

**Opened / created by:** `app/ui/main_window.py` → `_build_center()` line 321

**Controls (what you press → what runs):**

| line | control | type | text shown | signal | handler (line) | then calls |
|---|---|---|---|---|---|---|
| 780 | `a` |  | - | valueChanged | `_tick` (784) | - |
| 781 | `a` |  | - | finished | `_finish` (790) | - |

**Functions:**

* `__init__()` line 758 - -
* `setCurrentIndex()` line 762 - -  → calls: `self._finish`
* `_tick()` line 784 - -
* `_finish()` line 790 - -


## `app/ads.py`  (1007 lines)

Update check + partner advertisements.

**Files used:** `ADS_DIR`, `BASELINE_FILE`, `CACHE_DIR`, `DATA_DIR`, `ads_allowed.json`, `ads_links.json`, `ads_meta.json`, `downloads_counter.json`, `downloads_counter.txt`, `drive_page_debug.html`, `total_users.txt`, `updates.log`

**Functions of the module:**

* `month_tag()` line 62 - -
* `parse_version()` line 67 - 'tubearchivepro_v1.0.13.exe' or the 4shared name 'tubearchivepro_v1_0_13' -> (1, 0, 13); else None.
* `version_text()` line 73 - -
* `is_share()` line 77 - -
* `_open()` line 82 - -
* `_page()` line 88 - -  → calls: `_open`
* `_size_after()` line 93 - File size written near a link on a folder page ('9,542 KB', '9.3 MB') -> bytes or None.
* `list_remote()` line 105 - Links of a folder page -> [{'name', 'url', 'size'}] (name = text of the link or the last part of its address).  → calls: `is_share`, `_size_after`
* `pick()` line 120 - The ad files of this month: names that start with 'tubearchivepro-YYYY-MM_'.
* `newest_version()` line 134 - Highest tubearchivepro_vX.Y.Z entry that is higher than `current` -> (version, entry) or (None, None).  → calls: `parse_version`
* `is_github()` line 147 - -
* `parse_github()` line 151 - https://github.com/<owner>/<repo>[/tree/<branch>/<folder>] -> {"owner", "repo", "ref", "path"}
* `_github_json()` line 164 - -  → calls: `_open`
* `list_github()` line 176 - The files of the repository folder -> the same entries as list_remote: {'name', 'text', 'url', 'size'}.  → calls: `parse_github`, `_github_json`
* `github_releases()` line 194 - All published releases of the repository (newest first).  → calls: `parse_github`, `_github_json`
* `release_version()` line 212 - -
* `asset_downloads()` line 217 - How many times the file `name` (any release) was downloaded: the sum of GitHub's download_count.
* `file_download_count()` line 224 - Online: how many times the release file `name` was downloaded (e.g. 'TubeArchivePro_2.1.0.zip').  → calls: `asset_downloads`, `github_releases`
* `github_stats()` line 229 - -> {"version": 'x.y.z' newest published (not pre-) release higher than `current` or "", "version_url",  → calls: `release_version`, `version_text`
* `is_drive()` line 254 - -
* `drive_folder_id()` line 259 - -
* `parse_drive_folder()` line 264 - Embedded folder view (or the normal folder page) -> [{'name', 'text', 'url', 'id', 'size'}].
* `_save_debug()` line 286 - The page that could not be understood is kept in data/ so that it can be looked at.
* `list_drive()` line 294 - Files of a shared Google Drive folder. Several pages are tried (the embedded list, the same with the  → calls: `drive_folder_id`, `parse_drive_folder`, `_save_debug`, `_page`
* `drive_urls()` line 326 - -
* `fetch_drive_bytes()` line 331 - -  → calls: `drive_urls`, `_open`
* `direct_url()` line 350 - A page address of GitHub / Google Drive -> the address that gives the file itself.  → calls: `is_drive`
* `parse_ad_list()` line 366 - The monthly list (TubeArchivePro-YYYY-MM.txt), one ad per line:  number  source  url  → calls: `line.find`
* `is_image()` line 391 - -
* `_num()` line 395 - -
* `parse_links()` line 400 - texts = {txt file name: content}, gifs = ad file names -> {gif file name: web address}.  → calls: `_num`
* `load_links()` line 436 - {full path of the gif: address} saved by the last check (works offline).
* `_gif_candidates()` line 446 - Addresses that may hold the file. A normal web folder: the link itself.  → calls: `is_share`, `_page`
* `_download_gif()` line 470 - Try the candidate addresses; keep the first valid GIF that is about the size listed on the folder page.  → calls: `_gif_candidates`, `_open`
* `_load_meta()` line 499 - -
* `_load_allowed()` line 506 - -
* `local_ads()` line 514 - The ads that may be shown: the gifs listed by the allowed-ads file of THIS month (older downloads and ads  → calls: `_load_allowed`
* `_txt_stem()` line 528 - -
* `parse_allowed()` line 534 - tubearchivepro-YYYY-MM.txt -> the file names of the ads that are allowed (paid) this month.  → calls: `_num`
* `list_entries()` line 564 - -  → calls: `is_github`, `list_github`, `is_drive`, `list_drive`, `list_remote`
* `read_text_file()` line 570 - The text of `filename` from the online folder (None when it is not there).  → calls: `list_entries`, `fetch_drive_bytes`, `_open`
* `parse_counter()` line 591 - downloads_counter.txt -> {"total": N, "rows": [(label, number)]}.
* `parse_user_totals()` line 616 - total_users.txt -> {(1, 0, 0): 25, ...}. Lines: '1.0.0 = 25' (also ':' or a space, 'v1.0.0', 'x,xxx').
* `build_user_stats()` line 629 - Users per version = the download_count of the .exe files of a release; a version that has no .exe release file  → calls: `release_version`, `version_text`
* `save_counter()` line 645 - -
* `load_counter()` line 654 - The counter to show: the last online value; else the value shipped with the setup; else None (hidden).  → calls: `parse_counter`
* `fetch_remote_text()` line 672 - Downloads `filename` from the online folder; the text is kept in the cache folder and used again  → calls: `read_text_file`
* `sync_ads()` line 695 - One check: newer program version? + download this month's ads (refresh changed ones, delete old ones).  → calls: `month_tag`, `_load_meta`, `is_share`, `is_drive`, `is_github`
* `_update_links()` line 931 - Read this month's .txt files and save {gif: address} next to the gifs.  → calls: `parse_links`, `fetch_drive_bytes`, `_open`
* `write_log()` line 958 - -


## `app/context.py`  (35 lines)

One object that holds everything loaded at start-up.


### class `AppContext`  (line 21)

**Opened / created by:** `main.py` → `main()` line 106

**Functions:**

* `__init__()` line 22 - -


## `app/demo.py`  (121 lines)

DEMO data for testing the Library, Archive and Playlist Sync pages.

**Functions of the module:**

* `_videos()` line 49 - -
* `purge_demo()` line 56 - Real-data mode (demo_mode false): the sample records of earlier versions are removed from the history, the
* `seed_demo()` line 74 - Create / complete the demo records. Returns True when something was written.  → calls: `_videos`, `st.download_dir`, `add_schedule`


## `app/dlqueue.py`  (512 lines)

Download queue.  NO Qt in this file (tested on its own); the Qt signals are in app/download_manager.py.


### class `Task`  (line 42)

One video = one yt-dlp process.

**Opened / created by:** `app/dlqueue.py` → `add_playlist()` line 182; `app/dlqueue.py` → `add_video()` line 158

**Functions:**

* `__init__()` line 45 - -
* `active()` line 74 - -
* `finished()` line 78 - -


### class `Group`  (line 82)

A playlist: its videos are Tasks.

**Opened / created by:** `app/dlqueue.py` → `add_playlist()` line 173

**Functions:**

* `__init__()` line 85 - -
* `counts()` line 102 - -
* `percent()` line 110 - -
* `current()` line 115 - The video that was started last (its picture / numbers are shown on the playlist frame).
* `speed()` line 121 - -
* `downloaded()` line 125 - -


### class `DownloadQueue`  (line 129)

**Opened / created by:** `app/download_manager.py` → `__init__()` line 39

**Functions:**

* `__init__()` line 130 - -
* `max_concurrent()` line 143 - -
* `bandwidth_mb()` line 149 - -
* `add_video()` line 156 - -  → calls: `self.pump`
* `add_playlist()` line 166 - entries = [{id, index, title, url, thumb_url}]  (index = position in the playlist).  → calls: `self.pump`, `safe_name`, `tpl_escape`, `video_url`, `index_text`
* `pump()` line 192 - -  → calls: `self._start_waiting`
* `_start_waiting()` line 207 - -  → calls: `self._start`, `self.max_concurrent`, `self._do_resume`, `self._allowed`
* `playlist_limit()` line 221 - Videos of ONE playlist that may download together (Settings, default 1; never above max_concurrent).  → calls: `self.max_concurrent`
* `_allowed()` line 229 - -  → calls: `self.playlist_limit`
* `_start()` line 235 - -  → calls: `self.bandwidth_mb`, `engine_options`, `self._progress`, `self._processing`, `self._finished`, `self._failed`, `self._cancelled`
* `_fetch_thumb()` line 255 - -  → calls: `download_bytes`
* `_progress()` line 262 - -
* `_processing()` line 272 - -
* `_finished()` line 277 - -  → calls: `self._after`
* `_failed()` line 286 - -  → calls: `self._after`
* `_cancelled()` line 292 - -  → calls: `self._after`
* `_after()` line 299 - -  → calls: `self._check_group`, `self.pump`
* `_check_group()` line 303 - -  → calls: `is_audio`
* `_stop_async()` line 326 - -
* `skip()` line 331 - 'Skip this one' (playlist details window): a waiting video is dropped, a running one is stopped.  → calls: `self._after`, `self._stop_async`
* `cancel_task()` line 348 - -  → calls: `self._after`, `self._stop_async`
* `discard_task()` line 361 - Cancel a video and remove it from the list as soon as it has stopped.  → calls: `self.cancel_task`
* `discard_group()` line 366 - -  → calls: `self.cancel_group`
* `discard_all()` line 372 - Cancel every unfinished video / playlist and remove them from the list when they have stopped.  → calls: `self.discard_group`, `self.discard_task`
* `purge_discarded()` line 381 - Removes the discarded videos / playlists that have stopped. Returns how many rows went away.
* `cancel_group()` line 390 - -  → calls: `self.cancel_task`
* `cancel_all()` line 395 - Everything stops (Cancel all / exit). wait=True returns when the partial files are deleted.  → calls: `self._after`, `job.cancel`
* `pause_task()` line 419 - -  → calls: `t.job.pause`, `self.pump`
* `_do_resume()` line 429 - -  → calls: `t.job.resume`
* `resume_task()` line 436 - Resume a paused video. A paused video holds no place, so a video added meanwhile may have taken them all; then  → calls: `self._do_resume`, `self.max_concurrent`
* `pause_all()` line 449 - Pause every running video; the waiting ones stay waiting (a video added later still starts: paused ones hold no place).  → calls: `self.pause_task`
* `resume_all()` line 453 - -  → calls: `self.resume_task`
* `set_sequential()` line 456 - -  → calls: `self.pump`
* `clear_finished()` line 461 - Removes the finished videos / playlists from the list. Returns how many rows went away.
* `counts()` line 471 - (videos running, videos waiting)
* `counts_by_state()` line 477 - Files (every video of a playlist is one file): downloading now / paused / waiting in the queue.
* `speed()` line 484 - bytes / second of all running videos
* `downloaded_bytes()` line 488 - Everything downloaded since the program started (finished videos + what is on its way).
* `busy()` line 492 - -
* `active_percents()` line 495 - One number per unfinished link / playlist (the exit window).
* `top_items()` line 501 - Rows of the Downloads page in the order they were added: single videos and playlists.


## `app/download_manager.py`  (118 lines)

Qt side of the download engine: runs the work in background threads and reports to the
interface with signals. All the real logic is in app/downloader.py and app/dlqueue.py.


### class `DownloadManager`  (line 23)

**Opened / created by:** `app/ui/downloads_page.py` → `__init__()` line 396; `app/ui/new_download_page.py` → `__init__()` line 98

**Functions:**

* `__init__()` line 34 - -
* `_event()` line 42 - -
* `sync_tools()` line 66 - -
* `invalidate()` line 71 - Ignore the result of any running info request.
* `fetch()` line 75 - -
* `_fetch_worker()` line 79 - -  → calls: `fetch_info`, `log_fetch`


### class `InfoFetcher`  (line 91)

Reads a playlist in the background (for 'Sync now'), independent of the New Download page.

**Opened / created by:** `app/ui/sync_flow.py` → `__init__()` line 46

**Functions:**

* `__init__()` line 97 - -
* `fetch()` line 101 - -
* `_work()` line 104 - -  → calls: `fetch_info`, `download_bytes`


## `app/downloader.py`  (903 lines)

Download engine logic.  NO Qt in this file, so it can be tested on its own.

**Files used:** `DATA_DIR`, `description.txt`, `fetch.log`, `files.txt`

**Functions of the module:**

* `_exe_list()` line 72 - -
* `is_audio()` line 76 - -
* `looks_like_url()` line 80 - -
* `is_playlist_url()` line 84 - Only a real playlist page (/playlist?list=...) is treated as a playlist.
* `playlist_id()` line 94 - The list=... value of a playlist link ('' when there is none).
* `pad_width()` line 102 - Digits of the playlist index: 2 for fewer than 10 videos (01), 3 for 10-99 (001), 4 for 100-999 ...
* `index_text()` line 107 - '01', '002', '0015' ... the position of a video in its playlist.  → calls: `pad_width`
* `safe_name()` line 115 - A folder name that Windows accepts.
* `tpl_escape()` line 121 - Literal text inside a yt-dlp output template (a % must be doubled).
* `video_url()` line 126 - Address of a playlist entry: its own url, else the YouTube watch page of its id.
* `fmt_size()` line 135 - -
* `fmt_time()` line 146 - -
* `_num()` line 153 - -
* `max_height()` line 163 - -
* `quality_options()` line 169 - Values for the quality drop-down. Video: 0 = best, then heights (ascending).
* `parse_quality()` line 181 - A saved quality as a number: 720, "720", "1080p", "4K", "Best" (or anything unknown) -> 0 = best.
* `height_label()` line 195 - -
* `quality_label()` line 199 - Language-neutral label. Returns None for 'Best' (the interface translates that one).  → calls: `height_label`
* `effective_height()` line 209 - -  → calls: `max_height`
* `build_format_args()` line 216 - -
* `build_download_cmd()` line 236 - -  → calls: `build_format_args`, `_exe_list`
* `engine_options()` line 267 - yt-dlp options that come from Settings. `get(key, default)` reads a setting.
* `estimate_size()` line 295 - Estimated size in bytes for the chosen format/quality (None if unknown).  → calls: `size`, `has`
* `available_heights()` line 345 - The resolutions that the video really offers (ascending), e.g. [144, 360, 720, 1080].
* `_rate_bytes()` line 352 - Estimated bytes per second of the media for a format / quality (used when no real size is known).
* `estimate_playlist_size()` line 364 - Estimated total bytes of a whole playlist from the durations of its videos (None when no duration is known).  → calls: `_rate_bytes`
* `size_table()` line 370 - {(format, quality value): estimated bytes} for every container x every quality of one video; kept in memory by  → calls: `available_heights`, `quality_options`, `estimate_size`, `is_audio`
* `free_bytes()` line 386 - Free bytes of the partition that holds `path` (the folder may not exist yet). None when it cannot be read.
* `space_needed()` line 397 - Bytes that must be free for a download of `est` bytes: the file twice (parts + merged file) + `extra`.
* `drive_name()` line 402 - 'C:' for a Windows path, otherwise the mount point of the partition.
* `format_sizes()` line 412 - Sizes in bytes (None = unknown) of the streams that yt-dlp announced ('Downloading 2 format(s): 137+140').
* `parse_progress_line()` line 431 - -  → calls: `_num`
* `map_error()` line 463 - Translate a raw yt-dlp error text into (code, short detail).
* `download_bytes()` line 477 - -
* `_thumb_url()` line 486 - -
* `log_fetch()` line 502 - Diagnostics of 'Check': every attempt and its result go to data/fetch.log (2.0.9). Never raises.
* `fetch_info()` line 514 - -  → calls: `is_playlist_url`, `log_fetch`, `_thumb_url`, `_exe_list`, `map_error`


### class `EngineError`  (line 63)

**Opened / created by:** `app/downloader.py` → `fetch_info()` line 524; `app/downloader.py` → `fetch_info()` line 527; `app/downloader.py` → `fetch_info()` line 530; `app/downloader.py` → `fetch_info()` line 537; `app/downloader.py` → `fetch_info()` line 541

**Functions:**

* `__init__()` line 64 - -


### class `DownloadJob`  (line 575)

Callbacks (all optional, called from a background thread except on_cancelled):

**Opened / created by:** `app/dlqueue.py` → `_start()` line 241

**Functions:**

* `__init__()` line 585 - -  → calls: `is_playlist_url`
* `_log()` line 618 - -
* `alive()` line 622 - -
* `start()` line 626 - -  → calls: `build_download_cmd`, `self._cleanup_tmp`
* `_reader()` line 650 - -  → calls: `self._finish`, `self._handle`
* `_handle()` line 665 - -  → calls: `parse_progress_line`, `self._progress`, `map_error`, `format_sizes`, `self._log`
* `_progress()` line 693 - -  → calls: `self._refined_total`
* `_refined_total()` line 742 - Expected size of the whole file from what is known NOW: finished streams count with their real size,
* `_collect_files()` line 762 - -
* `_read_description()` line 782 - -
* `_finish()` line 790 - -  → calls: `self._collect_files`, `self._cleanup_tmp`, `self._read_description`, `is_audio`, `quality_label`, `effective_height`, `height_label`
* `_tree()` line 818 - -
* `pause()` line 822 - Suspend yt-dlp (and ffmpeg). The download is NOT terminated.  → calls: `self.alive`, `self._tree`
* `resume()` line 839 - -  → calls: `self.alive`, `self._tree`, `pr.resume`
* `_kill_tree()` line 856 - -
* `_cleanup_tmp()` line 878 - -
* `cancel()` line 887 - Stop the download, kill the utility and delete every partial file.  → calls: `self.alive`, `self._cleanup_tmp`, `self._kill_tree`


## `app/favorites.py`  (111 lines)

Favorites: categories (user defined) and which history record sits in which category.

**Files used:** `FAVORITES_FILE`


### class `FavoritesManager`  (line 17)

**Opened / created by:** `app/context.py` → `__init__()` line 28

**Functions:**

* `__init__()` line 18 - -
* `load()` line 23 - -
* `save()` line 36 - -
* `ensure_category()` line 41 - -
* `add()` line 49 - -  → calls: `self.ensure_category`
* `remove()` line 55 - -
* `is_favorite()` line 60 - -
* `category_of()` line 63 - -
* `icon_of()` line 66 - -
* `label()` line 69 - '🎬 Cinema' (icon + name) for lists and card tags.  → calls: `self.icon_of`
* `add_category()` line 74 - New category with an icon. None = the name is empty or already used.
* `edit_category()` line 85 - Rename (and re-icon) a category; its videos follow. False = empty name or the name is used by another one.
* `delete_category()` line 100 - The category goes away; its videos leave the favorites (they stay in the Library).
* `used_categories()` line 108 - Categories that contain at least one video (for the filter of the Downloads page).


## `app/feedback.py`  (170 lines)

Ratings typed in the exit window.

**Files used:** `FEEDBACK_FILE`, `install_id.txt`, `my_rating.json`

**Functions of the module:**

* `form_response_url()` line 31 - .../viewform?usp=... -> .../formResponse (the address that accepts the answers).
* `post_form()` line 39 - Sends one answer to a Google form. fields = {"rating": "entry.1", ...}, values = {"rating": 4, ...}.  → calls: `form_response_url`
* `post_json()` line 54 - Sends one rating to the Apps Script web app (the answer is {"status": "success"}).
* `os_text()` line 68 - -


### class `FeedbackManager`  (line 75)

**Opened / created by:** `app/context.py` → `__init__()` line 27

**Functions:**

* `__init__()` line 76 - -
* `install_id()` line 80 - A random anonymous id of this installation (so a changed rating replaces the old row, not a second one).
* `add()` line 98 - -
* `current()` line 111 - The rating given before {"rating", "comment", ...} or None.
* `save_rating()` line 119 - Keeps the rating. True = it is new or changed (or the last one was never sent): it has to be sent.  → calls: `self.current`
* `mark_sent()` line 140 - -  → calls: `self.current`
* `send_endpoint()` line 149 - Sends the last rating to the Apps Script web app; marks it as sent when it was accepted.  → calls: `self.current`, `post_json`, `self.mark_sent`, `self.install_id`, `os_text`
* `send()` line 161 - Sends the last rating to the Google form; marks it as sent when the form accepted it.  → calls: `self.current`, `post_form`, `self.mark_sent`


## `app/history.py`  (228 lines)

Download history (old downloads), newest first.

**Files used:** `HISTORY_FILE`, `THUMBS_DIR`

**Functions of the module:**

* `video_key()` line 35 - A key that is the same for every form of a video link (watch?v=, youtu.be/, shorts/, embed/); other sites: the link.
* `delete_files()` line 193 - Deletes the physical files of a history record (2.0.2: Delete button -> "delete the file(s) too").


### class `HistoryManager`  (line 57)

**Opened / created by:** `app/context.py` → `__init__()` line 25

**Functions:**

* `__init__()` line 58 - -
* `load()` line 61 - -
* `add()` line 78 - -
* `save()` line 83 - -
* `new_record()` line 89 - Build a record for a finished download, save its thumbnail and add it to the history.  → calls: `playlist_id`
* `sorted_records()` line 116 - Newest first (date text 'YYYY-MM-DD HH:MM' sorts correctly; stable for equal dates).
* `find_playlist()` line 120 - The history record of a playlist that was downloaded before (same list= id), newest first.  → calls: `self.sorted_records`, `is_playlist_url`, `playlist_id`
* `file_key()` line 131 - One key per file on disk (folder + file name); '' for a playlist (it has no single file).
* `same_file()` line 137 - The OTHER records that point to the same file as `rec` (the history keeps one entry per file).  → calls: `self.file_key`
* `dedupe_files()` line 142 - Keep only the newest record of every file. Returns {removed id: kept id} (favorites follow it). 2.0.7  → calls: `self.file_key`
* `find_video()` line 159 - The newest record of a single video downloaded before (same video id / same link), or None (2.0.5).  → calls: `video_key`, `self.sorted_records`
* `find()` line 169 - -
* `remove()` line 172 - -  → calls: `self.find`
* `thumb_path()` line 185 - -


## `app/i18n.py`  (81 lines)

Language manager: every language is one JSON file in data/languages/.

**Files used:** `LANG_DIR`


### class `LanguageManager`  (line 28)

**Opened / created by:** `app/context.py` → `__init__()` line 24

**Functions:**

* `__init__()` line 29 - -
* `discover()` line 37 - Find every <code>.json in data/languages (new languages appear automatically).
* `load()` line 53 - -
* `is_rtl()` line 71 - -
* `tr()` line 74 - -


## `app/infodoc.py`  (334 lines)

Info pages.  NO Qt in this file (tested on its own).

**Files used:** `APP_VERSION`, `INFO_DIR`, `.en.txt`

**Functions of the module:**

* `inline()` line 41 - Escapes the text and turns links, e-mail addresses and **bold** into HTML.  → calls: `_bold`
* `_bold()` line 60 - -
* `_card()` line 64 - -
* `parse_blocks()` line 69 - [(kind, payload)] kinds: title, h2, h3, p, ul, ol, note, rule, rows, facts.  → calls: `flush`, `push`
* `render_blocks()` line 114 - -  → calls: `inline`, `_card`
* `description_html()` line 166 - Plain video description -> HTML where every web address and e-mail address is a link and the line breaks stay
* `scale_html()` line 187 - Multiplies every font-size of the page by `scale` (the info page follows the size of the work area).
* `page_html()` line 194 - -
* `render_text()` line 199 - -  → calls: `page_html`, `render_blocks`, `parse_blocks`
* `info_path()` line 209 - assets/info/<name>.<lang>.txt, else <name>.en.txt, else <name>.txt (None when nothing exists).
* `load_info()` line 219 - -  → calls: `info_path`
* `_rating_of()` line 232 - -
* `_split_row()` line 241 - -
* `parse_reviews()` line 251 - -> [{"name", "rating" (0 when unknown), "comment", "date"}], newest first when dates are sortable.  → calls: `_rating_of`, `_split_row`
* `stars_html()` line 308 - -
* `render_reviews()` line 314 - HTML of the reviews page: title, average, one card per review.  → calls: `page_html`, `render_blocks`, `_card`, `stars_html`, `inline`


## `app/loader.py`  (104 lines)

Start-up loader: runs while the splash screen is visible.

**Files used:** `APP_VERSION`


### class `StartupLoader`  (line 29)

**Opened / created by:** `main.py` → `main()` line 161

**Functions:**

* `__init__()` line 34 - -
* `_load_language()` line 39 - -  → calls: `self.ctx.lang.discover`
* `_load_history()` line 43 - -  → calls: `self.ctx.history.dedupe_files`, `self.ctx.favorites.category_of`, `seed_demo`, `purge_demo`, `self.ctx.favorites.is_favorite`
* `_online_work()` line 59 - -  → calls: `sync_ads`, `write_log`, `fetch_rating`, `local_ads`, `parse_version`
* `_online_check()` line 79 - The check runs in its own thread; the splash screen waits for it at most ONLINE_WAIT seconds.
* `run()` line 85 - -

**Texts used (id · constant · English):**

<details><summary>show 7 texts</summary>

* MSG_003 · `M.LOAD_DEFAULTS` · 'Loading default settings'
* MSG_004 · `M.LOAD_SETTINGS` · 'Loading user settings'
* MSG_005 · `M.LOAD_LANG` · 'Loading language files'
* MSG_006 · `M.LOAD_RES` · 'Loading resources'
* MSG_007 · `M.LOAD_HISTORY` · 'Loading download history'
* MSG_008 · `M.READY` · 'Ready'
* MSG_379 · `M.LOAD_ONLINE` · 'Checking for updates and ads'

</details>


## `app/paths.py`  (122 lines)

Central place for every path the application uses.

**Files used:** `current_settings.json`, `data/config/current_settings.json`, `default_settings.json`, `downloads_baseline.txt`, `favorites.json`, `feedback.json`, `history.json`, `portable.txt`, `sync.json`

**Functions of the module:**

* `resolve_user_dir()` line 59 - Where the program writes its data (pure function, tested).
* `_app_dir()` line 67 - -
* `migrate_old_data()` line 104 - Setup of an older portable version: its settings / history / favorites / sync / feedback / ads that sit next to the


## `app/resources.py`  (68 lines)

Resource files: partner ad GIFs, owner banner, and the yt-dlp / ffmpeg executables.

**Files used:** `ADS_DIR`, `CONFIG_DIR`, `HISTORY_DIR`, `LANG_DIR`, `OWNER_DIR`, `TOOLS_DIR`

**Functions of the module:**

* `find_tool()` line 20 - Path of `name`(.exe) inside tools/ - directly, or in any sub-folder (e.g. tools/ffmpeg-...-full_build/bin).


### class `ResourceManager`  (line 35)

**Opened / created by:** `app/context.py` → `__init__()` line 26

**Functions:**

* `__init__()` line 36 - -
* `load()` line 44 - -  → calls: `local_ads`, `find_tool`


## `app/settings.py`  (97 lines)

Default settings + current (user) settings, both stored as JSON files.

**Files used:** `CONFIG_DIR`, `CURRENT_SETTINGS_FILE`, `DEFAULT_SETTINGS_FILE`


### class `SettingsManager`  (line 24)

**Opened / created by:** `app/context.py` → `__init__()` line 23

**Functions:**

* `__init__()` line 25 - -
* `load_defaults()` line 31 - -
* `load_current()` line 44 - User settings override defaults; the file is created on first run.
* `get()` line 62 - -
* `subscribe()` line 65 - fn(key) is called when a setting is changed by any part of the program (a 'don't show again' tick in a
* `_notify()` line 70 - -
* `set()` line 77 - -  → calls: `self._notify`
* `save()` line 83 - -
* `reset_to_defaults()` line 89 - 'Restore Defaults': current_settings.json becomes a copy of default_settings.json.  → calls: `self._notify`
* `download_dir()` line 96 - -


## `app/sounds.py`  (60 lines)

Short sound effects. `play("click" | "tab" | "done" | "warning")` never raises and never blocks.

**Files used:** `APP_DIR`

**Functions of the module:**

* `attach()` line 22 - The settings manager decides whether sounds are on (`sounds_enabled`, default on).
* `enabled()` line 28 - -
* `play()` line 35 - Start the sound `name`; True when it was started.  → calls: `fx.play`, `enabled`


## `app/stats.py`  (80 lines)

Numbers for the splash screen. The splash appears before any network call, so it shows the numbers of the LAST online
check (cache) - or the shipped baseline the first time - and the background check refreshes them for the next start.

**Files used:** `APP_DIR`, `CACHE_DIR`, `rating_stats.json`, `splash_baseline.json`

**Functions of the module:**

* `_versions_key()` line 23 - -
* `users_data()` line 27 - {"total": N, "versions": [("1.0.0", 25), ...]} of the last check; the shipped baseline the first time.  → calls: `load_counter`, `_versions_key`
* `fetch_rating()` line 45 - GET <endpoint>?action=stats -> {"average", "count"}; saved for the next start. None when it did not work.
* `load_rating()` line 68 - -
* `splash_data()` line 76 - Everything the splash screen shows: {"total", "versions", "rating"}.  → calls: `users_data`, `load_rating`


## `app/sync.py`  (101 lines)

Playlist sync schedule.   data/sync/sync.json

**Files used:** `SYNC_FILE`

**Functions of the module:**

* `now_text()` line 25 - -
* `add_schedule()` line 29 - start + 1 day / + 7 days / + 1 month (the day is cut to the end of a shorter month).


### class `SyncManager`  (line 41)

**Opened / created by:** `app/context.py` → `__init__()` line 29

**Functions:**

* `__init__()` line 42 - -
* `load()` line 45 - -
* `save()` line 53 - -
* `find()` line 57 - -
* `set_next()` line 60 - -  → calls: `add_schedule`
* `add()` line 63 - Add (or update) a playlist; the first sync is due one period after now.  → calls: `self.find`, `self.set_next`, `now_text`
* `synced_now()` line 75 - A sync finished (or was skipped): remember it and schedule the next one.  → calls: `self.find`, `now_text`, `self.set_next`
* `set_schedule()` line 83 - -  → calls: `self.set_next`
* `remove()` line 92 - -
* `is_due()` line 97 - -


## `app/sysmon.py`  (77 lines)

Numbers for the gauges panel. Qt-free; `psutil` can be replaced in tests.

**Functions of the module:**

* `auto_max()` line 21 - -
* `existing_parent()` line 25 - -
* `human_size()` line 72 - (number text, 'GB' or 'MB' key) for the gauges: MB below 1 GB.


### class `SysMonitor`  (line 32)

**Opened / created by:** `app/ui/main_window.py` → `__init__()` line 158

**Functions:**

* `__init__()` line 33 - -
* `_counters()` line 37 - -
* `sample()` line 48 - {'net': MB/s received by the computer, 'disk': MB/s read + written,  → calls: `self._counters`, `existing_parent`


## `main.py`  (171 lines)

TubeArchive Pro - entry point.

**Files used:** `FROZEN`, `error.log`

**Functions of the module:**

* `_install_error_log()` line 33 - Every uncaught error is written to data/error.log (and printed), so a problem can be reported.
* `_install_qt_log()` line 51 - The Qt warning 'QFont::setPointSize: Point size <= 0 (-1)' is harmless (a widget styled in pixels has no point
* `show_error()` line 81 - Error window with readable text (the program style paints labels white) + a copy in data/error.log.
* `main()` line 95 - -  → calls: `_install_error_log`, `_install_qt_log`, `migrate_old_data`, `splash_data`, `show_error`
