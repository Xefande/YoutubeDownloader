param(
    [ValidateSet("Install", "Uninstall")]
    [string]$Mode = "Install",
    [switch]$SkipShortcuts
)

$ErrorActionPreference = "Stop"
$appName = "YouTube Downloader"
$appId = "Xefandez.VODDownloader"
$legacyName = "YTDownloader"
$legacyNames = @("YTDownloader", "Xefandez VOD Downloader")
if ([string]::IsNullOrWhiteSpace($env:LOCALAPPDATA)) { throw "LOCALAPPDATA is not set." }
$localRoot = [System.IO.Path]::GetFullPath($env:LOCALAPPDATA)
$target = [System.IO.Path]::GetFullPath((Join-Path $localRoot $legacyName))
if ([System.IO.Directory]::GetParent($target).FullName -ne $localRoot.TrimEnd('\')) {
    throw "Unexpected installation target: $target"
}
if ((Test-Path -LiteralPath $target) -and ((Get-Item -LiteralPath $target).Attributes -band [IO.FileAttributes]::ReparsePoint)) {
    throw "The installation target must not be a junction or symbolic link: $target"
}

$payloadNames = @("YTDownloader.exe", "deno.exe", "ffmpeg.exe", "ffprobe.exe", "ffplay.exe", "release-info.json", "YouTube-Downloader.ico")
$configName = "vod_downloader.config.json"
$desktop = [Environment]::GetFolderPath("Desktop")
$programs = [Environment]::GetFolderPath("Programs")
$menu = if ($programs) { Join-Path $programs $appName } else { $null }
$legacyMenus = if ($programs) { @($legacyNames | ForEach-Object { Join-Path $programs $_ }) } else { @() }
$executable = Join-Path $target "YTDownloader.exe"
$shortcutIcon = Join-Path $target "YouTube-Downloader.ico"

function Get-OverrideVersion([string]$Path) {
    $versionPath = Join-Path $Path "yt_dlp\version.py"
    if (-not (Test-Path -LiteralPath $versionPath -PathType Leaf)) { return $null }
    # Read the declared version as data. Never execute an installed Python override.
    $content = Get-Content -LiteralPath $versionPath -Raw -Encoding UTF8
    $match = [regex]::Match($content, '(?m)^__version__\s*=\s*[''"](?<version>\d+(?:\.\d+){2,3})[''"]\s*(?:#.*)?$')
    $parsed = $null
    if ($match.Success -and [Version]::TryParse($match.Groups['version'].Value, [ref]$parsed)) { return $parsed }
    return $null
}

if (-not $SkipShortcuts) { . (Join-Path $PSScriptRoot "shortcuts.ps1") }

if ($Mode -eq "Install") {
    $source = Join-Path $PSScriptRoot "app"
    foreach ($name in ($payloadNames + $configName)) {
        $path = Join-Path $source $name
        if (-not (Test-Path -LiteralPath $path -PathType Leaf) -or (Get-Item -LiteralPath $path).Length -eq 0) {
            throw "Missing or empty release file: $path"
        }
    }
    $releaseInfo = Get-Content -LiteralPath (Join-Path $source "release-info.json") -Raw -Encoding UTF8 | ConvertFrom-Json
    $bundledVersion = $null
    if ($releaseInfo.name -ne $appName -or $releaseInfo.app_id -ne $appId -or
            -not [Version]::TryParse([string]$releaseInfo.bundled_yt_dlp_version, [ref]$bundledVersion)) {
        throw "Invalid package identity or bundled yt-dlp version in release-info.json."
    }
    $override = Join-Path $target "_pydeps"
    $backupOverride = $false
    if (Test-Path -LiteralPath $override) {
        $overrideItem = Get-Item -LiteralPath $override
        if (-not $overrideItem.PSIsContainer -or ($overrideItem.Attributes -band [IO.FileAttributes]::ReparsePoint)) {
            throw "The Python tool override must be an ordinary directory: $override"
        }
        $overrideVersion = Get-OverrideVersion $override
        # Equal/older/unknown overrides can shadow the refreshed bundled dependencies.
        # Preserve all contents in a visible backup; keep a demonstrably newer override active.
        $backupOverride = $null -eq $overrideVersion -or $overrideVersion -le $bundledVersion
    }
    New-Item -ItemType Directory -Path $target -Force | Out-Null
    # Stage first, then replace each managed binary with rollback on locked-file/copy failures.
    $transaction = Join-Path $target (".install-" + [Guid]::NewGuid().ToString("N"))
    New-Item -ItemType Directory -Path $transaction | Out-Null
    $replaced = New-Object 'System.Collections.Generic.List[string]'
    $created = New-Object 'System.Collections.Generic.List[string]'
    $safeCleanup = $false
    $overrideBackup = $null
    try {
        $installNames = @($payloadNames)
        if (-not (Test-Path -LiteralPath (Join-Path $target $configName))) { $installNames += $configName }
        foreach ($name in $installNames) {
            Copy-Item -LiteralPath (Join-Path $source $name) -Destination (Join-Path $transaction $name)
        }
        foreach ($name in $installNames) {
            $destination = Join-Path $target $name
            if (Test-Path -LiteralPath $destination) {
                Move-Item -LiteralPath $destination -Destination (Join-Path $transaction ($name + ".previous"))
                $replaced.Add($name)
            } else { $created.Add($name) }
            Move-Item -LiteralPath (Join-Path $transaction $name) -Destination $destination
        }
        if ($backupOverride) {
            $overrideBackup = Join-Path $target ("_pydeps.before-upgrade-" + [Guid]::NewGuid().ToString("N"))
            Move-Item -LiteralPath $override -Destination $overrideBackup
        }
        $safeCleanup = $true
    } catch {
        if ($overrideBackup -and (Test-Path -LiteralPath $overrideBackup)) {
            Move-Item -LiteralPath $overrideBackup -Destination $override
        }
        foreach ($name in $created) {
            $path = Join-Path $target $name
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
        }
        foreach ($name in $replaced) {
            $path = Join-Path $target $name
            if (Test-Path -LiteralPath $path) { Remove-Item -LiteralPath $path -Force }
            Move-Item -LiteralPath (Join-Path $transaction ($name + ".previous")) -Destination $path
        }
        $safeCleanup = $true
        throw
    } finally {
        # The transaction is created directly inside the checked application directory.
        $resolvedTransaction = [System.IO.Path]::GetFullPath($transaction)
        if ([System.IO.Directory]::GetParent($resolvedTransaction).FullName -ne $target) {
            throw "Unexpected transaction cleanup path."
        }
        # Keep recovery copies if rollback itself failed.
        if ($safeCleanup) {
            Remove-Item -LiteralPath $resolvedTransaction -Recurse -Force
        }
    }
    if (-not $SkipShortcuts) {
        $pinned = if ($env:APPDATA) { Join-Path $env:APPDATA "Microsoft\Internet Explorer\Quick Launch\User Pinned\TaskBar" } else { $null }
        Install-AppShortcuts -Desktop $desktop -Programs $programs -PinnedDirectory $pinned -Target $executable -IconPath $shortcutIcon -AppName $appName -AppId $appId -LegacyNames $legacyNames
    }
    if ($overrideBackup) { Write-Host "Older or unrecognized Python tools preserved at $overrideBackup. The bundled yt-dlp is now active." }
    Write-Host "Installed $appName in $target. Existing settings and downloads were preserved."
} else {
    # Explicit managed-file list: never recursively delete a user's output directory.
    foreach ($name in $payloadNames) {
        $path = Join-Path $target $name
        if (Test-Path -LiteralPath $path -PathType Leaf) { Remove-Item -LiteralPath $path -Force }
    }
    if (-not $SkipShortcuts) {
        if ($desktop) {
            foreach ($name in (@($appName) + $legacyNames)) {
                Remove-OwnedShortcut -Path (Join-Path $desktop "$name.lnk") -Target $executable
            }
        }
        foreach ($folder in (@($menu) + $legacyMenus)) {
            if ($folder -and (Test-Path -LiteralPath $folder)) {
                foreach ($name in (@($appName) + $legacyNames)) {
                    Remove-OwnedShortcut -Path (Join-Path $folder "$name.lnk") -Target $executable
                }
                if (@(Get-ChildItem -LiteralPath $folder -Force).Count -eq 0) { Remove-Item -LiteralPath $folder }
            }
        }
    }
    Write-Host "Removed $appName binaries. Settings, downloads and any updated Python tools remain in $target."
    Write-Host "Remove that remaining folder manually only if you no longer need its contents."
}
