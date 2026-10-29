# TubeArchive Pro - GitHub as the online folder (version 2.2.1)

## 1. What GitHub gives us
| Need | GitHub feature | Code (app/ads.py) |
|---|---|---|
| ads (gif), per-ad .txt, monthly list, reviews.txt | a **folder of the repository** (Contents API) | `list_github`, `sync_ads`, `read_text_file` |
| new version notice | the newest **Release** (tag like `v2.1.0`, not draft / pre-release) | `github_releases`, `github_stats` |
| number of downloads | **`download_count` of the setup file (`.exe`) attached to each Release** (GitHub counts each download of the file) | `github_stats` (total), `asset_downloads` / `file_download_count` (one file) |

Number of downloads of ONE file, example: `ads.file_download_count("https://github.com/OWNER/REPO", "TubeArchivePro_2.1.0.zip")`
(the sum over all releases that carry a file with that name).

## 2. Repository layout (suggested)
```
OWNER/REPO
  online/                          <- the folder the program reads (ads, texts)
      tubearchivepro-2026-10.txt           allowed ads of the month
      TubeArchivePro-2026-10_1.gif         the ads
      TubeArchivePro-2026-10_1.txt         link of the ad (optional)
      reviews.txt
      downloads_counter.txt                OPTIONAL: downloads before GitHub, e.g.  "old versions: 1250"
  Releases (Releases page, not a folder):
      v2.1.0  -> attach TubeArchivePro_2.1.0.zip   (+ optional .sha256: checksums / .txt are not counted)
```
Rules: tag = `v` + version (`v2.1.0`); a **draft** or **pre-release** is never offered to users and a draft is not counted.
Upload the zip as a release *file* (asset). The automatic "Source code" zips are not counted.

## 3. Setting
`current_settings.json` -> `"online_folder_url": "https://github.com/OWNER/REPO/tree/main/online"`
(also accepted: `https://github.com/OWNER/REPO` = the root folder of the repository; the default is still the Google Drive link
until you give me OWNER/REPO and I put it into `data/config/default_settings.json`.)
The repository must be **public**.

## 4. Numbers shown in the corner
`total = sum of download_count of the .exe setup files of all non-draft releases + the number in downloads_counter.txt`.
Other release files (zip, checksums, texts) are not counted.
Details per release are in the tooltip/rows. The value is cached in `data/cache/downloads_counter.json` (shown offline).

## 5. Limits you should know
* GitHub allows 60 requests per hour per IP address without a token. One program start uses 2-3 requests
  (folder, releases, + reviews page when opened). A message "GitHub limit reached" appears in `data/updates.log`; the cached values are used.
* `download_count` counts every download of the file (also by browsers retrying, bots); it is not unique users.
* Ads are fetched from the raw address of each file (`raw.githubusercontent.com`), by their fingerprint (sha): at every start the program lists the folder (1 request); an ad whose sha differs from the one stored in
  `assets/ads/ads_meta.json` is downloaded again, an unchanged one is not.
