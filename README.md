# Youtube Downloader

Created for the VOD editor guy and for localization buddies to allow easy downloading of VODs and subtitles from YouTube.

With this app, you (or your **video editor**) can easily download your stream after the live broadcast has finished.

It’s also useful for team members responsible for **localizing your videos**, as they can quickly download both the video **and** its subtitles as separate files.

## ⚡ Quick Start (30 seconds)

1. Go to **Releases** and download the latest **`YTDownloader.zip`**
2. Unzip it anywhere (example: `C:\Tools\YTDownloader\`)
3. Double click **`Install.cmd`** hit **Enter**
4. Launch **YTDownloader** from the **Desktop shortcut**
5. Paste one or more YouTube URLs (**one per line**)
6. Pick your **output folder**
7. Choose:
   - **Quality** (1080p MP4 recommended) or **2K/4K (MKV)**
   - Optional: **Audio track language**
   - Optional: **Subtitles**
8. Click **Start Download**

✅ If anything breaks (missing formats / extraction issues), click **Update Tools** and try again.

🎥 Preview:  

https://github.com/user-attachments/assets/d8e1caf0-61eb-4d9c-9735-dae3e5b6dbad

## Main Features
### Download video
- **MP4 downloads (recommended for 1080p and below)**
  - Quality presets: **480p / 720p / 1080p**
  - Preferred formats: **H.264 + AAC MP4**
- **High-resolution downloads**
  - **2K (1440p)** and **4K (2160p)** support
  - High-res downloads are saved as **MKV** (more reliable for VP9/AV1 + audio merging)
### Download subtitles
- Download subtitles as **separate files**
- Languages: **HU, EN, DE, IT, FR, ES, SK, CZ, PL**
### Select audio channel
 - Choose which **audio language/track** to download with the video
 - Languages: **HU, EN, DE, IT, FR, ES, SK, CZ, PL, Default**
### Download audio-only
- **M4A** (fast, no conversion)
- **MP3** (main audio track)
### Select bitrate
  - Set a maximum video bitrate to control **file size** and **bandwidth usage** (2K / 4K)
  - Available bitrate settings: 2 Mbps, 4 Mbps, 6 Mbps, 8 Mbps, 12 Mbps, 20 Mbps, 40 Mbps, No limit
 
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

## Download (Recommended)

Go to the **Releases** page and download the latest **`YTDownloader.zip`**.

---

## Installation

1. Download **`YTDownloader.zip`** from the latest Release
2. Unzip it anywhere (e.g. `C:\Tools\YTDownloader\`)
3. Run **`Install.cmd`**
4. Start the app from the **Desktop shortcut** (or Start Menu)

### Uninstall

- Close the app
- Run the included `Uninstall.cmd`, **or** delete:
  - `%LOCALAPPDATA%\YTDownloader`

---

## VOD Downloader UI

# YTDownloader (GUI) – YouTube VOD / Video Downloader for Editors

A small Windows-friendly GUI tool to download YouTube videos (and optional subtitles) to your PC.  
Designed so an editor can install it by: **unzip → run `Install.cmd` → start from Desktop shortcut**. *_no programming skills required_

<img width="1043" height="998" alt="vodDownloaderPro" src="https://github.com/user-attachments/assets/31608626-0268-4a7e-9f4d-64ad95052092" />

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

## FAQ

### Why is 2K/4K saved as MKV instead of MP4?
YouTube often serves 2K/4K streams using **VP9 or AV1** video codecs. MP4 merging can be unreliable in these cases, while **MKV is the most stable container** for high-res (video + audio).

### I selected “Italian audio”, but it still downloads German voicover. Why?
Usually one of these is happening:
- The video **does not contain** a Italian audio track, that case the downloaded audio chanell is the videos default audio track
- The track exists, but YouTube/metadata doesn’t label it cleanly
- YouTube serves the chosen track differently for that video

✅ Tip: Try **Update Tools**, then retry. If it still happens, that specific video likely has no IT track available.

### What does “Max bitrate (2K/4K)” do?
It sets an upper limit on the selected **video bitrate**, so even at 2K/4K the downloader avoids extremely large streams. This helps manage:
- download time
- file size
- bandwidth usage

### I get `HTTP 429` while downloading subtitles. Is it a bug?
No, its not a but. - YouTube is rate-limiting or you try to download a non-existing subtitle language.  
✅ Fix: Try again later, or download **fewer subtitle languages** at once. Most of the time, the download will happen despite the warning.

### Some formats are missing / extraction fails. What should I do?
Click **Update Tools**. It refreshes:
- Deno + FFmpeg tools (used for extraction/merge)
- **yt-dlp** (the extractor that needs frequent updates when YouTube changes)

### What is “Update Tools” exactly updating?
One click updates:
- `deno.exe`
- `ffmpeg.exe`, `ffprobe.exe`, `ffplay.exe`
- `yt-dlp`

After that, the app will use the updated versions automatically.

### Where are the downloaded files saved?
- You choose an output folder in the UI.
- The app creates one subfolder per item (upload date + title).
- File naming is kept clean:
  - Video: `<VIDEO_ID>.<ext>`
  - Subtitles: `<VIDEO_ID>-<LANG>.vtt`

---

## Notes

- **Subtitle HTTP 429 warnings**  
  YouTube is rate-limiting. Try again later or download fewer subtitle languages at once.

- **Missing formats / extraction issues**  
  Use **Tool Updater** (it refreshes Deno/FFmpeg and updates **yt-dlp**, which is the most common fix when YouTube changes something).

- **2K/4K output is MKV**  
  This is intentional for stability: YouTube high-res often uses VP9/AV1, and MKV merges more reliably than MP4.

 
> **Important:** This project is for legitimate use cases (e.g., downloading your own channel VODs, or content you have the rights/permission to download).

---

## For Developers

### Setup (Python)
```powershell
py -m venv .venv
.\.venv\Scripts\activate
python -m pip install -U pip
pip install -U yt-dlp pyinstaller
```
### Run (dev)
```powershell
python VOD_Downloader.py
```
### Build (dev)
```powershell
pyinstaller --noconfirm --clean --onefile --windowed VOD_Downloader.py
```
