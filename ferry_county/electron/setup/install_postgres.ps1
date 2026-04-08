# Run as Administrator once per machine (Steve / IT).
# Installs PostgreSQL silently, creates ferry_county DB user/db, enables PostGIS.
#
# SECURITY: Edit $superPassword and $ferryPassword before deployment. Do not commit real secrets.

$ErrorActionPreference = "Stop"

$pgVersion = "16.2"
$pgInstaller = "postgresql-$pgVersion-1-windows-x64.exe"
$pgUrl = "https://get.enterprisedb.com/postgresql/$pgInstaller"

$superPassword = "ChangeThisSuperuserPassword!"
$ferryPassword = "ChangeThisFerryAppPassword!"

Write-Host "Downloading PostgreSQL $pgVersion..."
Invoke-WebRequest -Uri $pgUrl -OutFile $pgInstaller

Write-Host "Installing PostgreSQL (unattended)..."
$p = Start-Process -FilePath ".\$pgInstaller" -ArgumentList @(
    "--mode", "unattended",
    "--superpassword", $superPassword,
    "--servicename", "postgresql-16",
    "--servicepassword", $superPassword,
    "--serverport", "5432",
    "--datadir", "C:\PostgreSQL\16\data"
) -Wait -PassThru
if ($p.ExitCode -ne 0) {
    throw "PostgreSQL installer exit code $($p.ExitCode)"
}

$psql = "C:\Program Files\PostgreSQL\16\bin\psql.exe"
if (-not (Test-Path $psql)) {
    throw "psql not found at $psql — adjust path to match your PostgreSQL install."
}

$env:PGPASSWORD = $superPassword
Write-Host "Creating application role and database..."
& $psql -U postgres -v ON_ERROR_STOP=1 -c "CREATE USER ferry WITH PASSWORD '$ferryPassword';"
& $psql -U postgres -v ON_ERROR_STOP=1 -c "CREATE DATABASE ferry_county OWNER ferry;"
& $psql -U postgres -v ON_ERROR_STOP=1 -c "GRANT ALL PRIVILEGES ON DATABASE ferry_county TO ferry;"
& $psql -U postgres -d ferry_county -v ON_ERROR_STOP=1 -c "CREATE EXTENSION IF NOT EXISTS postgis;"

Remove-Item Env:PGPASSWORD

Write-Host ""
Write-Host "Done. Use this URL in the Field System first-run wizard (password is the ferry user password):"
Write-Host ("postgresql+psycopg2://ferry:{0}@127.0.0.1:5432/ferry_county" -f [uri]::EscapeDataString($ferryPassword))
