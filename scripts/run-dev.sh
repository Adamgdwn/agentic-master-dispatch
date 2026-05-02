#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
export PYTHONPATH="${repo_root}/src"
mode="${GOVERNED_AGENT_LAB_MODE:-desktop}"
host="${GOVERNED_AGENT_LAB_HOST:-127.0.0.1}"
port="${GOVERNED_AGENT_LAB_PORT:-8000}"
interpreter="${GOVERNED_AGENT_LAB_PYTHON:-}"

if [[ -z "${interpreter}" ]]; then
  candidates=(
    "${repo_root}/.venv/bin/python"
    "${repo_root}/venv/bin/python"
    "${VIRTUAL_ENV:-}/bin/python"
    "${HOME}/.pyenv/versions/3.12.1/envs/agents-env/bin/python"
    "${HOME}/.pyenv/versions/3.12.1/bin/python"
  )
  for candidate in "${candidates[@]}"; do
    if [[ -n "${candidate}" && -x "${candidate}" ]]; then
      interpreter="${candidate}"
      break
    fi
  done
fi
if [[ -z "${interpreter}" ]]; then
  interpreter="python3"
fi

if ! "${interpreter}" -c "import sys" >/dev/null 2>&1; then
  echo "Unable to start Governed Agent Lab with interpreter: ${interpreter}" >&2
  exit 1
fi

exec "${interpreter}" -m governed_agent_lab --mode "${mode}" --host "${host}" --port "${port}"
