<#
.SYNOPSIS
  Run the full FlightMind app with upload on this Windows PC, behind a Cloudflare quick tunnel (SCRUM-65).

.DESCRIPTION
  1. Checks Docker, cloudflared, Cygwin, the asterix decoder, Python and npm.
  2. Starts the compose database and waits for pg_isready.
  3. Adds the uploads and quarantine tables if the database is older than contract 1.2.
  4. Builds web/ with a same-origin API base.
  5. Starts the real API (uvicorn serve:app, one process) on -Port.
  6. Starts "cloudflared tunnel --url http://127.0.0.1:<Port>" and prints the public URL.
  Ctrl+C stops uvicorn and cloudflared. The database keeps running (docker compose -f infra/docker-compose.yml stop).

.EXAMPLE
  .\scripts\run-upload-demo.ps1 -AsterixDir E:\asterix -CygwinBin C:\cygwin64\bin

.EXAMPLE
  .\scripts\run-upload-demo.ps1 -NoTunnel -SkipBuild   # local only, reuse the last web build

.EXAMPLE
  .\scripts\run-upload-demo.ps1 -DbPort 55432   # another Postgres already uses 5432
#>
param(
    [string]$AsterixDir = $env:FLIGHTMIND_ASTERIX_DIR,
    [string]$CygwinBin = $(if ($env:FLIGHTMIND_CYGWIN_BIN) { $env:FLIGHTMIND_CYGWIN_BIN } else { 'C:\cygwin64\bin' }),
    [string]$Python = '',
    [int]$Port = 8000,
    [int]$DbPort = $(if ($env:FLIGHTMIND_DB_PORT) { [int]$env:FLIGHTMIND_DB_PORT } else { 5432 }),
    [string]$DefaultRecording = $env:FLIGHTMIND_DEFAULT_RECORDING,
    # Outside the repo by default: a repo in OneDrive would sync, and may lock, every upload.
    [string]$UploadDir = $(if ($env:FLIGHTMIND_UPLOAD_DIR) { $env:FLIGHTMIND_UPLOAD_DIR } else { Join-Path $env:LOCALAPPDATA 'flightmind\uploads' }),
    [switch]$SkipBuild,
    [switch]$NoTunnel
)

# Continue, not Stop: docker, npm and cloudflared write progress to stderr, which Stop would
# turn into a fatal error once the output is redirected. Every step checks its own result.
$ErrorActionPreference = 'Continue'
$Root = Split-Path -Parent $PSScriptRoot
$Intel = Join-Path $Root 'services\intel'
$Web = Join-Path $Root 'web'
$Logs = Join-Path $Root 'data\logs'
$Compose = Join-Path $Root 'infra\docker-compose.yml'
$Db = 'flightmind-db'
$Dsn = "postgresql://flightmind:flightmind@localhost:$DbPort/flightmind"
$OutputEncoding = New-Object System.Text.UTF8Encoding $false  # SQL piped to psql

function Stop-Demo([string]$Message) {
    Write-Host ''
    Write-Host "run-upload-demo: $Message" -ForegroundColor Red
    exit 1
}

function Write-Step([string]$Message) {
    Write-Host "run-upload-demo: $Message" -ForegroundColor Cyan
}

# ---------- 1. prerequisites ----------

if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Stop-Demo 'Docker was not found on PATH. Install Docker Desktop and start it.'
}
docker info --format '{{.ServerVersion}}' *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-Demo 'Docker is installed but not running. Start Docker Desktop, wait for "Engine running", then retry.'
}
$Cloudflared = $null
if (-not $NoTunnel) {
    $Cloudflared = Get-Command cloudflared -ErrorAction SilentlyContinue
    if (-not $Cloudflared) {
        Stop-Demo 'cloudflared was not found on PATH. Install it (winget install --id Cloudflare.cloudflared), open a new terminal, then retry. Or pass -NoTunnel to run locally only.'
    }
}
if (-not (Test-Path (Join-Path $CygwinBin 'bash.exe'))) {
    Stop-Demo "Cygwin was not found: '$CygwinBin\bash.exe' does not exist. Install Cygwin, or pass -CygwinBin <folder with bash.exe>."
}
if (-not $AsterixDir) {
    Stop-Demo 'The asterix decoder folder is not set. Pass -AsterixDir <folder with asterix.exe> or set FLIGHTMIND_ASTERIX_DIR.'
}
foreach ($need in 'asterix.exe', 'config\asterix.ini') {
    if (-not (Test-Path (Join-Path $AsterixDir $need))) {
        Stop-Demo "The asterix decoder folder '$AsterixDir' has no $need. Pass -AsterixDir <folder with asterix.exe and config\asterix.ini>."
    }
}

