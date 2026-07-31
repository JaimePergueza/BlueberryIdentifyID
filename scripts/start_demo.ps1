param(
    [string]$EnvFile = ".env.docker"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path $EnvFile)) {
    throw "Environment file '$EnvFile' does not exist. Copy .env.docker.example and replace CHANGE_ME values."
}

Write-Host "Building and starting BlueberryMicroID..."
docker compose --env-file $EnvFile up -d --build postgres redis migrate api worker frontend
if ($LASTEXITCODE -ne 0) { throw "Docker Compose startup failed." }

$portLine = Get-Content $EnvFile | Where-Object { $_ -match '^APP_PORT=' } | Select-Object -First 1
$port = if ($portLine) { ($portLine -split '=', 2)[1].Trim() } else { "8080" }
$healthUrl = "http://127.0.0.1:$port/health"

Write-Host "Waiting for $healthUrl ..."
$healthy = $false
for ($attempt = 1; $attempt -le 60; $attempt++) {
    try {
        $health = Invoke-RestMethod -Uri $healthUrl -TimeoutSec 3
        if ($health.status -eq "ok") {
            $healthy = $true
            break
        }
    } catch {
        Start-Sleep -Seconds 2
    }
}
if (-not $healthy) {
    docker compose --env-file $EnvFile logs --tail=200
    throw "The public application did not become healthy."
}

Write-Host "Creating idempotent synthetic demonstration data..."
docker compose --env-file $EnvFile --profile demo run --rm demo-seed
if ($LASTEXITCODE -ne 0) { throw "Demo seed failed." }

Write-Host "Running full-stack smoke test..."
docker compose --env-file $EnvFile --profile demo run --rm demo-smoke
if ($LASTEXITCODE -ne 0) { throw "Full-stack smoke failed." }

Write-Host ""
Write-Host "BlueberryMicroID is ready at http://127.0.0.1:$port"
Write-Host "Use the demo credentials configured in $EnvFile."
