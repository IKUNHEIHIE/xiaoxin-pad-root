#!/bin/bash
# SPDX-License-Identifier: MIT
# Read-only target-side prerequisite check; not a proof of full ABI compatibility.
set -euo pipefail
[[ $# == 1 && -f "$1" ]] || { echo 'Usage: sudo check-touch-abi.sh module.ko' >&2; exit 2; }
[[ $(uname -m) == aarch64 ]]
[[ $(uname -r) == '6.14.0-rc5-next-20250306-tb128fu+' ]]
[[ $(modinfo -F vermagic "$1" | cut -d' ' -f1) == "$(uname -r)" ]]
mapfile -t imports < <(nm -u "$1" | awk '{print $NF}' | sort -u)
[[ ${#imports[@]} -gt 0 ]]
missing=0
for symbol in "${imports[@]}"; do
    if ! awk -v name="__ksymtab_$symbol" '$3 == name {found=1} END {exit !found}' /proc/kallsyms; then
        printf 'Missing exported symbol: %s\n' "$symbol" >&2
        missing=1
    fi
done
[[ "$missing" == 0 ]]
printf 'Release and %s export names matched. Review provenance/config/signatures; this script does not load anything.\n' "${#imports[@]}"
