#!/bin/sh
# SPDX-License-Identifier: MIT
# Debian python3-pywayland must be installed. Writes only to the chosen directory.
set -eu
[ "$#" -eq 1 ] || { echo 'Usage: generate-pointer-bindings.sh /path/to/output' >&2; exit 2; }
repo=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
mkdir -p "$1"
python3 - "$repo/protocols/wlr-virtual-pointer-unstable-v1.xml" "$1" <<'PY'
import sys
from pathlib import Path
from pywayland.scanner import Protocol
protocol = Protocol.parse_file(sys.argv[1])
imports = {'wl_seat': 'wayland', 'wl_output': 'wayland', 'wl_pointer': 'wayland'}
imports.update({interface.name: protocol.name for interface in protocol.interface})
protocol.output(sys.argv[2], imports)
for path in Path(sys.argv[2], protocol.name).rglob('*.py'):
    path.write_text(path.read_text().replace('from ..wayland import', 'from pywayland.protocol.wayland import'))
print('Bindings generated. Copy the resulting wlr_virtual_pointer_unstable_v1 package to /usr/local/lib/tb128-input/.')
PY
