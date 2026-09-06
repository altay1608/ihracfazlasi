[CmdletBinding()]
param()

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
        & $python -m flask --app run:app identity seed-dev-sandbox
        if ($LASTEXITCODE -ne 0) {
            throw "DEV sandbox verisi hazirlanamadi (cikis kodu: $LASTEXITCODE)."
        }

        & $python -m flask --app run:app identity bootstrap-platform-admin
        if ($LASTEXITCODE -ne 0) {
            throw "Platform admin bootstrap basarisiz oldu (cikis kodu: $LASTEXITCODE)."
        }

        $verificationCode = @"
from app import create_app
from app.extensions import db
from sqlalchemy import text

app = create_app()
with app.app_context():
    row = db.session.execute(text('''
        SELECT
            (SELECT COUNT(*) FROM users WHERE username = 'admin' AND is_platform_superadmin = true AND is_active = true),
            (SELECT COUNT(*)
             FROM user_site_roles usr
             JOIN users u ON u.id = usr.user_id
             JOIN sites s ON s.id = usr.site_id
             WHERE u.username = 'admin' AND s.code = 'DEV' AND s.is_sandbox = true AND usr.is_active = true),
            (SELECT COUNT(*)
             FROM user_site_roles usr
             JOIN users u ON u.id = usr.user_id
             JOIN sites s ON s.id = usr.site_id
             WHERE u.username = 'admin' AND s.is_sandbox = false AND usr.is_active = true),
            (SELECT COUNT(*) FROM products p JOIN sites s ON s.id = p.site_id WHERE s.code = 'DEV'),
            (SELECT COALESCE(SUM(si.stock_quantity), 0)
             FROM store_inventories si
             JOIN sites s ON s.id = si.site_id
             JOIN stores st ON st.id = si.store_id
             WHERE s.code = 'DEV' AND st.code = 'TEST')
    ''')).one()
    platform_admin, dev_membership, customer_membership, dev_products, dev_stock = row
    if platform_admin != 1 or dev_membership != 1 or customer_membership != 0:
        raise SystemExit(
            'KIMLIK_DOGRULAMA_BASARISIZ platform_admin={} dev_membership={} customer_membership={}'.format(
                platform_admin, dev_membership, customer_membership
            )
        )
    print(
        'PREPROD_KIMLIK_HAZIR platform_admin={} dev_membership={} customer_membership={} dev_products={} dev_stock={}'.format(
            platform_admin, dev_membership, customer_membership, dev_products, dev_stock
        )
    )
"@
        & $python -c $verificationCode
        if ($LASTEXITCODE -ne 0) {
            throw "Preprod kimlik dogrulamasi basarisiz oldu (cikis kodu: $LASTEXITCODE)."
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
