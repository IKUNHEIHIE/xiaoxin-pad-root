#!/bin/sh
# SPDX-License-Identifier: MIT
# Read-only; intentionally excludes serial numbers, addresses, SSIDs and accounts.
set -eu
printf 'Kernel: '; uname -r
printf 'Architecture: '; uname -m
if [ -r /sys/firmware/devicetree/base/compatible ]; then
    printf 'DT compatible:\n'
    tr '\000' '\n' </sys/firmware/devicetree/base/compatible
fi
printf 'OS:\n'
grep -E '^(ID|VERSION_ID|PRETTY_NAME)=' /etc/os-release
printf 'Root filesystem:\n'
findmnt -no SOURCE,FSTYPE,OPTIONS /
printf 'Packages:\n'
dpkg-query -W -f='${Package} ${Version}\n' phosh phoc libgtk-3-0t64 libgl1-mesa-dri 2>/dev/null || true
printf 'Services:\n'
for unit in greetd tb128-touch-poll tb128-touch-compat tb128-gpu-safe-clock tb128-gpu-guard tb128-usb-serial; do
    printf '%s: ' "$unit"
    systemctl is-active "$unit" || true
done
for name in max_freq cur_freq; do
    path=/sys/class/devfreq/5900000.gpu/$name
    [ ! -r "$path" ] || { printf 'GPU %s: ' "$name"; cat "$path"; }
done
for name in frames points motion releases bad_crc errors; do
    path=/sys/module/tb128_touch_poll/parameters/$name
    [ ! -r "$path" ] || { printf 'Touch %s: ' "$name"; cat "$path"; }
done
