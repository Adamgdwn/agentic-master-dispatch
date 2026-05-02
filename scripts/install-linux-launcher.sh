#!/usr/bin/env bash

set -euo pipefail

repo_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
launcher_path="${repo_root}/GovernedAgentLab.sh"
icon_path="${repo_root}/web/icon.svg"
desktop_dir="${XDG_DATA_HOME:-${HOME}/.local/share}/applications"
desktop_file="${desktop_dir}/governed-agent-lab.desktop"

mkdir -p "${desktop_dir}"
chmod +x "${launcher_path}"

cat > "${desktop_file}" <<EOF
[Desktop Entry]
Version=1.0
Type=Application
Name=Governed Agent Lab
Comment=Governed sandbox mission console
Exec=${launcher_path}
Path=${repo_root}
Icon=${icon_path}
Terminal=false
Categories=Development;Utility;
StartupNotify=true
EOF

if command -v update-desktop-database >/dev/null 2>&1; then
  update-desktop-database "${desktop_dir}" >/dev/null 2>&1 || true
fi

echo "Installed Linux launcher:"
echo "  ${desktop_file}"
echo
echo "You can now launch Governed Agent Lab from your application menu or by running:"
echo "  ${launcher_path}"
