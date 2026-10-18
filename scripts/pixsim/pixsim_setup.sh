#!/usr/bin/env bash
# Clona o PixSim (terceiro) numa versao fixa e cria um venv proprio; nunca toca o .venv do projeto.
set -euo pipefail

PIXSIM_SHA=7fdfc90013960f46df60c3ea01838e768e7a420a
ROOT="$(cd "$(dirname "$0")/../.." && pwd)/scripts/out/pixsim"
mkdir -p "$ROOT"

if [ ! -d "$ROOT/src/.git" ]; then
  git clone -q https://github.com/BashirZeimarani/pixsim_public "$ROOT/src"
fi
git -C "$ROOT/src" checkout -q "$PIXSIM_SHA"

if [ ! -x "$ROOT/.venv/bin/python" ]; then
  uv venv -q -p 3.13 "$ROOT/.venv"
  uv pip install -q -p "$ROOT/.venv/bin/python" -r "$ROOT/src/requirements.txt"
fi
echo "pixsim pronto: $PIXSIM_SHA"
