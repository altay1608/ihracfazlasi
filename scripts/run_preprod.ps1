[CmdletBinding()]
param(
    [switch]$MigrateOnly,
    [int]$Port = 5004
)

$ErrorActionPreference = "Stop"

$projectRoot = Split-Path -Parent $PSScriptRoot
$python = Join-Path $projectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path -LiteralPath $python)) {
    throw "Proje sanal ortami bulunamadi: $python"
}

$securePassword = Read-Host "lafemme_app PostgreSQL parolasi" -AsSecureString
$passwordPointer = [Runtime.InteropServices.Marshal]::SecureStringToBSTR($securePassword)
try {
    $plainPassword = [Runtime.InteropServices.Marshal]::PtrToStringBSTR($passwordPointer)
    $encodedPassword = [Uri]::EscapeDataString($plainPassword)
    $env:DATABASE_URL = "postgresql+psycopg://lafemme_app:$encodedPassword@127.0.0.1:5432/lafemme_preprod"

    Push-Location $projectRoot
    try {
        & $python -m flask --app run:app db upgrade
        if ($LASTEXITCODE -ne 0) {
            throw "Alembic migration basarisiz oldu (cikis kodu: $LASTEXITCODE)."
        }

        $verificationCode = @"
from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    database_name, product_count, transaction_count, opening_quantity, audit_enabled = db.session.execute(
        text('''
            SELECT
                current_database(),
                (SELECT COUNT(*) FROM products),
                (SELECT COUNT(*) FROM inventory_transactions),
                (SELECT COALESCE(SUM(quantity_delta), 0) FROM inventory_transactions WHERE transaction_code = 'OPENING-BAL'),
                (SELECT value FROM system_settings WHERE key = 'audit_logging_enabled')
        ''')
    ).one()
    print(
        'PREPROD_DOGRULAMA database={} product_count={} inventory_transactions={} opening_quantity={} audit_enabled={}'.format(
            database_name,
            product_count,
            transaction_count,
            opening_quantity,
            audit_enabled,
        )
    )
"@
        & $python -c $verificationCode
        if ($LASTEXITCODE -ne 0) {
            throw "Preprod veritabani dogrulamasi basarisiz oldu (cikis kodu: $LASTEXITCODE)."
        }

        if (-not $MigrateOnly) {
            & $python -m flask --app run:app run --host 127.0.0.1 --port $Port --no-reload
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
    Remove-Item Env:DATABASE_URL -ErrorAction SilentlyContinue
}
