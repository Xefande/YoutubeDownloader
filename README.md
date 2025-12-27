# Youtube Downloader

Created for the VOD editor guy and for localization buddies to allow easy downloading of VODs and subtitles from YouTube.

With this app, you (or your **video editor**) can easily download your stream after the live broadcast has finished.

It’s also useful for team members responsible for **localizing your videos**, as they can quickly download both the video **and** its subtitles as separate files.


## Main Features

- **Download video (MP4)**
  - Quality presets: **480p / 720p / 1080p**
  - Preferred formats: **H.264 + AAC MP4**
- **Download subtitles**
  - Languages: **HU, EN, DE, IT, FR, ES, SK, CZ, PL**
- **Download audio-only**
  - **M4A** (fast, no conversion)
  - **MP3** (main audio track)

---

## Quality of life

- Paste **multiple video URLs** (one per line)
- Choose **output folder**
- Creates a **separate subfolder per video** (upload date + title)
- Clean filenames:
  - Video: `<VIDEO_ID>.mp4`
  - Subtitles: `<VIDEO_ID>-<LANG>.vtt` (example: `dSPc5GHMydw-EN.vtt`)
- Built-in **Tool Updater**
  - Updates: `deno.exe`, `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe` with one click

---

## Installation

1. Download `YTDownloader.zip` from this release
2. Unzip it anywhere
3. Run `Install.cmd`
4. Start the app from the **Desktop** shortcut

---

## VOD Downloader UI

# YTDownloader (GUI) – YouTube VOD / Video Downloader for Editors

A small Windows-friendly GUI tool to download YouTube videos (and optional subtitles) to your PC.  
Designed so an editor can install it by: **unzip → run `Install.cmd` → start from Desktop shortcut**.


<img width="1019" height="759" alt="vodDownloader" src="https://github.com/user-attachments/assets/d027493b-abda-47cc-b1a5-c20c3ae71394" />


🎥 Preview:  


https://github.com/user-attachments/assets/d8e1caf0-61eb-4d9c-9735-dae3e5b6dbad


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

## Feature details

- Paste one or multiple youtube URLs (one per line)
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

## Notes

- If you see **subtitle HTTP 429** warnings no worries, _YouTube is rate-limiting_. Try again later or **download fewer subtitle languages at once**.
- If some formats are missing, use the **Tool Updater** (it refreshes Deno/FFmpeg tools used by yt-dlp).

 
> **Important:** This project is for legitimate use cases (e.g., downloading your own channel VODs, or content you have the rights/permission to download).

---

## For Developers

### Setup (Python)
```powershell
py -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
pip install -U yt-dlp pyinstaller



