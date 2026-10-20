#!/bin/bash
# SPDX-License-Identifier: MIT
# Build only; never installs or loads the module.
set -euo pipefail
if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo 'Usage: build-touch-module.sh /path/to/pinned-kernel /path/to/new-build [Module.symvers]' >&2
    exit 2
fi
repo=$(cd -- "$(dirname -- "$0")/.." && pwd)
src=$(realpath -- "$1")
build=$(realpath -m -- "$2")
pin=bd4ad8882d7c500cba79db8b35501960febf0f11
[[ $(git -C "$src" rev-parse HEAD) == "$pin" ]] || { echo 'Unexpected source revision' >&2; exit 1; }
git -C "$src" diff --quiet
[[ ! -e "$build" ]] || { echo 'Choose a new build directory' >&2; exit 1; }
symvers=${3:-}
if [[ -n "$symvers" ]]; then
    symvers=$(realpath -- "$symvers")
    [[ -s "$symvers" ]]
elif [[ ${ALLOW_UNVERIFIED_EXPORT_BUILD:-0} != 1 ]]; then
    echo 'Matching full-kernel Module.symvers required. See docs/fixes.md for the historical limited path.' >&2
    exit 1
fi
mkdir -p "$build/module"
cp "$repo/touch/kernel-release.config" "$build/.config"
common=(-C "$src" O="$build" ARCH=arm64 LOCALVERSION=+)
if [[ $(uname -m) != aarch64 ]]; then
    common+=(CROSS_COMPILE="${CROSS_COMPILE:-aarch64-linux-gnu-}")
fi
make "${common[@]}" olddefconfig
release=$(make -s "${common[@]}" kernelrelease)
[[ "$release" == '6.14.0-rc5-next-20250306-tb128fu+' ]] || { echo "Unexpected release: $release" >&2; exit 1; }
make -j"${JOBS:-4}" "${common[@]}" modules_prepare
cp "$repo/touch/tb128_touch_poll.c" "$repo/touch/Makefile" "$build/module/"
if [[ -n "$symvers" ]]; then
    cp "$symvers" "$build/Module.symvers"
    make "${common[@]}" M="$build/module" modules
else
    grep -q '^# CONFIG_MODVERSIONS is not set' "$build/.config"
    grep -q '^# CONFIG_MODULE_SIG is not set' "$build/.config"
    echo 'WARNING: incomplete modpost validation; do not load before target export/ABI review.' >&2
    make "${common[@]}" KBUILD_MODPOST_WARN=1 M="$build/module" modules
fi
sha256sum "$build/module/tb128_touch_poll.ko"
echo 'Build complete, NOT installed or loaded. Run target-side tools/check-touch-abi.sh before loading.'
