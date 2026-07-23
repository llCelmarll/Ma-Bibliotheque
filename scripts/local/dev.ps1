#!/usr/bin/env pwsh
param()

$Root = Split-Path (Split-Path (Split-Path $MyInvocation.MyCommand.Path -Parent) -Parent) -Parent

$PidFile = Join-Path $Root ".dev-pids"

function Start-ServiceWindow {
    param(
        [string]$Title,
        [string]$WorkDir,
        [string]$Command
    )
    $p = Start-Process powershell -ArgumentList "-NoExit", "-Command", "
        `$host.UI.RawUI.WindowTitle = '$Title'
        Set-Location '$WorkDir'
        $Command
    " -PassThru
    Add-Content $PidFile $p.Id
}

Write-Host ""
Write-Host "Demarrage de l'environnement de developpement..." -ForegroundColor Cyan
Write-Host ""

# Reinitialiser le fichier de PIDs
if (Test-Path $PidFile) { Remove-Item $PidFile }

# --- PostgreSQL via Docker ---
Write-Host "[1/4] PostgreSQL (Docker)..." -ForegroundColor Yellow
Set-Location $Root

# Verifier si Docker est actif, sinon lancer Docker Desktop
docker info 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "      Docker Desktop non actif, demarrage en cours..." -ForegroundColor Yellow
    Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"
    Write-Host "      Attente du daemon Docker..." -ForegroundColor Yellow
    $timeout = 60
    $elapsed = 0
    do {
        Start-Sleep -Seconds 3
        $elapsed += 3
        docker info 2>$null | Out-Null
    } while ($LASTEXITCODE -ne 0 -and $elapsed -lt $timeout)
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Erreur : Docker Desktop n'a pas demarre apres ${timeout}s." -ForegroundColor Red
        exit 1
    }
    Write-Host "      Docker Desktop demarre." -ForegroundColor Green
}

# Ouvrir l'UI Docker Desktop
Start-Process "C:\Program Files\Docker\Docker\Docker Desktop.exe"

$pgRunning = docker ps --filter "name=bibliotheque_postgres" --filter "status=running" -q 2>$null
if ($pgRunning) {
    Write-Host "      PostgreSQL deja en cours d'execution." -ForegroundColor Green
} else {
    docker compose up -d postgres
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Erreur : impossible de demarrer PostgreSQL." -ForegroundColor Red
        exit 1
    }
}
Write-Host "      PostgreSQL demarre." -ForegroundColor Green

# --- Backend FastAPI (venv natif) ---
Write-Host "[2/4] Backend FastAPI..." -ForegroundColor Yellow
$BackendDir = Join-Path $Root "backend"
$VenvActivate = Join-Path $Root ".venv\Scripts\Activate.ps1"

$BackendCmd = "
    & '$VenvActivate'
    Get-Content .env | ForEach-Object {
        if (`$_ -match '^\s*([^#][^=]+)=(.*)$') {
            [Environment]::SetEnvironmentVariable(`$matches[1].Trim(), `$matches[2].Trim(), 'Process')
        }
    }
    python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
"
Start-ServiceWindow -Title "Backend :8000" -WorkDir $BackendDir -Command $BackendCmd
Write-Host "      Fenetre Backend ouverte." -ForegroundColor Green

# --- Frontend Expo Web ---
Write-Host "[3/4] Frontend Expo Web..." -ForegroundColor Yellow
$FrontendDir = Join-Path $Root "frontend"
Start-ServiceWindow -Title "Frontend :8081" -WorkDir $FrontendDir -Command "`$env:BROWSER='none'; npx expo start --web"
Write-Host "      Fenetre Frontend ouverte." -ForegroundColor Green

# --- Mobile (telephone physique via USB) ---
$devices = adb devices 2>$null | Select-String "device$"
if ($devices) {
    Write-Host "      Telephone detecte en USB, configuration adb reverse..." -ForegroundColor Yellow
    Write-Host "      Attente du demarrage de Metro..." -ForegroundColor DarkGray
    $metroTimeout = 60
    $metroElapsed = 0
    $metroOk = $false
    while (-not $metroOk -and $metroElapsed -lt $metroTimeout) {
        Start-Sleep -Seconds 2
        $metroElapsed += 2
        try { $metroResp = Invoke-WebRequest -Uri "http://127.0.0.1:8081/status" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue; $metroOk = $metroResp.StatusCode -eq 200 } catch { $metroOk = $false }
    }
    if ($metroOk) {
        adb reverse tcp:8081 tcp:8081
        adb reverse tcp:8000 tcp:8000
        Write-Host "      Ports 8081 et 8000 forwardes via USB." -ForegroundColor Green
        adb shell am start -a android.intent.action.VIEW -d "exp://localhost:8081" host.exp.exponent | Out-Null
        Write-Host "      Expo Go ouvert sur le telephone." -ForegroundColor Green
    } else {
        Write-Host "      Metro non pret apres ${metroTimeout}s, adb reverse ignore." -ForegroundColor Red
    }
} else {
    Write-Host "      Aucun telephone detecte en USB, etape mobile ignoree." -ForegroundColor DarkGray
}

# --- Frontend Admin Vite ---
Write-Host "[4/4] Frontend Admin Vite..." -ForegroundColor Yellow
$AdminDir = Join-Path $Root "frontend-admin"
if (Test-Path (Join-Path $AdminDir "package.json")) {
    Start-ServiceWindow -Title "Admin :3001" -WorkDir $AdminDir -Command "npm run dev"
    Write-Host "      Fenetre Admin ouverte." -ForegroundColor Green
} else {
    Write-Host "      frontend-admin introuvable, ignore." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "Tous les services sont demarres :" -ForegroundColor Cyan
Write-Host "  API      http://localhost:8000" -ForegroundColor White
Write-Host "  Frontend http://localhost:8081" -ForegroundColor White
Write-Host "  Admin    http://localhost:3001" -ForegroundColor White
Write-Host ""
Write-Host "Pour arreter : .\run.ps1 stop" -ForegroundColor Gray

# Attendre que le backend (/docs) et le frontend soient prets puis ouvrir Chrome
Write-Host "Attente du demarrage des services..." -ForegroundColor Yellow
$timeout = 120
$elapsed = 0
$backOk = $false
$frontOk = $false
while ((-not $backOk -or -not $frontOk) -and $elapsed -lt $timeout) {
    Start-Sleep -Seconds 2
    $elapsed += 2
    try { $backResp = Invoke-WebRequest -Uri "http://127.0.0.1:8000/health" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue; $backOk = $backResp.StatusCode -eq 200 } catch { $backOk = $false }
    try { $frontResp = Invoke-WebRequest -Uri "http://127.0.0.1:8081" -TimeoutSec 2 -UseBasicParsing -ErrorAction SilentlyContinue; $frontOk = $frontResp.StatusCode -eq 200 } catch { $frontOk = $false }
    Write-Host "  [${elapsed}s] backend=$backOk frontend=$frontOk" -ForegroundColor DarkGray
}

$ChromePath = "C:\Program Files\Google\Chrome\Application\chrome.exe"
Start-Process $ChromePath -ArgumentList "--new-window http://localhost:8081 http://localhost:8000/docs http://localhost:3001"
Write-Host "Chrome ouvert." -ForegroundColor Green