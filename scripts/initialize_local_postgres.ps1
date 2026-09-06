[CmdletBinding()]
param(
    [string]$DatabaseUser = "lafemme_app",
    [string]$DatabaseName = "lafemme_preprod"
)

$ErrorActionPreference = "Stop"

$psql = "C:\Program Files\PostgreSQL\18\bin\psql.exe"
if (-not (Test-Path -LiteralPath $psql)) {
    throw "PostgreSQL psql bulunamadı: $psql"
}

# Parolalar bu betikte veya proje dosyalarında tutulmaz. psql hem postgres hem de
# uygulama kullanıcısı parolasını doğrudan, görünmeyen terminal istemleriyle alır.
$setupSql = @"
DO `$`$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '$DatabaseUser') THEN
        CREATE ROLE $DatabaseUser LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT;
    END IF;
END
`$`$;
\password $DatabaseUser
SELECT format('CREATE DATABASE %I OWNER %I ENCODING ''UTF8''', '$DatabaseName', '$DatabaseUser')
WHERE NOT EXISTS (SELECT 1 FROM pg_database WHERE datname = '$DatabaseName');
\gexec
"@

$tempSql = [System.IO.Path]::GetTempFileName()
try {
    # Windows PowerShell 5.1 utf8NoBOM adini desteklemez; psql icin BOM'suz
    # UTF-8 dosyasini .NET ile tutarli bicimde olusturuyoruz.
    [System.IO.File]::WriteAllText($tempSql, $setupSql, (New-Object System.Text.UTF8Encoding($false)))
    Write-Host "PostgreSQL yonetici (postgres) parolasi istenecek." -ForegroundColor Cyan
    Write-Host "Ardindan '$DatabaseUser' uygulama parolasini iki kez girin." -ForegroundColor Cyan
    & $psql -h 127.0.0.1 -p 5432 -U postgres -d postgres -v ON_ERROR_STOP=1 -f $tempSql
    if ($LASTEXITCODE -ne 0) {
        throw "Preprod veritabani hazirlanamadi (psql cikis kodu: $LASTEXITCODE)."
    }
    Write-Host "Hazir: $DatabaseName (sahip: $DatabaseUser)" -ForegroundColor Green
}
finally {
    Remove-Item -LiteralPath $tempSql -Force -ErrorAction SilentlyContinue
}