if (-not $Python) {
    $venv = Join-Path $Intel '.venv\Scripts\python.exe'
    $Python = if (Test-Path $venv) { $venv } else { 'python' }
}
& $Python -c "import fastapi, uvicorn, psycopg, flightmind_pipeline" *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-Demo ("'$Python' cannot import the API and the pipeline. Use Python 3.12, then run:`n" +
        "  $Python -m pip install -r services\intel\requirements.txt -e services\pipeline`n" +
        "or pass -Python <path to python.exe>.")
}
& $Python -c "import flightmind_pipeline; flightmind_pipeline.run_recording" *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-Demo 'The pipeline has no run_recording yet, so uploads cannot be processed. Merge SCRUM-63 (the pipeline entry point), then retry.'
}
if (-not $SkipBuild -and -not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Stop-Demo 'npm was not found on PATH. Install Node.js 22, or pass -SkipBuild to reuse web\dist.'
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    Stop-Demo "Port $Port is already in use. Stop that program, or pass -Port <free port>."
}

# ---------- 2. database ----------

Write-Step "starting the database on port $DbPort (docker compose)"
$env:FLIGHTMIND_DB_PORT = "$DbPort"
docker compose -f $Compose up -d
if ($LASTEXITCODE -ne 0) {
    Stop-Demo "docker compose up failed (see above). If port $DbPort is taken by another Postgres, pass -DbPort <free port> (for example -DbPort 55432)."
}
$ready = $false
foreach ($i in 1..60) {
    docker exec $Db pg_isready -U flightmind -d flightmind *> $null
    if ($LASTEXITCODE -eq 0) { $ready = $true; break }
    Start-Sleep -Seconds 1
}
if (-not $ready) { Stop-Demo "The database did not become ready in 60 s. See: docker logs $Db" }

function Invoke-Sql([string]$Sql) {
    $out = $Sql | docker exec -i $Db psql -v ON_ERROR_STOP=1 -U flightmind -d flightmind -tA
    if ($LASTEXITCODE -ne 0) { Stop-Demo "psql failed on: $Sql" }
    return $out
}

# A database made before contract 1.2 lacks the upload tables. Add only those
# statements from contracts/schema.sql; the rest of the schema is not run again.
$schema = (Get-Content -Raw -ErrorAction Stop (Join-Path $Root 'contracts\schema.sql')) -replace '--[^\r\n]*', ''  # comments may hold ';'
foreach ($table in 'uploads', 'quarantine') {
    if ((Invoke-Sql "SELECT to_regclass('public.$table') IS NOT NULL;").Trim() -eq 't') { continue }
    $statements = foreach ($chunk in $schema -split ';') {
        $m = [regex]::Match($chunk, "CREATE\s+(TABLE\s+$table\s*\(|(UNIQUE\s+)?INDEX\s+\w+\s+ON\s+$table\b)[\s\S]*")
        if ($m.Success) { $m.Value.Trim() + ';' }
    }
    if (-not $statements) { Stop-Demo "contracts\schema.sql has no CREATE TABLE $table." }
    Write-Step "adding the $table table (database older than contract 1.2)"
    Invoke-Sql ($statements -join "`n") | Out-Null
}

# ---------- 3. web UI ----------

if ($SkipBuild) {
    if (-not (Test-Path (Join-Path $Web 'dist\index.html'))) { Stop-Demo 'web\dist\index.html does not exist; run once without -SkipBuild.' }
} else {
    Write-Step 'building the web UI'
    # The web client has no same-origin mode yet; "/." makes "/./api/meta" become "/api/meta"
    # on whatever host serves the page (the same workaround as infra/vercel_build.py).
    $env:VITE_API_BASE = '/.'
    Push-Location $Web
    try {
        if (-not (Test-Path 'node_modules')) {
            npm ci
            if ($LASTEXITCODE -ne 0) { Stop-Demo 'npm ci failed (see above).' }
        }
        npm run build
        if ($LASTEXITCODE -ne 0) { Stop-Demo 'npm run build failed (see above).' }
    } finally {
        Pop-Location
        Remove-Item Env:VITE_API_BASE -ErrorAction SilentlyContinue
    }
}

# ---------- 4. API and tunnel ----------

