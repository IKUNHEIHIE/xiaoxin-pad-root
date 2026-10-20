#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Build and round-trip check a boot-v2 image; never connects to a device.

This is the portable publication recipe, not a new full-device flashing test.
Requires complete AOSP mkbootimg sources, cpio and fdtput on Linux/WSL.
"""
import argparse
import gzip
import hashlib
import os
from pathlib import Path
import struct
import subprocess
import sys
import tempfile

CMDLINE = ('console=tty0 console=ttyGS0,115200n8 init=/init root=/dev/sda18 '
           'ro rootwait loglevel=4 panic=0 clk_ignore_unused pd_ignore_unused '
           'slot_suffix=_a')


def boot_v2(path):
    with path.open('rb') as stream:
        header = stream.read(48)
    if len(header) < 48 or header[:8] != b'ANDROID!':
        raise ValueError(f'Not an Android boot image: {path}')
    if struct.unpack_from('<I', header, 40)[0] != 2:
        raise ValueError('Only the tested boot header v2 is supported')


def run(args, **kwargs):
    return subprocess.run([str(a) for a in args], check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--reference-android', type=Path, required=True)
    parser.add_argument('--upstream-boot', type=Path, required=True)
    parser.add_argument('--ramdisk-directory', type=Path, required=True)
    parser.add_argument('--aosp-tools', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    opts = parser.parse_args()
    for key, value in vars(opts).items():
        setattr(opts, key, value.resolve())
    if opts.output.exists():
        raise SystemExit('Output exists; choose a new file')
    boot_v2(opts.reference_android)
    boot_v2(opts.upstream_boot)
    stage = opts.ramdisk_directory
    for relative in ('init', 'bin/busybox', 'sbin/reboot-bootloader',
                     'lib/modules/qcom-pon.ko', 'lib/modules/spi-geni-qcom.ko'):
        if not (stage / relative).is_file():
            raise SystemExit('Missing ramdisk input: ' + relative)
    if not os.access(stage / 'init', os.X_OK):
        raise SystemExit('ramdisk /init must be executable')
    unpack = opts.aosp_tools / 'unpack_bootimg.py'
    mkboot = opts.aosp_tools / 'mkbootimg.py'
    if not unpack.is_file() or not mkboot.is_file():
        raise SystemExit('Use complete AOSP mkbootimg source directory')
    with tempfile.TemporaryDirectory(prefix='tb128-boot-') as tmp:
        work = Path(tmp)
        ref, upstream = work / 'reference', work / 'upstream'
        result = run([sys.executable, unpack, '--boot_img', opts.reference_android,
                      '--out', ref, '--format', 'mkbootimg', '-0'], stdout=subprocess.PIPE)
        args = result.stdout.rstrip(b'\0').decode().split('\0')
        run([sys.executable, unpack, '--boot_img', opts.upstream_boot,
             '--out', upstream], stdout=subprocess.DEVNULL)
        dtb = upstream / 'dtb'
        run(['fdtput', '-t', 's', dtb, '/chosen', 'bootargs', CMDLINE])
        names = ['.'] + sorted('./' + p.relative_to(stage).as_posix() for p in stage.rglob('*'))
        archive = run(['cpio', '--null', '-o', '-H', 'newc', '--owner=0:0', '--quiet'],
                      cwd=stage, input=('\0'.join(names) + '\0').encode(), stdout=subprocess.PIPE).stdout
        ramdisk = work / 'ramdisk.gz'
        ramdisk.write_bytes(gzip.compress(archive, mtime=0))
        if ramdisk.stat().st_size >= 4 * 1024 * 1024:
            raise SystemExit('Ramdisk exceeds tested small-ramdisk size limit')
        replacements = {'--kernel': str(upstream / 'kernel'), '--dtb': str(dtb),
                        '--ramdisk': str(ramdisk), '--cmdline': CMDLINE}
        for flag, value in replacements.items():
            if flag not in args:
                raise SystemExit('Reference missing required argument: ' + flag)
            args[args.index(flag) + 1] = value
        built = work / 'new-boot.img'
        run([sys.executable, mkboot, *args, '--output', built])
        boot_v2(built)
        verify = work / 'verify'
        run([sys.executable, unpack, '--boot_img', built, '--out', verify], stdout=subprocess.DEVNULL)
        for name, expected in [('kernel', upstream / 'kernel'), ('dtb', dtb), ('ramdisk', ramdisk)]:
            if (verify / name).read_bytes() != expected.read_bytes():
                raise SystemExit('Round-trip mismatch: ' + name)
        # Exclusive creation avoids clobbering an existing artifact after a race.
        payload = built.read_bytes()
        with opts.output.open('xb') as stream:
            stream.write(payload)
        print(f'{hashlib.sha256(payload).hexdigest()}  {opts.output.name} ({len(payload)} bytes)')
        print('Built and unpack-checked only; no partition was written.')


if __name__ == '__main__':
    main()
