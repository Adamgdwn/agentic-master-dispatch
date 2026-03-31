#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${repo_root}/src"
mode="${GOVERNED_AGENT_LAB_MODE:-desktop}"
host="${GOVERNED_AGENT_LAB_HOST:-127.0.0.1}"
port="${GOVERNED_AGENT_LAB_PORT:-8000}"
interpreter="${GOVERNED_AGENT_LAB_PYTHON:-}"

if [[ -z "${interpreter}" && -x "${HOME}/.pyenv/versions/3.12.1/bin/python" ]]; then
  interpreter="${HOME}/.pyenv/versions/3.12.1/bin/python"
fi
if [[ -z "${interpreter}" ]]; then
  interpreter="python3"
fi

exec "${interpreter}" -m governed_agent_lab --mode "${mode}" --host "${host}" --port "${port}"
