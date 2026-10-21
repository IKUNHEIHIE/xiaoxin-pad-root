#!/bin/bash
# SPDX-License-Identifier: MIT
# Build only. Does not install, load, flash, or connect to a tablet.
set -euo pipefail
if [[ $# -lt 2 || $# -gt 3 ]]; then
    echo 'Usage: build-bluetooth-module.sh /path/to/pinned-kernel /path/to/new-build [Module.symvers]' >&2
    exit 2
fi
repo=$(cd -- "$(dirname -- "$0")/.." && pwd)
src=$(realpath -- "$1")
build=$(realpath -m -- "$2")
[[ $(git -C "$src" rev-parse HEAD) == bd4ad8882d7c500cba79db8b35501960febf0f11 ]]
git -C "$src" diff --quiet
[[ ! -e "$build" ]] || { echo 'Choose a new build directory' >&2; exit 1; }
symvers=${3:-}
if [[ -n "$symvers" ]]; then
    symvers=$(realpath -- "$symvers")
    [[ -s "$symvers" ]]
elif [[ ${ALLOW_UNVERIFIED_EXPORT_BUILD:-0} != 1 ]]; then
    echo 'Matching full-kernel Module.symvers required. See docs/bluetooth.md for the historical limited path.' >&2
    exit 1
fi
mkdir -p "$build/module"
cp "$repo/touch/kernel-release.config" "$build/.config"
prefix=${CROSS_COMPILE:-}
if [[ -z "$prefix" && $(uname -m) != aarch64 ]]; then prefix=aarch64-linux-gnu-; fi
common=(-C "$src" O="$build" ARCH=arm64 LOCALVERSION=+)
[[ -z "$prefix" ]] || common+=(CROSS_COMPILE="$prefix")
make "${common[@]}" olddefconfig
release=$(make -s "${common[@]}" kernelrelease)
[[ "$release" == '6.14.0-rc5-next-20250306-tb128fu+' ]]
make -j"${JOBS:-4}" "${common[@]}" modules_prepare
cp "$repo/bluetooth/tb128_bt_uart.c" "$repo/bluetooth/Makefile" "$build/module/"
if [[ -n "$symvers" ]]; then
    cp "$symvers" "$build/Module.symvers"
    make "${common[@]}" M="$build/module" modules
else
    grep -q '^# CONFIG_MODVERSIONS is not set' "$build/.config"
    grep -q '^# CONFIG_MODULE_SIG is not set' "$build/.config"
    echo 'Incomplete modpost validation: target exports and ABI must be reviewed before loading.' >&2
    make "${common[@]}" KBUILD_MODPOST_WARN=1 M="$build/module" modules
fi
"${prefix}nm" -u "$build/module/tb128_bt_uart.ko" | awk '{print $NF}' > "$build/module/undefined-symbols.txt"
(cd "$build/module" && sha256sum tb128_bt_uart.ko > module.sha256)
cat "$build/module/module.sha256"
echo 'Build only. No device changed. Follow the validation and manual installation notes.'
