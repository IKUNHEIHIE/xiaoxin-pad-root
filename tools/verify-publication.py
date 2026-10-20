#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Offline source-publication audit. Does not connect to the tablet or GitHub."""
import argparse
import ast
import hashlib
import json
from pathlib import Path
import re
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
BINARY_SUFFIXES = {'.img', '.bin', '.elf', '.mbn', '.ko', '.o', '.a', '.7z', '.zip', '.gz', '.xz', '.deb', '.ext4', '.log', '.pem', '.key'}


def files():
    return sorted((p for p in ROOT.rglob('*') if p.is_file() and '.git' not in p.relative_to(ROOT).parts),
                  key=lambda p: p.relative_to(ROOT).as_posix())


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--write-manifest', action='store_true')
    parser.add_argument('--deny', action='append', default=[], help='Additional private literal to reject; never stored')
    opts = parser.parse_args()
    paths = files()
    for path in paths:
        relative = path.relative_to(ROOT).as_posix()
        if path.suffix.lower() in BINARY_SUFFIXES or re.search(r'\.so(?:\.|$)', path.name):
            raise SystemExit('Disallowed artifact: ' + relative)
        payload = path.read_bytes()
        if b'\x00' in payload or len(payload) > 1_000_000:
            raise SystemExit('Not a small source/config file: ' + relative)
        text = payload.decode('utf-8')
        for secret in opts.deny:
            if secret.casefold() in text.casefold():
                raise SystemExit('Private literal found in ' + relative)
        if re.search(r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----', text):
            raise SystemExit('Private key material in ' + relative)
        if re.search(r'(?:gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{40,})', text):
            raise SystemExit('Credential-like value in ' + relative)
        if path.suffix == '.py' or payload.startswith((b'#!/usr/bin/python3', b'#!/usr/bin/env python3')):
            ast.parse(text, filename=relative)
        if path.suffix == '.json':
            json.loads(text)
        if path.suffix == '.md':
            for match in re.finditer(r'\[[^\]\n]+\]\(([^\s)]+)\)', text):
                target = match.group(1).strip('<>')
                if urlsplit(target).scheme or target.startswith('#'):
                    continue
                local = (path.parent / unquote(target.split('#', 1)[0])).resolve()
                if not local.is_relative_to(ROOT) or not local.exists():
                    raise SystemExit(f'Broken local link: {relative} -> {target}')
    manifest = ROOT / 'SHA256SUMS'
    expected = ''.join(f'{digest(p)}  {p.relative_to(ROOT).as_posix()}\n' for p in paths if p != manifest)
    if opts.write_manifest:
        manifest.write_text(expected, encoding='utf-8', newline='\n')
    elif not manifest.exists() or manifest.read_text(encoding='utf-8') != expected:
        raise SystemExit('Manifest missing/outdated; review changes then use --write-manifest')
    downloads = json.loads((ROOT / 'sources/downloads.json').read_text(encoding='utf-8'))
    for entry in downloads['downloads']:
        sha = entry.get('sha256')
        if sha is not None and not re.fullmatch('[a-f0-9]{64}', sha):
            raise SystemExit('Invalid download hash: ' + entry['id'])
        if entry.get('local_path') and digest(ROOT / entry['local_path']) != sha:
            raise SystemExit('Vendored patch differs from source checksum')
    print(f'Publication audit passed: {len(files())} text files, local links, Python syntax, JSON, patch hash and SHA256SUMS')
    print('Also run bash -n / sh -n for shell files; device behavior is outside this offline audit.')


if __name__ == '__main__':
    main()
