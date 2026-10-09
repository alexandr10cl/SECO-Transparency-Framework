<#
.SYNOPSIS
    Prepara o ambiente local do backend (Opcao B do README): venv, dependencias
    Python e o Chromium do Playwright.

.DESCRIPTION
    O `pip install -r requirements.txt` instala so o pacote Python `playwright`;
    o navegador que ele controla (usado pela coleta do portal na personalizacao
    de cenarios) e um download separado. Este script faz os dois passos.

    Pode ser rodado de novo a qualquer momento: reaproveita o venv, o pip so
    instala o que faltar, e o Playwright so baixa o Chromium se a versao
    instalada mudou (ex.: apos atualizar o playwright no requirements.txt).

    NAO sobe o banco nem roda migrations/seed - os proximos passos aparecem no
    final.

.PARAMETER Dev
    Instala requirements-dev.txt (inclui pytest) em vez de requirements.txt.

.PARAMETER SkipBrowser
    Pula o download do Chromium (so se voce nao for usar a coleta do portal).

.EXAMPLE
    powershell -ExecutionPolicy Bypass -File .\setup.ps1
    powershell -ExecutionPolicy Bypass -File .\setup.ps1 -Dev
#>
param(
    [switch]$Dev,
    [switch]$SkipBrowser
)

# Este arquivo e ASCII de proposito: o Windows PowerShell 5.1 le .ps1 sem BOM como
# ANSI, e acentos virariam lixo. Os erros de programas nativos (pip, python) sao
# tratados pelo codigo de saida, nao por excecao.
$ErrorActionPreference = 'Continue'
Set-Location -Path $PSScriptRoot

function Write-Step($message) { Write-Host "`n==> $message" -ForegroundColor Cyan }

function Stop-Setup($message) {
    Write-Host "`nERRO: $message" -ForegroundColor Red
    exit 1
}

# --- 1. Python >= 3.10 ---------------------------------------------------------

Write-Step 'Procurando Python 3.10 ou superior'

$pyExe = $null
$pyArgs = @()
foreach ($candidate in @('py', 'python', 'python3')) {
    if (-not (Get-Command $candidate -ErrorAction SilentlyContinue)) { continue }
    $probe = @()
    if ($candidate -eq 'py') { $probe = @('-3') }
    & $candidate @probe -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>$null
    if ($LASTEXITCODE -eq 0) {
        $pyExe = $candidate
        $pyArgs = $probe
        break
    }
}
if (-not $pyExe) {
    Stop-Setup 'Python 3.10+ nao encontrado. Instale em https://www.python.org/downloads/ e marque "Add python.exe to PATH".'
}
& $pyExe @pyArgs --version

# --- 2. venv ---------------------------------------------------------------------

$venvPython = Join-Path $PSScriptRoot 'venv\Scripts\python.exe'

if (Test-Path $venvPython) {
    Write-Step 'venv ja existe - reaproveitando'
} else {
    Write-Step 'Criando o ambiente virtual (venv)'
    & $pyExe @pyArgs -m venv venv
    if ($LASTEXITCODE -ne 0 -or -not (Test-Path $venvPython)) {
        Stop-Setup 'Nao consegui criar o venv.'
    }
}

# --- 3. Dependencias Python ------------------------------------------------------

$requirements = if ($Dev) { 'requirements-dev.txt' } else { 'requirements.txt' }
Write-Step "Instalando dependencias ($requirements)"
& $venvPython -m pip install -r $requirements
if ($LASTEXITCODE -ne 0) {
    Stop-Setup "pip install -r $requirements falhou. Veja a mensagem acima."
}

# --- 4. Chromium do Playwright ---------------------------------------------------

if ($SkipBrowser) {
    Write-Host "`n(Chromium ignorado por -SkipBrowser - a coleta do portal nao vai funcionar ate rodar: venv\Scripts\python -m playwright install chromium)" -ForegroundColor Yellow
} else {
    Write-Step 'Instalando o Chromium do Playwright (o download so acontece se ele ainda nao existir)'
    & $venvPython -m playwright install chromium
    if ($LASTEXITCODE -ne 0) {
        Stop-Setup 'playwright install chromium falhou. Veja a mensagem acima.'
    }
}

# --- 5. .env ---------------------------------------------------------------------

if (Test-Path '.env') {
    Write-Step '.env ja existe - mantido como esta'
} elseif (Test-Path '.env.example') {
    Write-Step 'Criando .env a partir de .env.example'
    Copy-Item '.env.example' '.env'
}

# --- Proximos passos -------------------------------------------------------------

Write-Host "`nPronto. Proximos passos (a partir da raiz do repositorio):" -ForegroundColor Green
Write-Host @'

  docker compose up -d db          # MySQL na porta 3307
  cd tet-website
  venv\Scripts\activate
  flask --app index.py db upgrade
  flask --app index.py seed
  python index.py                  # http://localhost:5000
  (ou: powershell -ExecutionPolicy Bypass -File .\dev-up.ps1  - faz tudo isso de uma vez)
'@
