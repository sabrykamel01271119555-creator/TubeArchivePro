# TubeArchive Pro 2.0.3 - progress record (read first when continued)
Base = 2.0.2 (see PROGRESS_2.0.2.md). Tests: `python3 -W error::ResourceWarning -m unittest discover -s tests` (104 pass; very rare flaky failure not reproducible).
Checks: AST undefined-name script (scratchpad/undef.py), message-id parity en/ar (all MSG ids used + same placeholders).
No Qt in sandbox -> UI is never seen; keep changes simple and defensive.

## User list (2.0.3)
[x] 1 Main window starts on New Download page
[x] 2 Gauge titles: one font for all gauges, drawn UNDER each gauge close to it
[x] 3 Free-space gauge: arc = used / partition total (no red), number = free space
[x] 4 Page change animation: no white splash from the middle; use colours of the app + new mechanism
[x] 5 Settings page must fit ANY work-area size (maximized too): scale components so everything shows
[x] 6 Library favorites drop-down shows category icons (not stars)
[x] 7 Playlist Sync page: smaller fonts so last sync / next sync etc. are fully readable
[x] 8 Video description: links are hyperlinks
[x] docs: version 2.0.3 (paths.py), headers, CHANGELOG, README, tests, zip, closing message

All 8 items coded (UI not visually verified). Version 2.0.3. Zip delivered after tests.
