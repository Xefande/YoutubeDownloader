<img src="yt_downloader/assets/logo-256.png" alt="YouTube Downloader logo" width="96" height="96">

# YouTube Downloader

A free, ad-free Windows app for downloading YouTube VODs, audio and subtitles. Built for streamers, video editors and localization teams who want their files ready to work with.

**Version 1.4.1** · **Windows 10/11 x64** · **No Python installation needed for the release ZIP**

**Official website:** [youtubedownloader.xefande.com](https://youtubedownloader.xefande.com/)

[Download for Windows](https://github.com/Xefande/YoutubeDownloader/releases/latest) · [Changelog](CHANGELOG.md) · [Report an issue](https://github.com/Xefande/YoutubeDownloader/issues)

## Get started

1. Download `YouTube-Downloader-v1.4.1-win64.zip` from [Releases](https://github.com/Xefande/YoutubeDownloader/releases).
2. Extract the complete ZIP and run `Install.cmd`.
3. Open **YouTube Downloader** from the Desktop or Start Menu.
4. Paste your YouTube links, one per line, and choose an output folder.
5. Select video quality or audio-only mode. Choose an audio language and subtitle languages if needed.
6. Click **Start download** and let the app process the list.

For portable use, keep the extracted package together and run `app\YTDownloader.exe` directly. The release includes Deno and the FFmpeg tools needed for extraction, merging and audio conversion.


<img width="1407" height="790" alt="image" src="https://github.com/user-attachments/assets/2a25b0c1-336e-4b42-89c8-d2b170ee422a" />


## What you can do

- **Download a batch of videos.** Paste multiple links, including a list of 50, and start them together. Videos are processed in sequence; playlist links are supported too.
- **Choose your video quality.** Use Best available, 480p, 720p, 1080p, 1440p or 2160p/4K presets. The app selects from the formats available on YouTube.
- **Keep long VODs.** There is no built-in video-duration limit. The complete recording must be available from YouTube, with enough free disk space for the download and merge.
- **Select a preferred audio language.** Choose one language for a video's audio track. If a suitable track is unavailable, another available track may be used.
- **Download several subtitle languages.** Select multiple languages at once. Uploaded and automatic captions are requested where available and saved as separate files.
- **Export audio.** Use M4A-preferred downloading without conversion, or convert to MP3 with FFmpeg.
- **Manage storage.** Select a lower resolution or an available lower-bitrate video format. Bitrate presets range from 2 to 40 Mbps, with a No limit option.
- **Organize your files.** Choose the destination in the app. By default, each video gets a folder named with its upload date and title, and media files use the video ID.

The interface is in English. Available content languages: **English (EN), German (DE), Hungarian (HU), Italian (IT), French (FR), Spanish (ES), Slovak (SK), Czech (CZ) and Polish (PL)**.

Audio selection uses one preferred language per video. Subtitles can use several selected languages in the same download. Availability depends on the video; the app does not translate or create missing tracks.

## Everyday controls

- Follow progress and results in the activity log, including warnings, partial downloads and cancellation.
- Use **Ctrl+Enter** to start and **Esc** to request cancellation. An active network request or conversion may need to finish before the app stops.
- Use **After date** to filter videos by upload date.
- Enable **Dry-run** to check extraction without downloading media.
- Use **Update tools** to refresh yt-dlp, Deno, FFmpeg, FFprobe and FFplay when extraction or format selection needs an update.

Download history is stored in `.ytdlp_archive.txt` inside the output folder to help skip videos already downloaded there. Use a different output folder when you want another quality or language version of the same video.

Advanced folder and filename patterns can be changed through `folder_template` and `file_template` in `vod_downloader.config.json`. Close the app before editing that file.

## Install, upgrade or remove

The installer uses `%LOCALAPPDATA%\YTDownloader` and creates **YouTube Downloader** shortcuts. The window title is **Xefande's Vod Downloader**.

**Upgrading:** close the running app, extract the new release and run its `Install.cmd`. Existing settings and downloads are preserved. There is no need to uninstall first.

**Removing:** close the app and run `Uninstall.cmd` from the current release package. It removes the managed application files and shortcuts while keeping settings, downloads and updated Python tools.

**Update tools** updates the download components. To update the application itself, install a newer release ZIP.

## A few useful details

**Why MKV for 1440p and 4K?** The high-resolution presets use MKV to combine the available video and audio streams. The lower-resolution presets prefer H.264 video and AAC audio in MP4, with fallbacks when those formats are unavailable.

**Does a bitrate setting guarantee a file size?** It filters available source formats rather than re-encoding the video. The final size depends on duration, video and audio, and a very restrictive setting may leave no suitable format.

**Missing audio, subtitles or formats?** Try **Update tools**, then check whether the requested content is available on that video. YouTube restrictions, rate limits and network conditions can affect downloads. For a rate-limit response, wait before retrying.

## Support and contact

If the app helps with your work, you can [support development on the website](https://youtubedownloader.xefande.com/#support).

Have an idea for a custom app, website, Discord bot or game? [Get in touch](mailto:software@xefande.com), or explore more free tools from [Xefande Software Development](https://software.xefande.com/).

## For developers

Use **Windows x64 and Python 3.12 x64**. Clone this repository or download its source ZIP, then open a terminal in the project folder.

To run the application from source:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe vod_downloader.py
```

To build the Windows executable:

```powershell
.\Build.cmd
```

`Build.cmd` creates a `.venv-build` environment, installs the pinned dependencies and produces **`dist\YTDownloader.exe`**, including the application icon and version information. Use **Update tools** before the first download from a source run or a source-built EXE to obtain Deno and FFmpeg.

The `buildcore/` folder contains the installer and uninstaller source files and a default configuration. Those scripts require a complete release payload in their `app/` folder. `Build.cmd` builds the standalone EXE; it does not assemble the installer ZIP.
