#!/usr/bin/env python3
"""Read-only pre-tag checks for a skill repository.

Checks that every version touch point names the new version, lists leftover
mentions of the previous version outside history files, confirms the release
notes file exists, and lints the release workflow for draft-first publishing.

Usage:
  python check_versions.py --repo . --version 1.2.0 [--previous 1.1.0]
                           [--config packaging/version_files.json]
                           [--workflow .github/workflows/release.yml]

Exit 0 when every check passes, 1 when any fails, 2 on usage errors.
Standard library only; no network; never writes to the repository.
"""
import argparse
import fnmatch
import io
import json
import os
from pathlib import Path
import re
import sys

__version__ = '0.1.0'
SEMVER = re.compile(r'^\d+\.\d+\.\d+$')
TEXT_SUFFIXES = {'.md', '.py', '.json', '.yml', '.yaml', '.txt', '.ps1', '.toml', '.cfg'}
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'dist'}
DEFAULT_HISTORY = ['CHANGELOG.md', 'packaging/RELEASE_NOTES_v*.md', 'HOST_INSTALL_LOG.md']


def safe_stdout():
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', newline='\n')


def load_config(repo, path):
    if path is None:
        default = repo / 'packaging' / 'version_files.json'
        if not default.exists():
            return {'files': [], 'history': DEFAULT_HISTORY}
        path = default
    cfg = json.loads(Path(path).read_text(encoding='utf-8'))
    cfg.setdefault('files', [])
    cfg.setdefault('history', DEFAULT_HISTORY)
    return cfg


def check_touch_points(repo, cfg, version, results):
    v = re.escape(version) + r'(?![\d.]*\d)'  # 1.2.1 must not match 1.2.10
    for entry in cfg['files']:
        rel = entry['path']
        pattern = entry.get('pattern', '{v}').replace('{v}', v)
        p = repo / rel
        if not p.is_file():
            results.append(('FAIL', 'touch point missing: %s' % rel))
            continue
        text = p.read_text(encoding='utf-8', errors='replace')
        n = len(re.findall(pattern, text, re.M))
        if n == 0:
            results.append(('FAIL', '%s does not match %s' % (rel, entry.get('pattern', '{v}'))))
        else:
            results.append(('PASS', '%s names %s' % (rel, version)))


def check_notes(repo, version, results):
    rel = 'packaging/RELEASE_NOTES_v%s.md' % version
    if (repo / rel).is_file():
        results.append(('PASS', 'release notes present: %s' % rel))
    else:
        results.append(('FAIL', 'release notes missing: %s (the workflow will refuse to publish)' % rel))


def is_history(rel, patterns):
    return any(fnmatch.fnmatch(rel, pat) for pat in patterns)


def check_previous(repo, cfg, previous, results):
    pat = re.compile(r'(?<![\d.])v?' + re.escape(previous) + r'(?![\d])')
    hits = []
    for root, dirs, files in os.walk(repo):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            p = Path(root) / f
            if p.suffix.lower() not in TEXT_SUFFIXES:
                continue
            rel = p.relative_to(repo).as_posix()
            if is_history(rel, cfg['history']):
                continue
            try:
                lines = p.read_text(encoding='utf-8').splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(lines, 1):
                if pat.search(line):
                    hits.append('%s:%d: %s' % (rel, i, line.strip()[:120]))
    if hits:
        results.append(('FAIL', '%d mention(s) of previous version %s outside history files; '
                                'fix each or add the file to "history":' % (len(hits), previous)))
        results.extend(('    ', h) for h in hits)
    else:
        results.append(('PASS', 'no mentions of previous version %s outside history files' % previous))


def check_workflow(path, results):
    p = Path(path)
    if not p.is_file():
        results.append(('FAIL', 'workflow not found: %s' % path))
        return
    text = p.read_text(encoding='utf-8', errors='replace')
    lines = [line.split('#', 1)[0] for line in text.splitlines()]
    code = '\n'.join(lines)
    # Join shell continuations so a multi-line `gh release create` is judged as one command.
    joined = re.sub(r'\\\s*\n', ' ', code)
    creates = [l for l in joined.splitlines() if 'gh release create' in l]
    drafts_ok = bool(creates) and all(re.search(r'--draft(?![=\w-])', l) for l in creates)
    no_undraft = not re.search(r'--draft[= ]false', code)
    rules = [
        (drafts_ok, 'every `gh release create` uses --draft (%d found)' % len(creates)),
        (no_undraft, 'never publishes from the workflow (no --draft=false)'),
        ('--clobber' not in code, 'never replaces existing assets (no --clobber)'),
        ('--generate-notes' not in code, 'uses the reviewed notes file (no --generate-notes)'),
        ('release view' in code, 'checks for an existing release (refusal itself not proven by lint; read the step)'),
    ]
    for ok, label in rules:
        results.append(('PASS' if ok else 'FAIL', 'workflow ' + label))


def main(argv=None):
    safe_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--repo', default='.')
    ap.add_argument('--version', dest='new_version')
    ap.add_argument('--previous')
    ap.add_argument('--config')
    ap.add_argument('--workflow')
    ap.add_argument('-V', '--tool-version', action='store_true', help='print helper version')
    if argv is None:
        argv = sys.argv[1:]
    if argv == ['--version']:
        print('check_versions ' + __version__)
        return 0
    args = ap.parse_args(argv)
    if args.tool_version:
        print('check_versions ' + __version__)
        return 0
    if not args.new_version or not SEMVER.match(args.new_version):
        print('need --version X.Y.Z')
        return 2
    if args.previous and not SEMVER.match(args.previous):
        print('--previous must be X.Y.Z')
        return 2
    repo = Path(args.repo).resolve()
    cfg = load_config(repo, args.config)
    results = []
    if not cfg['files']:
        results.append(('FAIL', 'no touch points configured (packaging/version_files.json)'))
    check_touch_points(repo, cfg, args.new_version, results)
    check_notes(repo, args.new_version, results)
    if args.previous:
        check_previous(repo, cfg, args.previous, results)
    if args.workflow:
        check_workflow(repo / args.workflow if not Path(args.workflow).is_absolute() else args.workflow, results)
    failed = sum(1 for status, _ in results if status == 'FAIL')
    for status, msg in results:
        print('%-4s %s' % (status, msg))
    print('RESULT %s  (%d check(s) failed)' % ('FAIL' if failed else 'PASS', failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
