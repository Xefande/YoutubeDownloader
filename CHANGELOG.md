# Changelog

## 1.4.1

A refreshed Windows release with a clearer dark interface, updated download tools and improved installation and download feedback. This summary covers the changes since the previous public release, 1.1.0.

### Interface and usability

- Redesigned the dark interface with clearer sections, download controls, progress feedback and activity messages.
- Added the new turquoise logo throughout the application, executable and Windows shortcuts.
- Standardized the launcher, Desktop/Start Menu shortcuts and in-app heading as **YouTube Downloader**. The native window title is **Xefande's Vod Downloader**.
- Fixed checkbox and radio-button labels becoming unreadable on hover and other interaction states.
- Applied the dark Windows title bar before the window first appears.
- Fixed Windows icon handling with a dedicated shortcut icon and explicit window icons.
- Corrected the Czech subtitle checkbox and activity log to show **CZ**. The internal `cs` language code and saved settings remain compatible.

### Downloads and reliability

- Improved progress and result reporting, with separate completed, warning, partial-failure and cancelled outcomes.
- Improved cancellation handling and kept completed media and resumable partial files available.
- Preserved subtitle-language selections when subtitles are switched off and saved.
- Added clearer validation for download settings and safer configuration persistence.
- Improved tool-update recovery and reporting when only part of an update succeeds.
- Preserved existing video, audio, subtitle, batch-download and output-organization workflows.

### Installation and upgrades

- Preserved existing settings and downloads during upgrades.
- Added rollback for managed application files if replacement fails during installation.
- Preserved outdated or unrecognized local yt-dlp overrides in a backup so they do not hide the bundled version; known newer overrides remain active.
- Updated owned legacy shortcuts and refreshed their icons without changing unrelated shortcuts.
- Kept settings, downloaded media and updated Python tools when using the current uninstaller.

### Bundled components

| Component | Version |
| --- | --- |
| yt-dlp | 2026.8.19 |
| yt-dlp-ejs | 0.8.0 |
| Deno | 2.9.8 |
| FFmpeg, FFprobe and FFplay | 9.0.2 |
| Python runtime | 3.12.10 |

### Install or upgrade

1. Download and extract `YouTube-Downloader-v1.4.1-win64.zip`.
2. Close the running application and run the new `Install.cmd`.
3. Open **YouTube Downloader** from the Desktop or Start Menu.

No prior uninstall is required. Existing settings and downloads are preserved. For portable use, keep the extracted package together and run `app\YTDownloader.exe`.

### Download verification

**Package:** `YouTube-Downloader-v1.4.1-win64.zip`  
**Size:** 183,738,532 bytes

**SHA256:**

```text
49e7313bc1ceb46cd29b62dbcbeb5473f7dbeee05b2878c595dc3eeb7a0cfa75
```

### For developers

- Split the application into smaller components for interface, configuration, downloads, tool updates and platform integration.
- Added pinned runtime and build dependencies, executable version information, release metadata and SHA256 checksums.
- Added `Build.cmd` for Windows x64 source builds with Python 3.12. The output is `dist\YTDownloader.exe`.
- Included the installer source in `buildcore/`. Source builds produce a standalone EXE; the release ZIP includes the complete installer payload and external tools.
- Validated the release with 90 automated tests and an additional Czech-checkbox regression check using the UI code embedded in the built EXE.
