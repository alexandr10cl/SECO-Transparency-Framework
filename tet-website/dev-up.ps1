<#
.SYNOPSIS
    Sobe o ambiente de desenvolvimento da Opcao B do README: MySQL no Docker,
    migrations, seed e o servidor Flask rodando no venv.

.DESCRIPTION
    Faz, em ordem:
      1. confere os pre-requisitos (Docker rodando, venv e .env criados)
      2. docker compose up -d --wait db   (espera o healthcheck do MySQL)
      3. flask db upgrade                 (aplica as migrations)
      4. flask seed                       (dados de referencia; ignora o que ja existe)
      5. python index.py                  (http://localhost:5000; Ctrl+C para parar)

    Pode ser rodado quantas vezes quiser: o banco ja de pe e reaproveitado, as
    migrations aplicam so o que falta e o seed nao duplica nada.

    Pre-requisito: ter rodado setup.ps1 uma vez (cria o venv, instala as
    dependencias e o Chromium do Playwright, e cria o .env).

    Ao parar o servidor o container do banco continua rodando. Para para-lo:
        docker compose stop db
    (os dados ficam guardados no volume; `docker compose down -v` apaga tudo.)

.PARAMETER NoServer
    Prepara banco, migrations e seed, mas nao inicia o servidor Flask.

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\dev-up.ps1
    powershell -ExecutionPolicy Bypass -File .\dev-up.ps1 -NoServer
#>
param(
    [switch]$NoServer
)

# ASCII de proposito (o Windows PowerShell 5.1 le .ps1 sem BOM como ANSI). Erros de
# programas nativos sao tratados pelo codigo de saida, nao por excecao.
$ErrorActionPreference = 'Continue'

$tetDir = $PSScriptRoot
$repoRoot = Split-Path -Parent $PSScriptRoot
$venvPython = Join-Path $tetDir 'venv\Scripts\python.exe'

function Write-Step($message) { Write-Host "`n==> $message" -ForegroundColor Cyan }

function Stop-DevUp($message) {
    Write-Host "`nERRO: $message" -ForegroundColor Red
    exit 1
}

# --- 1. Pre-requisitos ---------------------------------------------------------

Write-Step 'Conferindo pre-requisitos'

if (-not (Test-Path $venvPython)) {
    Stop-DevUp 'venv nao encontrado. Rode primeiro: powershell -ExecutionPolicy Bypass -File .\setup.ps1'
}
if (-not (Test-Path (Join-Path $tetDir '.env'))) {
    Stop-DevUp '.env nao encontrado. Rode primeiro o setup.ps1 (ele cria o .env a partir do .env.example).'
}
if (-not (Get-Command docker -ErrorAction SilentlyContinue)) {
    Stop-DevUp 'Docker nao encontrado. Instale o Docker Desktop: https://www.docker.com/products/docker-desktop/'
}
docker info *> $null
if ($LASTEXITCODE -ne 0) {
    Stop-DevUp 'O Docker esta instalado mas nao esta rodando. Abra o Docker Desktop, espere ele iniciar e rode de novo.'
}
Write-Host 'OK: venv, .env e Docker'

# --- 2. Banco --------------------------------------------------------------------

Write-Step 'Subindo o MySQL (porta 3307) e esperando ele ficar saudavel'
Push-Location $repoRoot
docker compose up -d --wait db
$composeExit = $LASTEXITCODE
Pop-Location
if ($composeExit -ne 0) {
    Stop-DevUp 'docker compose up -d --wait db falhou. Se a porta 3307 estiver ocupada, pare o outro servico; veja tambem: docker compose logs db'
}

# --- 3 e 4. Migrations e seed ----------------------------------------------------

Set-Location $tetDir

Write-Step 'Aplicando as migrations (flask db upgrade)'
& $venvPython -m flask --app index.py db upgrade
if ($LASTEXITCODE -ne 0) {
    Stop-DevUp "flask db upgrade falhou. Veja a mensagem acima e a tabela de Troubleshooting do tet-website/README.md (ex.: banco criado com a cadeia antiga de migrations)."
}

Write-Step 'Populando os dados de referencia (flask seed)'
& $venvPython -m flask --app index.py seed
if ($LASTEXITCODE -ne 0) {
    Stop-DevUp 'flask seed falhou. Veja a mensagem acima.'
}

# --- 5. Servidor -----------------------------------------------------------------

if ($NoServer) {
    Write-Host "`nPronto: banco, migrations e seed em dia. Para iniciar o servidor: venv\Scripts\python index.py" -ForegroundColor Green
    exit 0
}

Write-Host "`nTudo pronto. Iniciando o servidor em http://localhost:5000 (Ctrl+C para parar)" -ForegroundColor Green
Write-Host 'O container do banco continua rodando depois disso; para para-lo: docker compose stop db' -ForegroundColor DarkGray
& $venvPython index.py
