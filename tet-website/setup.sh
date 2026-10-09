#!/usr/bin/env bash
# Prepara o ambiente local do backend (Opcao B do README): venv, dependencias
# Python e o Chromium do Playwright.
#
# O `pip install -r requirements.txt` instala so o pacote Python `playwright`; o
# navegador que ele controla (usado pela coleta do portal na personalizacao de
# cenarios) e um download separado. Este script faz os dois passos.
#
# Pode ser rodado de novo a qualquer momento: reaproveita o venv, o pip so
# instala o que faltar, e o Playwright so baixa o Chromium se a versao instalada
# mudou (ex.: apos atualizar o playwright no requirements.txt).
#
# NAO sobe o banco nem roda migrations/seed - os proximos passos aparecem no final.
#
# Uso:  bash setup.sh [--dev] [--skip-browser] [--with-deps]
#   --dev            instala requirements-dev.txt (inclui pytest)
#   --skip-browser   pula o download do Chromium
#   --with-deps      tambem instala as bibliotecas de sistema do Chromium (apt;
#                    precisa de root/sudo - e o que o Dockerfile faz)

set -euo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

DEV=0
SKIP_BROWSER=0
WITH_DEPS=0
for arg in "$@"; do
  case "$arg" in
    --dev) DEV=1 ;;
    --skip-browser) SKIP_BROWSER=1 ;;
    --with-deps) WITH_DEPS=1 ;;
    -h|--help) sed -n '2,20p' "$0"; exit 0 ;;
    *) echo "Opcao desconhecida: $arg (use --help)" >&2; exit 1 ;;
  esac
done

step() { printf '\n==> %s\n' "$1"; }
die() { printf '\nERRO: %s\n' "$1" >&2; exit 1; }

# --- 1. Python >= 3.10 ---------------------------------------------------------

step "Procurando Python 3.10 ou superior"
PY=""
for candidate in python3 python; do
  if command -v "$candidate" >/dev/null 2>&1 \
     && "$candidate" -c 'import sys; sys.exit(0 if sys.version_info >= (3, 10) else 1)' 2>/dev/null; then
    PY="$candidate"
    break
  fi
done
[ -n "$PY" ] || die "Python 3.10+ nao encontrado. Instale-o (ex.: sudo apt install python3 python3-venv)."
"$PY" --version

# --- 2. venv ---------------------------------------------------------------------

if [ -x venv/bin/python ] || [ -x venv/Scripts/python.exe ]; then
  step "venv ja existe - reaproveitando"
else
  step "Criando o ambiente virtual (venv)"
  "$PY" -m venv venv || die "Nao consegui criar o venv. No Debian/Ubuntu: sudo apt install python3-venv"
fi
# venv/bin no Linux/Mac; venv/Scripts so num venv criado no Windows (ex.: Git Bash).
VENV_PY="venv/bin/python"
[ -x "$VENV_PY" ] || VENV_PY="venv/Scripts/python.exe"

# --- 3. Dependencias Python ------------------------------------------------------

REQUIREMENTS="requirements.txt"
[ "$DEV" -eq 1 ] && REQUIREMENTS="requirements-dev.txt"
step "Instalando dependencias ($REQUIREMENTS)"
"$VENV_PY" -m pip install -r "$REQUIREMENTS" || die "pip install -r $REQUIREMENTS falhou. Veja a mensagem acima."

# --- 4. Chromium do Playwright ---------------------------------------------------

if [ "$SKIP_BROWSER" -eq 1 ]; then
  echo
  echo "(Chromium ignorado por --skip-browser - a coleta do portal nao vai funcionar ate rodar: venv/bin/python -m playwright install chromium)"
else
  step "Instalando o Chromium do Playwright (o download so acontece se ele ainda nao existir)"
  if [ "$WITH_DEPS" -eq 1 ]; then
    "$VENV_PY" -m playwright install --with-deps chromium || die "playwright install --with-deps chromium falhou (precisa de root/sudo)."
  else
    "$VENV_PY" -m playwright install chromium || die "playwright install chromium falhou. Veja a mensagem acima."
    echo "Se a coleta reclamar de bibliotecas faltando (libnss3, libatk...), rode: bash setup.sh --with-deps"
  fi
fi

# --- 5. .env ---------------------------------------------------------------------

if [ -f .env ]; then
  step ".env ja existe - mantido como esta"
elif [ -f .env.example ]; then
  step "Criando .env a partir de .env.example"
  cp .env.example .env
fi

# --- Proximos passos -------------------------------------------------------------

cat <<'EOF'

Pronto. Proximos passos (a partir da raiz do repositorio):

  docker compose up -d db          # MySQL na porta 3307
  cd tet-website
  source venv/bin/activate
  export FLASK_APP=index.py
  flask db upgrade
  flask seed
  python index.py                  # http://localhost:5000
EOF
