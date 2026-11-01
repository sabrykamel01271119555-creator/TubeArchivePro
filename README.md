# TubeArchive Pro (v2.3.2)

Windows desktop app (Python + PySide6) that will download YouTube videos/playlists with **yt-dlp.exe**.
Working now: splash screen, main window, exit flow, the **New Download** tab (real downloads) and the **Downloads** tab (history + favorites).
The other tabs are still design-only.


💡 Version 2.3.6 - this help file lives in assets/info/help.en.txt. The program shows it in your language when a help file for it exists, otherwise in English.

● What is new in 2.3.6, 2.3.2, 2.3.1 and 2.3.0
Downloads list - the X of a finished download removes it from the list: green check = completed, red cross = failed.
Reviews show the comment and the features the users wish for, with the average rating.
Splash screen - users and users per version together on the left, the rating on the right.
Faster splash screen - it appears first and counts every number from 1 to the number of users in 10 seconds: a big coral number and a colour bar from red to green.
Open a playlist - double-click a playlist card in the Archive / Library: its videos open in the same work area, in order, with their pictures. Back to the list returns.
Same video, one record - a direct video link that was already downloaded inside a playlist is recognised as downloaded, and a video downloaded directly is not downloaded again when the playlist is synced.
Videos that cannot be downloaded - a window lists them with Retry now, Later (kept, you are reminded at the next start) and Cancel (ignored).
Sync all - ONE window: a progress bar (playlist 3 of 12), the picture and details of the playlist being checked, and below them the work area with the list of new videos (choose, then the next playlist follows) or the "nothing new" message (moves on by itself). Chosen downloads start when the window closes. The Settings page now fits the window at any size.
2K / 4K / 8K - the quality list goes on after 1080p (when the video offers it) and shows the size beside every quality.
MP4 for editors and TVs - MP4 files are H.264 + AAC, so they open in Premiere, After Effects, DaVinci Resolve and on almost every TV and player. 2K / 4K / 8K streams come as VP9 / AV1 from YouTube, so they are converted (slower). Switch in Settings: *MP4 = H.264 + AAC*.
Reviews show the real ratings and comments of our users. About us now also holds Contact us and Donate.
Links that belong to a playlist - when you check or start a video link that also carries a playlist, the program asks what to do. Playlist not downloaded before: Download playlist, Check playlist, Download file only or Cancel. Playlist downloaded before: the window tells you whether THIS file was downloaded before and shows the list (videos in the history, last sync, folder) with Sync playlist.
Sync results - when a playlist is synced and nothing is new, a window says so, shows when the next sync is due and lets you change the schedule (daily, weekly, monthly, yearly) or switch automatic sync off.
Sync all / checking window - shows which playlist is being checked, how many files are already there, the last sync, the quality and the saved folder.
Updates window - Settings > Check for updates now. It shows the program version, and the tools (yt-dlp, ffmpeg). Tick Update tools to install them; a progress window shows the percentage and the total size. Tools are also checked at start-up and after a download fails for a reason an old yt-dlp can cause. Updates are not installed while downloads are running.
System tray - the minimize button sends the program to the tray (next to the clock). Click the icon or choose Open to bring it back; Exit closes it. Downloads keep running.
More languages - English and Arabic first, then Chinese, Hindi, Spanish, French, Portuguese, Russian, German and Turkish. The setup can install only the languages you want.
Sound effects - new soft sounds for clicks, tabs, finished downloads and warnings (switch them off in Settings > Notifications).
Rating window - rate the program and tell us which features you would like. The splash screen shows the number of users and the average rating.
Usage count - the program sends an anonymous install ID, the version, the Windows language and the country once, so we can count users. Switch it off with Share anonymous usage information in Settings.
● How to download a video
Open New Download, paste a YouTube link and press Check.
Choose the format, the quality and the save folder.
Press Start. The video joins the queue - you can paste the next link at once.
Watch the progress on the Downloads page. Pause, resume or cancel each file there.
If the video was downloaded before, a window offers Redownload, Play or Cancel.
● How to download a playlist
Paste a playlist link (/playlist?list=) - or a video link and choose Download playlist when asked.
In the window that opens choose whether to create a folder, and whether to keep the playlist in Playlist Sync (and how often).
On the Downloads page press Details to see every video. Use Skip this one to leave a video out.
Files are numbered 01, 02 ... (001 ... for bigger playlists).
● Archive, Library and favorites
Archive - everything downloaded through TubeArchive Pro: Videos, Audio and Playlists.
Library - only the videos you put in a favorite category (Cinema, Music ...). Use the star button, or Add to Favorite in the success window.
Create, rename and delete categories in Settings > Favorite Categories.
● Playlist Sync
Keeps downloaded playlists up to date. Switch a playlist ON (green), choose how often to check, and press Sync now (one playlist) or Sync all. The window lists the new videos, the videos you skipped, files that disappeared from the folder and files that are there. When the sync date has come, the program asks at start-up: Sync now (in the background), Let me check or Later.
● Settings
Everything is saved with Apply & Save; Reset to Default brings back the factory values.
Max concurrent downloads, Max network bandwidth (0 = unlimited), notifications, sound effects, usage information.
Check for updates now - see the Updates window above.
● Updates, ads and statistics
At start-up the program reads the online folder: the newest program version (you are asked), the ads of the month and the numbers for the splash screen. The online text files may be encrypted; the program opens them itself.
● Problems?
Nothing downloads: check your internet connection. Open Settings > Check for updates now and update the tools - an old yt-dlp is the most common reason.
A video is "unavailable" or "private": it cannot be downloaded.
The window looked odd or a message appeared on the console: please tell us (Contact us) and attach data/error.log if there is one.
