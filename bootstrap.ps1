# AI OS Bootstrap - Windows PowerShell wrapper
$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path

$Python = Get-Command python -ErrorAction SilentlyContinue
if (-not $Python) {
    Write-Error "Python not found. Install Python 3.10+ and add to PATH."
    exit 1
}

& python "$Root\scripts\ai-os.py" bootstrap @args
exit $LASTEXITCODE
