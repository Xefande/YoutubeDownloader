# YoutubeDownloader

Created for the VOD editor guy and my localization buddies to allow easy downloading of VODs and subtitles from YouTube.


# YTDownloader (GUI) – YouTube VOD / Video Downloader for Editors

A small Windows-friendly GUI tool to download YouTube videos (and optional subtitles) to your PC.  
Designed so an editor can install it by: **unzip → run `Install.cmd` → start from Desktop shortcut**.

> **Note:** This project is for legitimate use cases (e.g., downloading your own channel VODs, or content you have the rights/permission to download).

---

## Download (Recommended)

Go to the **Releases** page and download the latest `YTDownloader.zip`.

### Install
1. Unzip `YTDownloader.zip`
2. Double click `Install.cmd`
3. Start **YTDownloader** from the Desktop shortcut (or Start Menu)

### Uninstall
- Run `Uninstall.cmd` (if included), or delete:
  - `%LOCALAPPDATA%\YTDownloader`

---

## Features

- Paste one or multiple URLs (one per line)
- Choose:
  - Output folder
  - Video quality preset (H.264 + AAC MP4 preferred presets)
  - Audio-only mode
  - Subtitle languages: **HU, EN, DE, IT, SK, CS, PL, ES, FR**
- Creates a dedicated subfolder per item (upload date + title)
- Built-in **“Update tools”** button to refresh:
  - `deno.exe`
  - `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe`
- Uses a portable cache folder inside the output directory (`.ytdlp_cache`)

---

## Requirements (End User)

- Windows 10/11
- No Python installation required (Release build includes the app)

---

## For Developers

### Setup (Python)
```powershell
py -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
pip install -U yt-dlp pyinstaller



