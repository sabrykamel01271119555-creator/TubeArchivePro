# TubeArchive Pro 2.0.2 - progress record (read first when a session is continued)
Tests: `python3 -W error::ResourceWarning -m unittest discover -s tests` (pause tests use fixed sleeps; one flaky failure seen under load).
No Qt in the sandbox: UI cannot be seen; logic tested with tests/qt_stub.py. A copy of the 1.0.14 zip was uploaded by the user and unzipped at /home/claude/old1014 (may be gone in a new session).
User feedback on 2.0.1 + new notes = this version 2.0.2. Point 17 (update check + downloads counter) is DELAYED to the next prompt (leave code as is).

## Items (user numbering)
[x] 1  Glass style withdrawn -> 1.0.14 look restored (theme.py, Shell, NavButton, ToggleSwitch colours)
[x] 2  Gauges (MiniGauge scale+needle+end numbers, call sites updated; not visually verified)
[old] 2  Gauges: Downloaded = session bytes vs free-at-start, Free = free vs partition total; ALL gauges show a small measuring scale (ticks + min/max numbers)
[x] 6  Details dialog: folder value clickable (opens folder), url clickable (opens browser)
[~] 9  Ads (ads.py list_drive tries 4 pages + data/drive_page_debug.html; missing month txt = show all month ads; CANNOT test Drive from sandbox): gifs/txt not downloaded, frame empty -> fix (online check, Drive parsing, fallback to local)
[x] 11 (theme.font_qss/area_scale, widgets.FontScaler on Downloads/Sync/Info pages, GlassDialog fits window, Settings+Library use width AND height; tests/test_scale.py; real look NOT verifiable) Work-area scaling for ALL pages/windows (playlist details, settings, ...)
[x] 12 (downloader._refined_total + format_sizes, tested) Real estimated size updated while downloading (not the first estimate)
[x] 15 Apply & Save = apply now (language etc.) + save to current_settings.json
[x] 16 Ad frame (header AdBanner fit; footer ad + owner banner removed): back to 1.0.14 behaviour (fit gif to frame); "Advertisement space" frame REPLACES the top banner (remove banner; work area stretches)
[x] 18 Donate (icons assets/info/icons/*.png drawn by me - replace with official logos if wanted; about/contact/donate texts rewritten en+ar): instapay + vodafone cash icons; Contact: remove whatsapp number (link only) + facebook https://www.facebook.com/sabry.kamel.12 ; About: richer description, no ugly frames around version/date/developer, YouTube link https://www.youtube.com/@LetsHaveFun-ActiveMind
[x] 20 (done: Check button, 4 buttons acting on queue, available heights, sizes dict, space check + playlist total; Downloads page keeps rows until Clear completed - already) New Download: URL box free right after Add; 4 buttons (Start download, Pause, Cancel, Open folder) like 1.0.14 with their function; small "analyze" button beside URL: fills container list with available formats only, keeps estimated sizes, checks free space on target partition (needs ~2x size), warns + suggests lower quality / other partition; same for playlists (total est.); Downloads page keeps ALL files of this run after completion (cleared only by "Clear completed"); new run starts empty
[x] 21 Settings <-> current config file sync; "don't ask again" checkboxes in dialogs <-> Settings checkboxes
[x] 22 Playlist concurrent downloads: default 1, shown in Settings, applied on Apply & Save
[x] 23 Header (icon, name 26px, version 11px, ad space): app icon, name (smaller), version below (smaller), advertisement space for the rest
[x] 24 (feedback.py my_rating.json + post_form; form url/fields empty until user gives them; tests/test_feedback.py) Exit window: buttons "Skip & Exit" / "Submit & Exit"; rating saved in a local file and shown next time; changed rating submitted to the Google form
[x] 25 (history.delete_files + library_page.delete_record; tested) Delete video: ask also delete physical file
[x] 26 (same; playlist record has 'subfolder' flag; also removes it from sync list) Delete playlist: ask also delete physical files + playlist subfolder
[x] docs: CHANGELOG 2.0.2, README, APP_VERSION 2.0.2, tests (104 pass; rare flaky failure not reproducible), zip delivered

## Done notes (update 1)
- 2: MiniGauge scale+needle+end numbers; SpeedGauge 0/max labels (main_window._size_text). Visual check pending.
- 9: ads.list_drive tries 4 pages + data/drive_page_debug.html; missing month txt => all ads of the month shown. Cannot reach Drive from sandbox: user must test; send data/updates.log
- 16/23: header = icon+name(26px)+version(11px)+AdBanner(fit) ; owner banner & footer ad removed (main_window._build_header)
- 6: DetailsDialog folder/url are links. 18: infodoc icon rows + about/contact/donate texts + assets/info/icons/*.png (generic badges, not official logos)

## Open / next prompt
- Item 17 (update check + downloads counter redesign) postponed by the user.
- Need from user: Google form link + entry ids (fill settings feedback_form_url / feedback_form_fields); official InstaPay / Vodafone Cash logos; screenshots to check the real look.
- Ads: if empty, read data/updates.log and data/drive_page_debug.html.
