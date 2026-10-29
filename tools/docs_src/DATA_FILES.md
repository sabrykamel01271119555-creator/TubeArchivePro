# Data files

## Written by the program (user data folder = `%APPDATA%\TubeArchivePro`; the program folder when portable / not installed)
| File | Content |
|---|---|
| `data/config/current_settings.json` | The user's settings (override `default_settings.json`) |
| `data/history/history.json`, `data/history/thumbs/` | Records of every download (+ videos of playlists), small pictures (`pl_<video id>.img` = pictures of videos shown inside an opened playlist) |
| `data/failed/failed.json` | Videos that could not be downloaded and were kept with **Later** (reminded at the next start) |
| `data/favorites/favorites.json` | Categories (with icons) and the videos in them |
| `data/sync/sync.json` | Playlist sync entries: schedule, enabled, last / next sync |
| `data/feedback/feedback.json`, `my_rating.json`, `install.json` | Rating history, last rating, install id + installation date |
| `data/cache/*` | Last online numbers: counter, `users_base.json`, `users_stats.json`, `rating_stats.json`, `reviews_cache.json`, ad fingerprints |
| `assets/ads/` | Downloaded ad pictures of the current month |
| `tools/` | yt-dlp / ffmpeg downloaded by the update window (searched before the program's `tools/`) + `tools.json` |
| `data/*.log` | Logs (fetch / online check) |

## Shipped with the program (read only)
`data/config/default_settings.json`, `data/languages/*.json`, `data/splash_baseline.json`, `data/downloads_baseline.txt`,
`assets/info/*.txt`, `assets/sounds/*.wav`, `assets/owner/*`, `tools/` (yt-dlp, ffmpeg, ffprobe, ffplay).

## Online folder (GitHub repository folder; setting `online_folder_url`)
- `TubeArchivePro-YYYY-MM.txt` - ads of the month, one per line: `number  source  url` (`source` = where the picture is downloaded from, `url` = where
  a click goes). May be encrypted.
- `total_users.txt` - users of versions before the register: lines `1.0.0 = 25`. May be encrypted.
- `TubeArchivePro-x.y.z.exe` (release assets / files) - the newest version number is taken from these names.

## Google sheet (Apps Script, one row per installation)
`install_id | installation_date | version | os | language | country | rating_date | rating | feedback | new_features`
Settings `feedback_form_url` (the /exec address) and `feedback_form_fields` (JSON key of each column).

## Language files
`data/languages/<code>.json`: `meta` (`code`, `name`, `direction`, `order`) and `messages` (`MSG_001` ... `MSG_509`). A new language = a new file.
