param(
    [int]$Port = 0
)

$ErrorActionPreference = 'Stop'
$serverPath = Join-Path $PSScriptRoot 'server.py'
$python = Get-Command python -ErrorAction SilentlyContinue
$launcher = $null
if ($null -eq $python) { $launcher = Get-Command py -ErrorAction SilentlyContinue }
if ($null -eq $python -and $null -eq $launcher) {
    throw 'Python 3.9 or newer is required. Install Python, then run this script again.'
}

$previousPort = $env:PORT
if ($Port -gt 0) {
    $env:PORT = [string]$Port
}

try {
    if ($null -ne $python) {
        & $python.Source $serverPath
    } else {
        & $launcher.Source -3 $serverPath
    }
} finally {
    $env:PORT = $previousPort
}
