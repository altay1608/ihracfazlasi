[CmdletBinding()]
param(
    [string]$Label = "manual"
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$backupDirectory = Join-Path $projectRoot "backups\postgres"
$postgresBin = "C:\Program Files\PostgreSQL\18\bin"
$pgDump = Join-Path $postgresBin "pg_dump.exe"

if (-not (Test-Path -LiteralPath $pgDump)) {
    throw "pg_dump bulunamadi: $pgDump"
}

$safeLabel = ($Label -replace "[^A-Za-z0-9_-]", "_").Trim("_")
if (-not $safeLabel) {
    $safeLabel = "manual"
}

New-Item -ItemType Directory -Path $backupDirectory -Force | Out-Null
$timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$backupPath = Join-Path $backupDirectory "lafemme_preprod_${safeLabel}_${timestamp}.dump"

$securePassword = Read-Host "lafemme_app PostgreSQL parolasi" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    $env:PGPASSWORD = $plainPassword

    & $pgDump --host 127.0.0.1 --port 5432 --username lafemme_app --format custom --file $backupPath lafemme_preprod
    if ($LASTEXITCODE -ne 0) {
        throw "PostgreSQL preprod yedegi basarisiz oldu (cikis kodu: $LASTEXITCODE)."
    }
    if (-not (Test-Path -LiteralPath $backupPath) -or (Get-Item -LiteralPath $backupPath).Length -le 0) {
        throw "PostgreSQL preprod yedegi dogrulanamadi."
    }

    Write-Output "PREPROD_YEDEK_BASARILI: $backupPath"
}
finally {
    if ($passwordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    }
    Remove-Item Env:PGPASSWORD -ErrorAction SilentlyContinue
}
