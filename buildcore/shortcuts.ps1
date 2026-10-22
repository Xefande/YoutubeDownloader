# Keep desktop and Start Menu shortcuts aligned with the process AppUserModelID.
# https://learn.microsoft.com/windows/win32/shell/appids
if (-not ("Xefandez.ShortcutIdentity" -as [type])) {
    Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
using System.Runtime.InteropServices.ComTypes;

namespace Xefandez {
    [StructLayout(LayoutKind.Sequential, Pack = 4)]
    public struct PropertyKey { public Guid Format; public uint Id; }

    [StructLayout(LayoutKind.Explicit, Size = 24)]
    public struct PropertyValue {
        [FieldOffset(0)] public ushort Type;
        [FieldOffset(8)] public IntPtr Text;
    }

    [ComImport, Guid("886D8EEB-8CF2-4446-8D02-CDBA1DBDCF99"), InterfaceType(ComInterfaceType.InterfaceIsIUnknown)]
    public interface IPropertyStore {
        void GetCount(out uint count);
        void GetAt(uint index, out PropertyKey key);
        void GetValue(ref PropertyKey key, out PropertyValue value);
        void SetValue(ref PropertyKey key, ref PropertyValue value);
        void Commit();
    }

    public static class ShortcutIdentity {
        [DllImport("ole32.dll")] private static extern int PropVariantClear(ref PropertyValue value);
        [DllImport("shell32.dll", CharSet = CharSet.Unicode)]
        private static extern void SHChangeNotify(int events, uint flags, string item1, IntPtr item2);
        public static void Notify(string path, int change) {
            // Only notify the changed path. Never clear the global icon cache.
            SHChangeNotify(change, 0x0005 | 0x1000, path, IntPtr.Zero); // PATHW | FLUSH
        }
        private static PropertyKey AppIdKey() {
            return new PropertyKey { Format = new Guid("9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3"), Id = 5 };
        }
        private static object Load(string path) {
            object link = Activator.CreateInstance(Type.GetTypeFromCLSID(new Guid("00021401-0000-0000-C000-000000000046")));
            ((IPersistFile)link).Load(path, 2);
            return link;
        }
        public static void Set(string path, string id) {
            object link = Load(path);
            PropertyValue value = new PropertyValue { Type = 31, Text = Marshal.StringToCoTaskMemUni(id) };
            try {
                PropertyKey key = AppIdKey();
                IPropertyStore store = (IPropertyStore)link;
                store.SetValue(ref key, ref value);
                store.Commit();
                ((IPersistFile)link).Save(path, true);
            } finally {
                PropVariantClear(ref value);
                Marshal.FinalReleaseComObject(link);
            }
        }
        public static string Get(string path) {
            object link = Load(path);
            PropertyValue value = new PropertyValue();
            try {
                PropertyKey key = AppIdKey();
                ((IPropertyStore)link).GetValue(ref key, out value);
                return value.Type == 31 ? Marshal.PtrToStringUni(value.Text) : null;
            } finally {
                PropVariantClear(ref value);
                Marshal.FinalReleaseComObject(link);
            }
        }
    }
}
'@
}

function New-BrandedShortcut {
    param([string]$Path, [string]$Target, [string]$WorkingDirectory, [string]$AppId, [string]$Description, [string]$IconPath)
    if (-not (Test-Path -LiteralPath $IconPath -PathType Leaf)) { throw "Shortcut icon is missing: $IconPath" }
    $existed = Test-Path -LiteralPath $Path
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    $shortcut.TargetPath = $Target
    $shortcut.WorkingDirectory = $WorkingDirectory
    $shortcut.IconLocation = "$IconPath,0"
    $shortcut.Description = $Description
    $shortcut.Save()
    [Xefandez.ShortcutIdentity]::Set($Path, $AppId)
    [Xefandez.ShortcutIdentity]::Notify($Path, $(if ($existed) { 0x2000 } else { 0x0002 }))
}

function Remove-OwnedShortcut {
    param([string]$Path, [string]$Target)
    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) { return }
    $shell = New-Object -ComObject WScript.Shell
    $shortcut = $shell.CreateShortcut($Path)
    if ($shortcut.TargetPath -and [IO.Path]::GetFullPath($shortcut.TargetPath) -eq [IO.Path]::GetFullPath($Target)) {
        Remove-Item -LiteralPath $Path -Force
        [Xefandez.ShortcutIdentity]::Notify($Path, 0x0004)
    }
}

function Update-OwnedPinnedShortcuts {
    param([string]$Directory, [string]$Target, [string]$IconPath, [string]$AppId, [string]$Description)
    if (-not (Test-Path -LiteralPath $Directory -PathType Container)) { return }
    $shell = New-Object -ComObject WScript.Shell
    foreach ($file in Get-ChildItem -LiteralPath $Directory -Filter '*.lnk' -File) {
        $shortcut = $shell.CreateShortcut($file.FullName)
        if (-not $shortcut.TargetPath -or [IO.Path]::GetFullPath($shortcut.TargetPath) -ne [IO.Path]::GetFullPath($Target)) { continue }
        # Preserve pin order, filename, arguments, working directory and target.
        # Only the owned link's presentation and application identity are refreshed.
        $shortcut.IconLocation = "$IconPath,0"
        $shortcut.Description = $Description
        $shortcut.Save()
        [Xefandez.ShortcutIdentity]::Set($file.FullName, $AppId)
        [Xefandez.ShortcutIdentity]::Notify($file.FullName, 0x2000)
    }
}

function Install-AppShortcuts {
    param([string]$Desktop, [string]$Programs, [string]$PinnedDirectory,
          [string]$Target, [string]$IconPath, [string]$AppName, [string]$AppId,
          [string[]]$LegacyNames)
    if (-not $Desktop -or -not $Programs) { throw "Cannot locate Desktop or Start Menu." }
    $menu = Join-Path $Programs $AppName
    New-Item -ItemType Directory -Path $menu -Force | Out-Null
    foreach ($shortcutPath in @((Join-Path $Desktop "$AppName.lnk"), (Join-Path $menu "$AppName.lnk"))) {
        New-BrandedShortcut -Path $shortcutPath -Target $Target -WorkingDirectory ([IO.Path]::GetDirectoryName($Target)) -AppId $AppId -Description $AppName -IconPath $IconPath
    }
    $legacyMenus = @($LegacyNames | ForEach-Object { Join-Path $Programs $_ })
    foreach ($name in $LegacyNames) {
        Remove-OwnedShortcut -Path (Join-Path $Desktop "$name.lnk") -Target $Target
        foreach ($folder in $legacyMenus) {
            Remove-OwnedShortcut -Path (Join-Path $folder "$name.lnk") -Target $Target
        }
    }
    foreach ($folder in $legacyMenus) {
        if ((Test-Path -LiteralPath $folder) -and @(Get-ChildItem -LiteralPath $folder -Force).Count -eq 0) {
            Remove-Item -LiteralPath $folder
        }
    }
    if ($PinnedDirectory) {
        Update-OwnedPinnedShortcuts -Directory $PinnedDirectory -Target $Target -IconPath $IconPath -AppId $AppId -Description $AppName
    }
}
