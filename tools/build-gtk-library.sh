#!/bin/bash
# SPDX-License-Identifier: MIT
# Native ARM64 Debian13 build. No installation and no system-library replacement.
# Dependencies (install separately): build-essential meson ninja-build pkg-config dpkg-dev
# libglib2.0-dev libcairo2-dev libpango1.0-dev libatk1.0-dev libgdk-pixbuf-2.0-dev
# libwayland-dev wayland-protocols libxkbcommon-dev libepoxy-dev libx11-dev
# libxext-dev libxrender-dev libxrandr-dev libxi-dev libxcursor-dev libxfixes-dev
# libxcomposite-dev libxdamage-dev libxinerama-dev libfribidi-dev libatk-bridge2.0-dev
set -euo pipefail
[[ $# == 1 ]] || { echo 'Usage: build-gtk-library.sh /path/to/new-build-directory' >&2; exit 2; }
[[ $(dpkg --print-architecture) == arm64 ]]
[[ $(dpkg-query -W -f='${Version}' libgtk-3-0t64) == 3.24.49-3 ]] || { echo 'This recipe is pinned to GTK 3.24.49-3' >&2; exit 1; }
repo=$(cd -- "$(dirname -- "$0")/.." && pwd)
[[ ! -e "$1" ]] || { echo 'Choose a new build directory' >&2; exit 1; }
mkdir -p "$1"
cd "$1"
python3 - "$repo" <<'PY'
import hashlib
import pathlib
import sys
import urllib.request
repo = pathlib.Path(sys.argv[1])
entries = {
    'gtk+3.0_3.24.49.orig.tar.xz': '5ea52c6a28f0e5ecf2e9a3c2facbb30d040b73871fcd5f33cd1317e9018a146e',
    'gtk+3.0_3.24.49-3.debian.tar.xz': '0d20b6ef612ca462929f0f27ad0e359881938a7e44088687f2ce632a4bc0fcd7',
    'gtk+3.0_3.24.49-3.dsc': '513599dc090f48106d1e2fc4d570c4d6e682e52e0ce6c059ea0218f624d48e22',
}
for name, expected in entries.items():
    url = 'https://deb.debian.org/debian/pool/main/g/gtk+3.0/' + name
    with urllib.request.urlopen(url, timeout=120) as response:
        payload = response.read()
    if hashlib.sha256(payload).hexdigest() != expected:
        raise SystemExit('Checksum mismatch: ' + name)
    pathlib.Path(name).write_bytes(payload)
patch = (repo / 'patches/gtk3-preserve-touch-serial.patch').read_bytes()
if hashlib.sha256(patch).hexdigest() != '0b4cc0f5306ae18856a9b40e86e7b5c3fffa5eda2ddc736df43d6bbaa2976f25':
    raise SystemExit('Unexpected patch checksum')
pathlib.Path('startup-serial.patch').write_bytes(patch)
PY
# --no-check skips signature lookup; every exact input is hash-pinned above.
dpkg-source --no-check -x gtk+3.0_3.24.49-3.dsc source
patch --batch --fuzz=0 -d source -p1 < startup-serial.patch
meson setup build source --prefix=/opt/tb128-gtk3-startup --libdir=lib \
  --buildtype=release -Dgtk_doc=false -Dman=false -Dintrospection=false \
  -Ddemos=false -Dexamples=false -Dtests=false -Dinstalled_tests=false \
  -Dbroadway_backend=true -Dx11_backend=true -Dwayland_backend=true \
  -Dprint_backends=file -Dcolord=no -Dcloudproviders=false -Dtracker3=false
original=$(readlink -f /usr/lib/aarch64-linux-gnu/libgdk-3.so.0)
gdk_name=$(basename "$original")
ninja -C build -j"${JOBS:-3}" "gdk/$gdk_name"
library=$PWD/build/gdk/$gdk_name
relocations=$(ldd -r "$library" 2>&1)
printf '%s\n' "$relocations"
if grep -Eq 'undefined symbol|not found' <<<"$relocations"; then exit 1; fi
nm -D --defined-only "$original" | awk '{print $3}' | sort -u > original.exports
nm -D --defined-only "$library" | awk '{print $3}' | sort -u > patched.exports
comm -23 original.exports patched.exports > missing.exports
[[ ! -s missing.exports ]] || { echo 'Missing original exports; do not install' >&2; cat missing.exports; exit 1; }
sha256sum "$library"
printf 'Verified private build, NOT installed: %s\n' "$library"
echo 'Review docs/fixes.md before installing the private library and Phosh wrapper.'
