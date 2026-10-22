# Changelog

## 1.4.1b - 2026-10-22

- Add self-signed Authenticode signatures as **Xefande** to `YTDownloader.exe`, `install.ps1` and `shortcuts.ps1` in the official release ZIP.
- Include the public `publisher.cer` certificate and signature evidence in the package. No private key is distributed and no certificate is installed into Windows trust stores.
- A self-signed certificate does not establish automatic Windows trust or Microsoft certification; SmartScreen warnings can still appear.
- Keep the displayed version `1.4.1b` and numeric Windows file/product version `1.4.1.2` consistent. Support the revision letter in the public source build and set its company metadata to **Xefande**.
- Preserve the application behavior, artwork, settings and bundled tools from 1.4.1. Public source builds remain unsigned.

### Download verification

**Package:** `YouTube-Downloader-v1.4.1b-win64.zip`

**Size:** 183,777,271 bytes

**SHA256:**

```text
64836f17d313f18de692b88bf3e359d247bfc17347f40ec7b70656dc361cf668
```

The signed release passed 94 automated tests, package validation and cryptographic signature/content verification.

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

The latest stable download tool versions were checked on **2026-10-22** and are included in the release ZIP. No first-use **Update tools** step is required.

| Component | Version |
| --- | --- |
| yt-dlp | 2026.10.21 |
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
**Size:** 183,751,298 bytes

**SHA256:**

```text
fffefb58c9a27af54dbddd66201706da46ff5ce95b78078c98c46c601b5aff4f
```

### For developers

- Split the application into smaller components for interface, configuration, downloads, tool updates and platform integration.
- Added pinned runtime and build dependencies, executable version information, release metadata and SHA256 checksums.
- Added `Build.cmd` for Windows x64 source builds with Python 3.12. The output is `dist\YTDownloader.exe`.
- Included the installer source in `buildcore/`. Source builds produce a standalone EXE; the release ZIP includes the complete installer payload and external tools.
- Validated the release with 90 automated tests and an additional Czech-checkbox regression check using the UI code embedded in the built EXE.
