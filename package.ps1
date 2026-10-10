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

# Bundles hold the models (and the reel sounds); the bobber is still an .obj and the Horn of Aegir's blast a .wav.
# Other .obj files are older copies of models that are now in the bundles, so they're left out, as are the
# bundles_backup_* / icons_backup_* folders.
if (Test-Path $ModelsDir) {
    Get-ChildItem $ModelsDir -File | Where-Object {
        $_.Extension -eq '.bundle' -or $_.Name -like '*_icon.png' -or $_.Name -in 'bobber.obj', 'bobber.png', 'horn_of_aegir.wav'
    } | Copy-Item -Destination "$stage\config\ValheimDeepWaters\Models\"
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
