param(
    [string]$ValheimDir = "D:\SteamLibrary\steamapps\common\Valheim"
)

$env:ValheimDir = $ValheimDir
dotnet build .\ValheimDeepWaters.csproj -c Release -p:ValheimDir="$ValheimDir"

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build failed." -ForegroundColor Red
    exit $LASTEXITCODE
}

$dest = Join-Path $ValheimDir "BepInEx\plugins\ValheimDeepWaters"
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Copy-Item ".\bin\Release\netstandard2.1\ValheimDeepWaters.dll" $dest -Force
Write-Host "Installed ValheimDeepWaters.dll" -ForegroundColor Green
