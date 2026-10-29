# TubeArchive Pro 2.0.1 - progress record (read this first when a session is continued)

Last updated: 2026-10-20. Tests: `python3 -W error::ResourceWarning -m unittest discover -s tests` (90 pass at audit time).
Checks used instead of pyflakes: AST undefined-name script (scratchpad/undef.py, 0 problems), message-id parity en/ar (379 ids, OK).

## State found at the start of this session
An earlier (interrupted) run had ALREADY implemented most of 2.0.1 in the files (headers say 2.0.1):
dlqueue.py (queue), downloads_page.py, infodoc.py + info_page.py + assets/info/*.txt, glass theme, library/archive split,
settings page scaling, sync toggle, ad fit, counter (ads.py parse_counter/load_counter + data/downloads_baseline.txt), loader runs online check on splash.

## The 18 points - status (update as verified)
1 glass style ........ theme.py + Shell gradient (main_window)       : code present, NOT visually verified (no Qt in sandbox)
2 gauge Downloaded ... session bytes vs free space at start          : verified in code
3 gauge Free space ... free / partition total                        : verified in code
4 Archive vs Library . Archive = 3 vaults, above Library in menu     : code present
5 Help file .......... assets/info/help.en/ar.txt shown in work area : present (to be rewritten together later)
6 Description ........ saved from yt-dlp, shown in Details dialog    : present
7 Queue / concurrency  dlqueue.py, default max_concurrent 3, queue gauge : present, tests in test_queue.py
8 Bandwidth limit .... speed_limit_mb split between running tasks    : verified in code
9 Allowed ads ....... only gifs listed in tubearchivepro-YYYY-MM.txt, check on splash : present
10 Playlist UI ....... group row + details window with skip          : present
11 Settings sizes .... page follows work-area size                   : present
12 Size ratio ........ "done / total"                                : verified in code
13 Index 01/001 ...... downloader.index_text                         : present
14 Sync ON toggle .... sync_page                                     : present
15 "Apply & Save" .... settings_page / messages                      : verified in code
16 Ad fit ............ AdBanner(fit=True)                            : present
17 Downloads counter . DECISION: option 3 (downloads_counter.txt on Drive) + local cache + baseline file shipped in setup
18 Corner + 5 links .. channel logo circle, Reviews(online reviews.txt)/Help/About/Contact/Donate : present

## Still to do (in order)
- [x] verified items 2,3,8,12,15 in code
- [x] CHANGELOG.md 2.0.1 entry, README.md update
- [x] rebuild zip /home/claude/TubeArchivePro.zip (no history/favorites/sync/feedback data files inside) and send it
- [ ] closing message to the user (list untested items: Qt rendering, real Drive, real yt-dlp)

## Next (after user feedback)
- Review screenshots of the glass UI, Downloads page, Archive vaults, Settings; fix layout issues.
- Rewrite help/about/contact/donate texts together (assets/info/*.en.txt / *.ar.txt).
- Check data/updates.log if ads / counter / reviews do not appear (Drive folder must be shared with anyone-with-link; files named exactly reviews.txt, downloads_counter.txt, tubearchivepro-YYYY-MM.txt).
