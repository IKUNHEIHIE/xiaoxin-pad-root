#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Read this tablet's own persist address without journal replay or raw output."""
import os
from pathlib import Path
import re
import subprocess
import tempfile

if os.geteuid() != 0:
    raise SystemExit('Run as root on the target tablet.')
compatible=Path('/proc/device-tree/compatible').read_bytes().split(b'\0')
if b'lenovo,tb128' not in compatible:
    raise SystemExit('Not the documented TB128 hardware.')
target=Path('/root/tb128-bluetooth-private/factory-address')
if target.exists():
    raise SystemExit('Private address already exists; review it locally before replacing.')
mountpoint=Path(tempfile.mkdtemp(prefix='tb128-bt-persist.',dir='/run'))
mounted=False
try:
    subprocess.run(['mount','-t','ext4','-o','ro,noload','/dev/disk/by-partlabel/persist',str(mountpoint)],check=True)
    mounted=True
    address=(mountpoint/'bt_macaddress').read_text().strip().upper()
    assert re.fullmatch(r'(?:[0-9A-F]{2}:){5}[0-9A-F]{2}',address),'Unexpected address format'
    assert not int(address[:2],16)&1,'Not a unicast address'
    assert address not in ('00:00:00:00:00:00','FF:FF:FF:FF:FF:FF','39:90:21:64:07:00'),'Invalid or placeholder address'
    target.parent.mkdir(mode=0o700,parents=True,exist_ok=True)
    os.chmod(target.parent,0o700)
    fd=os.open(target,os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
    with os.fdopen(fd,'w') as stream:
        stream.write(address+'\n')
    print('Factory address saved privately on this device; persist was not modified.')
finally:
    if mounted:
        subprocess.run(['umount',str(mountpoint)],check=True)
    mountpoint.rmdir()
