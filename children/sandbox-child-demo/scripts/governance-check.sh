#!/usr/bin/env bash

set -euo pipefail

if [[ $# -ne 1 ]]; then
  echo "Usage: $0 /path/to/project"
  exit 1
fi

project_path="$1"
errors=0
warnings=0

pass() {
  echo "PASS: $1"
}

warn() {
  echo "WARN: $1"
  warnings=$((warnings + 1))
}

fail() {
  echo "FAIL: $1"
  errors=$((errors + 1))
}

require_file() {
  local rel_path="$1"
  if [[ -f "${project_path}/${rel_path}" ]]; then
    pass "Found ${rel_path}"
  else
    fail "Missing required file ${rel_path}"
  fi
}

require_file "README.md"
require_file "project-control.yaml"
require_file "docs/architecture.md"
require_file "docs/risks/risk-register.md"
require_file "docs/agent-inventory.md"
require_file "docs/model-registry.md"
require_file "docs/prompt-register.md"
require_file "docs/tool-permission-matrix.md"
require_file "docs/evaluation-approach.md"
require_file "docs/human-oversight-rules.md"
require_file "docs/deployment-guide.md"
require_file "docs/runbook.md"
require_file "AGENTS.md"

if [[ ${errors} -gt 0 ]]; then
  echo
  echo "Governance check failed with ${errors} error(s) and ${warnings} warning(s)."
  exit 1
fi

echo
echo "Governance check passed with ${warnings} warning(s)."
