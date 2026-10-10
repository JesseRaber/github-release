#!/usr/bin/env python3
"""Read-only post-install check: find every SKILL.md under host skill folders
and report skill names that appear more than once.

Hosts such as Codex search every subfolder of their skills folder for
SKILL.md, so a backup kept inside that folder loads as a second skill with
the same name and can shadow the new install (observed 2026-10-09).

Usage:
  python check_skill_duplicates.py ROOT [ROOT ...]
         [--name SKILL] [--expect-version X.Y.Z] [--json]

Without --name: exit 1 when any skill name appears in more than one SKILL.md.
With --name: exit 1 unless exactly one SKILL.md carries that name and, when
--expect-version is given, it reports that version.
Exit 2 on usage errors (for example a root that does not exist).

Matches files named SKILL.md case-insensitively (Windows file systems are
case-insensitive); a renamed backup such as SKILL.backup-not-loaded.md is not
matched. Does not follow directory symlinks or junctions.
Standard library only; no network; never writes anything.
"""
import argparse
import json
import os
from pathlib import Path
import re
import sys

__version__ = '0.3.0'
BACKUP_HINT = re.compile(r'backup|\.bak|\.old|pre-v\d|\.orig', re.I)


def parse_frontmatter(text):
    """Return (name, version) from YAML frontmatter; None for missing fields."""
    if text.startswith('﻿'):
        text = text[1:]
    lines = text.splitlines()
    if not lines or lines[0].strip() != '---':
        return None, None
    name = version = None
    in_metadata = False
    for line in lines[1:]:
        if line.strip() == '---':
            break
        m = re.match(r'^name:\s*(.*?)\s*$', line)
        if m:
            name = m.group(1).strip('\'"')
            continue
        if re.match(r'^metadata:\s*$', line):
            in_metadata = True
            continue
        if line and not line[0].isspace():
            in_metadata = False
        m = re.match(r'^(\s*)version:\s*(.*?)\s*$', line)
        if m and (in_metadata or not m.group(1)) and version is None:
            version = m.group(2).strip('\'"')
    return name, version


def find_skill_files(root):
    found = []
    for dirpath, dirnames, filenames in os.walk(root, followlinks=False):
        dirnames[:] = sorted(d for d in dirnames
                             if not os.path.islink(os.path.join(dirpath, d)))
        for f in sorted(filenames):
            if f.lower() == 'skill.md':
                found.append(Path(dirpath) / f)
    return found


def scan(roots):
    entries = []
    for root in roots:
        for p in find_skill_files(root):
            try:
                text = p.read_text(encoding='utf-8', errors='replace')
            except OSError as e:
                entries.append({'path': str(p), 'name': None, 'version': None,
                                'error': str(e)})
                continue
            name, version = parse_frontmatter(text)
            rel = os.path.relpath(str(p), str(root))
            entries.append({'path': str(p), 'name': name, 'version': version,
                            'backup_like_path': bool(BACKUP_HINT.search(rel))})
    return entries


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('roots', nargs='*', type=Path, help='host skill folders to search (all subfolders)')
    ap.add_argument('--name', help='the installed skill; exactly one SKILL.md may carry it')
    ap.add_argument('--expect-version', help='version the single --name copy must report')
    ap.add_argument('--json', action='store_true', help='machine-readable output')
    ap.add_argument('--version', action='version', version='%(prog)s ' + __version__)
    a = ap.parse_args(argv)
    if not a.roots:
        ap.error('give at least one skills folder')
    if a.expect_version and not a.name:
        ap.error('--expect-version needs --name')
    missing = [str(r) for r in a.roots if not r.is_dir()]
    if missing:
        print('ERROR: not a folder (or not reachable): %s' % ', '.join(missing), file=sys.stderr)
        return 2

    entries = scan(a.roots)
    by_name = {}
    for e in entries:
        by_name.setdefault(e['name'], []).append(e)
    duplicates = {n: v for n, v in by_name.items() if n and len(v) > 1}

    failures = []
    if a.name:
        copies = by_name.get(a.name, [])
        if len(copies) == 0:
            failures.append('no SKILL.md carries name: %s' % a.name)
        elif len(copies) > 1:
            failures.append('%d SKILL.md files carry name: %s (failed install; one must remain)'
                            % (len(copies), a.name))
        if a.expect_version and len(copies) == 1 and copies[0]['version'] != a.expect_version:
            failures.append('%s reports version %s, expected %s'
                            % (copies[0]['path'], copies[0]['version'], a.expect_version))
    else:
        for n, v in sorted(duplicates.items()):
            failures.append('duplicate name %s in %d SKILL.md files' % (n, len(v)))
    unnamed = [e['path'] for e in entries if not e['name']]

    result = {'tool': 'check_skill_duplicates', 'tool_version': __version__,
              'roots': [str(r) for r in a.roots], 'skill_files': len(entries),
              'entries': entries, 'duplicates': duplicates,
              'unnamed': unnamed, 'failures': failures,
              'result': 'FAIL' if failures else 'PASS'}
    if a.json:
        print(json.dumps(result, indent=2))
    else:
        print('Searched %s: %d SKILL.md file(s)' % (', '.join(result['roots']), len(entries)))
        for e in entries:
            flag = '  [backup-like path]' if e.get('backup_like_path') else ''
            print('  %s | version %s | %s%s' % (e['name'], e['version'], e['path'], flag))
        for n, v in sorted(duplicates.items()):
            print('DUPLICATE %s:' % n)
            for e in v:
                print('  - %s (version %s)' % (e['path'], e['version']))
        for p in unnamed:
            print('WARN no name: line: %s' % p)
        for f in failures:
            print('FAIL ' + f)
        print(result['result'])
    return 1 if failures else 0


if __name__ == '__main__':
    sys.exit(main())
