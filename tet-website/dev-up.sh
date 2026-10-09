#!/usr/bin/env bash
# Sobe o ambiente de desenvolvimento da Opcao B do README: MySQL no Docker,
# migrations, seed e o servidor Flask rodando no venv. Equivalente ao dev-up.ps1.
#
# Faz, em ordem:
#   1. confere os pre-requisitos (Docker rodando, venv e .env criados)
#   2. docker compose up -d --wait db   (espera o healthcheck do MySQL)
#   3. flask db upgrade                 (aplica as migrations)
#   4. flask seed                       (dados de referencia; ignora o que ja existe)
#   5. python index.py                  (http://localhost:5000; Ctrl+C para parar)
#
# Pode ser rodado quantas vezes quiser: o banco ja de pe e reaproveitado, as
# migrations aplicam so o que falta e o seed nao duplica nada.
#
# Pre-requisito: ter rodado `bash setup.sh` uma vez (cria o venv, instala as
# dependencias e o Chromium do Playwright, e cria o .env).
#
# Ao parar o servidor o container do banco continua rodando. Para para-lo:
#     docker compose stop db
# (os dados ficam guardados no volume; `docker compose down -v` apaga tudo.)
#
# Uso:  bash dev-up.sh [--no-server]
#   --no-server   prepara banco, migrations e seed, mas nao inicia o Flask

set -euo pipefail

TET_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(dirname "$TET_DIR")"
cd "$TET_DIR"

NO_SERVER=0
for arg in "$@"; do
  case "$arg" in
    --no-server) NO_SERVER=1 ;;
    -h|--help) sed -n '2,22p' "$0"; exit 0 ;;
    *) echo "Opcao desconhecida: $arg (use --help)" >&2; exit 1 ;;
  esac
done

step() { printf '\n==> %s\n' "$1"; }
die() { printf '\nERRO: %s\n' "$1" >&2; exit 1; }

# --- 1. Pre-requisitos ---------------------------------------------------------

step "Conferindo pre-requisitos"

# venv/bin no Linux/Mac; venv/Scripts so aparece num venv criado no Windows
# (ex.: Git Bash), onde o dev-up.ps1 e o caminho natural.
if [ -x venv/bin/python ]; then
  VENV_PY="venv/bin/python"
elif [ -x venv/Scripts/python.exe ]; then
  VENV_PY="venv/Scripts/python.exe"
else
  die "venv nao encontrado. Rode primeiro: bash setup.sh"
fi
[ -f .env ] || die ".env nao encontrado. Rode primeiro o setup.sh (ele cria o .env a partir do .env.example)."
command -v docker >/dev/null 2>&1 || die "Docker nao encontrado. Instale-o: https://docs.docker.com/engine/install/"
docker info >/dev/null 2>&1 \
  || die "O Docker esta instalado mas nao responde. Inicie o servico (ex.: sudo systemctl start docker, ou abra o Docker Desktop) e confira se seu usuario tem permissao (grupo docker)."
echo "OK: venv, .env e Docker"

# --- 2. Banco --------------------------------------------------------------------

step "Subindo o MySQL (porta 3307) e esperando ele ficar saudavel"
(cd "$REPO_ROOT" && docker compose up -d --wait db) \
  || die "docker compose up -d --wait db falhou. Se a porta 3307 estiver ocupada, pare o outro servico; veja tambem: docker compose logs db"

# --- 3 e 4. Migrations e seed ----------------------------------------------------

export FLASK_APP=index.py

step "Aplicando as migrations (flask db upgrade)"
"$VENV_PY" -m flask db upgrade \
  || die "flask db upgrade falhou. Veja a mensagem acima e a tabela de Troubleshooting do tet-website/README.md (ex.: banco criado com a cadeia antiga de migrations)."

step "Populando os dados de referencia (flask seed)"
"$VENV_PY" -m flask seed || die "flask seed falhou. Veja a mensagem acima."

# --- 5. Servidor -----------------------------------------------------------------

if [ "$NO_SERVER" -eq 1 ]; then
  printf '\nPronto: banco, migrations e seed em dia. Para iniciar o servidor: %s index.py\n' "$VENV_PY"
  exit 0
fi

printf '\nTudo pronto. Iniciando o servidor em http://localhost:5000 (Ctrl+C para parar)\n'
echo "O container do banco continua rodando depois disso; para para-lo: docker compose stop db"
exec "$VENV_PY" index.py