New-Item -ItemType Directory -Force -ErrorAction Stop $Logs, $UploadDir | Out-Null
$env:FLIGHTMIND_API_APP = 'real_api.app:app'
$env:FLIGHTMIND_DSN = $Dsn
$env:FLIGHTMIND_WEB_DIST = Join-Path $Web 'dist'
$env:FLIGHTMIND_UPLOAD_DIR = $UploadDir
$env:FLIGHTMIND_ASTERIX_DIR = $AsterixDir
$env:FLIGHTMIND_CYGWIN_BIN = $CygwinBin
if ($DefaultRecording) { $env:FLIGHTMIND_DEFAULT_RECORDING = $DefaultRecording }

$api = $null
$tunnel = $null
try {
    Write-Step "starting the real API on http://127.0.0.1:$Port (log: data\logs\api.log)"
    # One process only: the upload worker runs inside it (see services/intel/README.md).
    $api = Start-Process -ErrorAction Stop -FilePath $Python -WorkingDirectory $Intel -PassThru -NoNewWindow `
        -ArgumentList '-m', 'uvicorn', 'serve:app', '--host', '127.0.0.1', '--port', "$Port" `
        -RedirectStandardOutput (Join-Path $Logs 'api.out.log') -RedirectStandardError (Join-Path $Logs 'api.log')
    $up = $false
    foreach ($i in 1..60) {
        if ($api.HasExited) { break }
        try {
            Invoke-WebRequest -ErrorAction Stop -UseBasicParsing -TimeoutSec 2 "http://127.0.0.1:$Port/api/meta" | Out-Null
            $up = $true; break
        } catch { Start-Sleep -Seconds 1 }
    }
    if (-not $up) {
        Get-Content (Join-Path $Logs 'api.log') -Tail 20 -ErrorAction SilentlyContinue
        Stop-Demo 'The API did not answer /api/meta in 60 s (its log is above).'
    }

    $public = "http://127.0.0.1:$Port"
    if (-not $NoTunnel) {
        Write-Step 'starting the Cloudflare quick tunnel (log: data\logs\tunnel.log)'
        $tunnelLog = Join-Path $Logs 'tunnel.log'
        Remove-Item $tunnelLog -ErrorAction SilentlyContinue
        $tunnel = Start-Process -ErrorAction Stop -FilePath $Cloudflared.Source -PassThru -NoNewWindow `
            -ArgumentList 'tunnel', '--no-autoupdate', '--url', "http://127.0.0.1:$Port" `
            -RedirectStandardOutput (Join-Path $Logs 'tunnel.out.log') -RedirectStandardError $tunnelLog
        $public = $null
        foreach ($i in 1..60) {
            if ($tunnel.HasExited) { break }
            # Not api.trycloudflare.com, which the log names when cloudflared cannot get a tunnel.
            $hit = Select-String -Path $tunnelLog -Pattern 'https://(?!api\.)[a-z0-9-]+\.trycloudflare\.com' -ErrorAction SilentlyContinue | Select-Object -First 1
            if ($hit) { $public = $hit.Matches[0].Value; break }
            Start-Sleep -Seconds 1
        }
        if (-not $public) {
            Get-Content $tunnelLog -Tail 20 -ErrorAction SilentlyContinue
            Stop-Demo 'cloudflared printed no trycloudflare.com URL in 60 s (its log is above).'
        }
    }

    Write-Host ''
    Write-Host "  FlightMind is running: $public" -ForegroundColor Green
    if ($DefaultRecording) {
        Write-Host "  The app opens recording '$DefaultRecording' by default."
        Write-Host "  Check it:  python infra\smoke.py $public --upload"
    } else {
        Write-Host '  No -DefaultRecording: the app opens the recording ingested last, so every upload' -ForegroundColor Yellow
        Write-Host '  (smoke.py --upload too) changes what everyone sees. For a demo, upload the demo' -ForegroundColor Yellow
        Write-Host '  recording, then restart this script with -DefaultRecording <its id>.' -ForegroundColor Yellow
        Write-Host "  Check it:  python infra\smoke.py $public"
    }
    if (-not $NoTunnel) {
        Write-Host '  Anyone with this URL can upload. Stop the script when you are not demoing.'
    }
    Write-Host '  Press Ctrl+C to stop the API and the tunnel.'
    Write-Host ''
    while (-not $api.HasExited -and ($NoTunnel -or -not $tunnel.HasExited)) { Start-Sleep -Seconds 1 }
    if ($api.HasExited) { Stop-Demo 'The API stopped (see data\logs\api.log).' }
    Stop-Demo 'cloudflared stopped (see data\logs\tunnel.log).'
} finally {
    foreach ($p in $tunnel, $api) {
        if ($p -and -not $p.HasExited) { Stop-Process -Id $p.Id -Force -ErrorAction SilentlyContinue }
    }
    Write-Host 'run-upload-demo: stopped the API and the tunnel. The database is still running.'
}
