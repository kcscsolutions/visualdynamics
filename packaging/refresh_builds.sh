#!/bin/zsh
# Every distributable, rebuilt from the working tree and staged for
# the launch site's preview — so what http://127.0.0.1:8710/downloads.html
# hands out is always the code as it stands (Brandon, 2026-08-31:
# keep the builds updated and in the folder for testing).
#
#     packaging/refresh_builds.sh
#
# The Linux build runs on the media server in the background while the
# two local builds run here in sequence (they share dist/, which each
# build script wipes — staging is cumulative, so each installer is
# staged the moment its build lands). Roughly: macOS ~5 min, Windows
# ~8 min, Linux ~20 min on the server, all told the slowest leg.
set -e
cd "$(dirname "$0")/.."

packaging/build_linux_remote.sh > /tmp/vd-linux-build.log 2>&1 &
linux=$!

./packaging/build_macos.sh
packaging/stage_downloads.py

packaging/build_macos_intel.sh
packaging/stage_downloads.py

packaging/build_windows_wine.sh build
packaging/stage_downloads.py

if wait $linux; then
    packaging/stage_downloads.py
else
    echo 'Linux leg failed — tail /tmp/vd-linux-build.log' >&2
fi

echo '— staged:'
python3 -c "import json; print('\n'.join(
    f\"  {a['name']}  {a['size'] / 2**20:.0f} MB\"
    for a in json.load(open('web/launch/downloads/manifest.json'))['assets']))"
