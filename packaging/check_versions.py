#!/usr/bin/env python3
"""Read-only pre-tag checks for a skill repository.

Checks that every version touch point names the new version, lists leftover
mentions of the previous version outside history files, confirms the release
notes file exists and reads as a released note (no candidate wording, no
placeholders, no pre-written dates, no internal IDs), checks record files for
encoding damage, lints the release workflow for draft-first publishing, and
optionally lists repository copies that drifted from the skill's templates.

Usage:
  python check_versions.py --repo . --version 1.2.0 [--previous 1.1.0]
                           [--config packaging/version_files.json]
                           [--workflow .github/workflows/release.yml]
                           [--drift-against path/to/skills/github-release]

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

__version__ = '0.3.0'
SEMVER = re.compile(r'^\d+\.\d+\.\d+$')
TEXT_SUFFIXES = {'.md', '.py', '.json', '.yml', '.yaml', '.txt', '.ps1', '.toml', '.cfg'}
SKIP_DIRS = {'.git', '__pycache__', 'node_modules', 'dist'}
DEFAULT_HISTORY = ['CHANGELOG.md', 'packaging/RELEASE_NOTES_v*.md', 'HOST_INSTALL_LOG.md']
DEFAULT_RECORDS = ['HOST_INSTALL_LOG.md', 'CHANGELOG.md', 'README.md', 'packaging/RELEASE_NOTES_v*.md']
# Wording that must never reach a published release body (observed on immutable releases).
NOTES_FORBIDDEN = [
    (r'\(candidate\)|status:\s*(local |release )?candidate|\bcandidate[,;]? not\b', 'candidate status wording'),
    (r'\bnot (yet )?released\b', '"not released" wording'),
    (r'\bnot (yet )?(committed|published)\b', '"not committed/published" wording'),
    (r'\bTBD\b|\bTODO\b', 'TBD/TODO'),
    (r'verification required before release', 'pre-release checklist'),
    (r'SKILL-NAME|X\.Y\.Z|YYYY-MM-DD|<[a-z][a-z -]*>', 'template placeholder'),
    (r'^\s*-\s*$', 'empty bullet'),
    (r'\breleased (on )?\d{4}-\d{2}-\d{2}', 'pre-written publish date (GitHub shows published_at)'),
]
NOTES_WARN = [
    (r'\bcandidate\b', 'the word "candidate" (fine when it describes a feature, never as release status)'),
    (r'\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b', 'session UUID (internal ID)'),
    (r'\b[RWL]-?\d{3}\b', 'register/tracker row ID (internal ID)'),
]
# Repository copy -> skill path, for --drift-against.
DRIFT_PAIRS = [
    ('packaging/check_versions.py', 'scripts/check_versions.py'),
    ('packaging/verify_release.py', 'scripts/verify_release.py'),
    ('packaging/check_skill_duplicates.py', 'scripts/check_skill_duplicates.py'),
    ('packaging/build_packages.py', 'templates/build_packages.py'),
    ('.github/workflows/release.yml', 'templates/release.yml'),
    ('.github/workflows/ci.yml', 'templates/ci.yml'),
]


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
        lint_notes(repo / rel, rel, results)
    else:
        results.append(('FAIL', 'release notes missing: %s (the workflow will refuse to publish)' % rel))


def lint_notes(path, rel, results):
    """The notes file becomes the public release body; it must read as released text."""
    text = path.read_text(encoding='utf-8', errors='replace')
    # HTML comments are template guidance, not public text; blank them but keep line numbers.
    text = re.sub(r'<!--.*?-->', lambda m: '\n' * m.group(0).count('\n'), text, flags=re.S)
    lines = text.splitlines()
    bad = 0
    for i, line in enumerate(lines, 1):
        for pat, label in NOTES_FORBIDDEN:
            if re.search(pat, line, re.I if label != 'TBD/TODO' else 0):
                results.append(('FAIL', 'notes %s:%d %s: %s' % (rel, i, label, line.strip()[:100])))
                bad += 1
        for pat, label in NOTES_WARN:
            if re.search(pat, line):
                results.append(('WARN', 'notes %s:%d %s; keep it in the PR body: %s' % (rel, i, label, line.strip()[:100])))
    if not bad:
        results.append(('PASS', 'notes body lint: no candidate wording, placeholders or pre-written dates'))


def check_records(repo, patterns, results):
    """Record files must be UTF-8 without BOM, no NUL bytes, LF line endings."""
    seen = set()
    for pat in patterns:
        for p in sorted(repo.glob(pat)):
            if not p.is_file() or p in seen:
                continue
            seen.add(p)
            rel = p.relative_to(repo).as_posix()
            data = p.read_bytes()
            problems = []
            if data.startswith(b'\xef\xbb\xbf'):
                problems.append('UTF-8 BOM')
            if data[:2] in (b'\xff\xfe', b'\xfe\xff') or b'\x00' in data:
                problems.append('%d NUL byte(s) (UTF-16 write?)' % data.count(b'\x00'))
            if b'\r\n' in data:
                problems.append('CRLF line endings')
            try:
                data.decode('utf-8')
            except UnicodeDecodeError as e:
                problems.append('not UTF-8 (byte %d)' % e.start)
            if p.name == 'HOST_INSTALL_LOG.md':
                text = data.decode('utf-8', errors='replace')
                heads = [l.strip() for l in text.splitlines() if re.match(r'^\|\s*Date\b', l)]
                if not heads:
                    problems.append('no table header row')
                elif len(heads) != len(set(heads)):
                    # A new column set may start a new appended table; the same header twice means a rewrite.
                    problems.append('repeated identical table header row')
            if problems:
                results.append(('FAIL', 'record %s: %s' % (rel, '; '.join(problems))))
            else:
                results.append(('PASS', 'record %s: UTF-8, no BOM, no NUL, LF' % rel))


def check_drift(repo, skill_dir, results):
    import hashlib
    skill = Path(skill_dir)
    if not (skill / 'SKILL.md').is_file():
        results.append(('FAIL', 'drift: no SKILL.md in %s' % skill))
        return
    stale = 0
    for repo_rel, skill_rel in DRIFT_PAIRS:
        a, b = repo / repo_rel, skill / skill_rel
        if not a.is_file():
            continue  # repository does not carry this copy
        if not b.is_file():
            results.append(('WARN', 'drift: skill has no %s to compare with %s' % (skill_rel, repo_rel)))
            continue
        same = hashlib.sha256(a.read_bytes()).digest() == hashlib.sha256(b.read_bytes()).digest()
        if not same:
            stale += 1
        results.append(('PASS' if same else 'FAIL', 'drift: %s %s skill %s' % (repo_rel, '==' if same else 'differs from', skill_rel)))
    log, tmpl = repo / 'HOST_INSTALL_LOG.md', skill / 'templates' / 'HOST_INSTALL_LOG.md'
    if log.is_file() and tmpl.is_file():
        def header(p):
            heads = [l.strip() for l in p.read_text(encoding='utf-8', errors='replace').splitlines()
                     if re.match(r'^\|\s*Date\b', l)]
            return heads[-1] if heads else None  # the table new rows are appended to
        same = header(log) == header(tmpl)
        if not same:
            stale += 1
        results.append(('PASS' if same else 'FAIL', 'drift: HOST_INSTALL_LOG.md current (last) table header %s template' % ('matches' if same else 'differs from')))
    results.append(('INFO', 'drift: %d stale cop%s' % (stale, 'y' if stale == 1 else 'ies')))


def is_history(rel, patterns):
    return any(fnmatch.fnmatch(rel, pat) for pat in patterns)


def _scan_previous(base, label, pat, history, hits):
    for root, dirs, files in os.walk(base):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for f in sorted(files):
            p = Path(root) / f
            if p.suffix.lower() not in TEXT_SUFFIXES:
                continue
            rel = p.relative_to(base).as_posix()
            if history is not None and is_history(rel, history):
                continue
            try:
                lines = p.read_text(encoding='utf-8').splitlines()
            except (UnicodeDecodeError, OSError):
                continue
            for i, line in enumerate(lines, 1):
                if pat.search(line):
                    hits.append('%s%s:%d: %s' % (label, rel, i, line.strip()[:120]))


def check_previous(repo, cfg, previous, results, extra_roots=()):
    pat = re.compile(r'(?<![\d.])v?' + re.escape(previous) + r'(?![\d])')
    hits = []
    _scan_previous(repo, '', pat, cfg['history'], hits)
    for er in extra_roots:
        erp = Path(er)
        if not erp.is_dir():
            results.append(('FAIL', 'extra root not found (clone it or drop the flag): %s' % er))
            continue
        _scan_previous(erp, erp.name + '/', pat, None, hits)
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
    ap.add_argument('--extra-root', action='append', default=[],
                    help='also scan this directory (e.g. a wiki clone) for previous-version mentions; repeatable')
    ap.add_argument('--config')
    ap.add_argument('--workflow')
    ap.add_argument('--drift-against', metavar='SKILL_DIR',
                    help='compare repository copies of helpers, workflows and the install-log header with this skill folder (gate G14)')
    ap.add_argument('--no-records', action='store_true', help='skip the record-file encoding lint')
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
        check_previous(repo, cfg, args.previous, results, args.extra_root)
    if not args.no_records:
        check_records(repo, cfg.get('records', DEFAULT_RECORDS), results)
    if args.drift_against:
        check_drift(repo, args.drift_against, results)
    if args.workflow:
        check_workflow(repo / args.workflow if not Path(args.workflow).is_absolute() else args.workflow, results)
    failed = sum(1 for status, _ in results if status == 'FAIL')
    for status, msg in results:
        print('%-4s %s' % (status, msg))
    print('RESULT %s  (%d check(s) failed)' % ('FAIL' if failed else 'PASS', failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
