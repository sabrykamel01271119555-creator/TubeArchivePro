# TubeArchive Pro | Version 2.3.2 | build\get_tools.ps1
# Downloads everything the build needs and that is still missing (nothing is downloaded twice):
#   tools\yt-dlp.exe, tools\ffmpeg.exe, tools\ffprobe.exe, build\Arabic.isl, build\ChineseSimplified.isl, build\Hindi.isl,
#   build\redist\vc_redist.x64.exe.   Called by build.bat; you can also run:  powershell -ExecutionPolicy Bypass -File build\get_tools.ps1
$ErrorActionPreference = "Stop"
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12
$ProgressPreference = "SilentlyContinue"
$root  = Split-Path -Parent $PSScriptRoot
$tools = Join-Path $root "tools"
$build = Join-Path $root "build"
New-Item -ItemType Directory -Force -Path $tools, (Join-Path $build "redist") | Out-Null

function Get-File($url, $dest) {
    if (Test-Path $dest) { Write-Host "  have     $dest"; return }
    Write-Host "  download $url"
    try { Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing }
    catch { Write-Host "  FAILED   $url  ($($_.Exception.Message))"; if (Test-Path $dest) { Remove-Item $dest -Force }; return $false }
    return $true
}

# 1. yt-dlp
Get-File "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe" (Join-Path $tools "yt-dlp.exe") | Out-Null

# 2. ffmpeg + ffprobe (gyan.dev "release essentials": enough for the program, about half the size of "full")
if (-not ((Test-Path (Join-Path $tools "ffmpeg.exe")) -and (Test-Path (Join-Path $tools "ffprobe.exe")))) {
    $zip = Join-Path $env:TEMP "ffmpeg-release-essentials.zip"
    $tmp = Join-Path $env:TEMP "ffmpeg-essentials-extract"
    if (Get-File "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip" $zip) {
        if (Test-Path $tmp) { Remove-Item $tmp -Recurse -Force }
        Expand-Archive -Path $zip -DestinationPath $tmp -Force
        foreach ($n in "ffmpeg.exe", "ffprobe.exe") {
            $f = Get-ChildItem $tmp -Recurse -Filter $n | Select-Object -First 1
            if ($f) { Copy-Item $f.FullName (Join-Path $tools $n) -Force; Write-Host "  copied   $n" }
        }
        Remove-Item $zip, $tmp -Recurse -Force -ErrorAction SilentlyContinue
    }
} else { Write-Host "  have     ffmpeg.exe, ffprobe.exe" }

# 3. wizard languages that Inno Setup does not ship (optional)
$isl = "https://raw.githubusercontent.com/jrsoftware/issrc/main/Files/Languages/Unofficial/"
foreach ($n in "Arabic.isl", "ChineseSimplified.isl", "Hindi.isl") { Get-File ($isl + $n) (Join-Path $build $n) | Out-Null }

# 4. Microsoft Visual C++ runtime (installed silently by the setup only when the PC does not have it)
Get-File "https://aka.ms/vs/17/release/vc_redist.x64.exe" (Join-Path $build "redist\vc_redist.x64.exe") | Out-Null
Write-Host "get_tools finished."
