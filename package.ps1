# Builds the mod and makes the Thunderstore package: dist\Valheim_Deep_Waters-<version>.zip
#
#   .\package.ps1                     build and package
#   .\package.ps1 -ModelsDir <path>   take models and icons from another folder
#
# The package holds:
#   manifest.json, icon.png, README.md, CHANGELOG.md
#   plugins\ValheimDeepWaters.dll
#   config\ValheimDeepWaters\Models\   the custom models (bundles, bobber) and icons; r2modman / Thunderstore
#                                      Mod Manager installs this into BepInEx\config
param(
    [string]$ModelsDir = "$env:APPDATA\Thunderstore Mod Manager\DataFolder\Valheim\profiles\Test\BepInEx\config\ValheimDeepWaters\Models"
)
$ErrorActionPreference = 'Stop'
$root = $PSScriptRoot

$manifest = Get-Content "$root\thunderstore\manifest.json" -Raw | ConvertFrom-Json
$version = $manifest.version_number
$pluginVersion = (Select-String -Path "$root\src\Core\Plugin.cs" -Pattern 'Version = "([^"]+)"').Matches[0].Groups[1].Value
if ($pluginVersion -ne $version) { throw "manifest.json says $version but Plugin.cs says $pluginVersion - make them match." }

dotnet build "$root\ValheimDeepWaters.csproj" -c Release
if ($LASTEXITCODE -ne 0) { throw "Build failed." }

$stage = "$root\dist\stage"
if (Test-Path $stage) { Remove-Item $stage -Recurse -Force }
New-Item -ItemType Directory -Force "$stage\plugins", "$stage\config\ValheimDeepWaters\Models" | Out-Null

Copy-Item "$root\thunderstore\manifest.json", "$root\thunderstore\icon.png", "$root\README.md", "$root\CHANGELOG.md" $stage
Copy-Item "$root\bin\Release\netstandard2.1\ValheimDeepWaters.dll" "$stage\plugins\"

# Bundles hold the models (the bobber too) and the reel sounds; they ship packed as .vdwpak so asset rippers can't
# open them (src\Models\PackedBundles.cs reads them back; the scheme below must match it). The Horn of Aegir's blast
# is a .wav, the icons .png. Loose .obj files are older copies of models now in the bundles, so they're left out, as
# are the bundles_backup_* / icons_backup_* folders.
Add-Type -TypeDefinition @'
public static class VdwPack
{
    const int PadSize = 4096;
    static byte[] BuildPad()
    {
        var pad = new byte[PadSize];
        uint x = 0x9E3779B9u ^ 0x56445750u;
        for (int i = 0; i < PadSize; i++) { x ^= x << 13; x ^= x >> 17; x ^= x << 5; pad[i] = (byte)(x >> 24); }
        return pad;
    }
    public static void Pack(string from, string to)
    {
        var pad = BuildPad();
        var data = System.IO.File.ReadAllBytes(from);
        for (long p = 0; p < data.LongLength; p++) data[p] ^= (byte)(pad[p % PadSize] ^ (byte)((p / PadSize) * 167));
        System.IO.File.WriteAllBytes(to, data);
    }
}
'@
if (Test-Path $ModelsDir) {
    $dest = "$stage\config\ValheimDeepWaters\Models"
    Get-ChildItem $ModelsDir -File -Filter *.bundle | ForEach-Object {
        [VdwPack]::Pack($_.FullName, (Join-Path $dest ($_.BaseName + '.vdwpak')))
    }
    Get-ChildItem $ModelsDir -File | Where-Object {
        $_.Name -like '*_icon.png' -or $_.Name -eq 'horn_of_aegir.wav'
    } | Copy-Item -Destination $dest
} else {
    Write-Warning "Models folder not found ($ModelsDir); packaging without models and icons."
}

$zip = "$root\dist\Valheim_Deep_Waters-$version.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
# Written by hand rather than with Compress-Archive, which (in Windows PowerShell 5.1) stores paths with
# backslashes that Thunderstore and Linux mod managers don't treat as folders.
Add-Type -AssemblyName System.IO.Compression, System.IO.Compression.FileSystem
$archive = [System.IO.Compression.ZipFile]::Open($zip, [System.IO.Compression.ZipArchiveMode]::Create)
try {
    Get-ChildItem $stage -Recurse -File | ForEach-Object {
        $entry = $_.FullName.Substring($stage.Length + 1).Replace('\', '/')
        [System.IO.Compression.ZipFileExtensions]::CreateEntryFromFile($archive, $_.FullName, $entry, [System.IO.Compression.CompressionLevel]::Optimal) | Out-Null
    }
} finally { $archive.Dispose() }
Remove-Item $stage -Recurse -Force

$size = [math]::Round((Get-Item $zip).Length / 1MB, 1)
Write-Host "Packaged $zip ($size MB)"
