[CmdletBinding()]
param(
    [string]$SourcePath,
    [switch]$DryRun
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
$importer = Join-Path $PSScriptRoot "sqlite_to_postgres.py"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Proje sanal ortami bulunamadi: $python"
}
if (-not (Test-Path -LiteralPath $importer)) {
    throw "Aktarim betigi bulunamadi: $importer"
}

if (-not $SourcePath) {
    $latestSnapshot = Get-ChildItem -LiteralPath (Join-Path $projectRoot "backups") `
        -Filter "lafemme_live_snapshot_before_postgres_import_*.db" -File |
        Sort-Object LastWriteTime -Descending |
        Select-Object -First 1
    if (-not $latestSnapshot) {
        throw "Canli SQLite snapshot bulunamadi. Once yedek alin."
    }
    $SourcePath = $latestSnapshot.FullName
}

$resolvedSource = (Resolve-Path -LiteralPath $SourcePath -ErrorAction Stop).Path
$securePassword = Read-Host "lafemme_app PostgreSQL parolasi" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    $encodedPassword = [Uri]::EscapeDataString($plainPassword)
    $targetUrl = "postgresql+psycopg://lafemme_app:$encodedPassword@127.0.0.1:5432/lafemme_preprod"
    $arguments = @(
        $importer,
        "--source", $resolvedSource,
        "--target-url", $targetUrl,
        "--expected-target-database", "lafemme_preprod"
    )

    if ($DryRun) {
        $arguments += "--dry-run"
    }
    else {
        $confirmation = Read-Host "Yalnizca lafemme_preprod verisi yenilenecek. Devam etmek icin AKTAR yazin"
        if ($confirmation -cne "AKTAR") {
            throw "Aktarim kullanici tarafindan iptal edildi."
        }
        $arguments += "--confirm-replace-target"
    }

    Push-Location $projectRoot
    try {
        & $python @arguments
        if ($LASTEXITCODE -ne 0) {
            throw "PostgreSQL preprod aktarimi basarisiz oldu (cikis kodu: $LASTEXITCODE)."
        }
    }
    finally {
        Pop-Location
    }
}
finally {
    if ($passwordPointer -ne [IntPtr]::Zero) {
        [Runtime.InteropServices.Marshal]::ZeroFreeBSTR($passwordPointer)
    }
}
