param(
    [int]$Port = 0
)

$ErrorActionPreference = 'Stop'
$serverPath = Join-Path $PSScriptRoot 'server.ps1'
if ($Port -gt 0) {
    & $serverPath -Port $Port
} else {
    & $serverPath
}
