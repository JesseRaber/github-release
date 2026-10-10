#!/usr/bin/env python3
"""Read-only verification of downloaded release assets.

Compares a folder of downloaded release assets with its SHA256SUMS.txt,
optionally with the GitHub release metadata (JSON from `gh api`) and with a
local candidate build. Never downloads, uploads or changes anything.

Usage:
  python verify_release.py --assets DIR [--version X.Y.Z]
                           [--release-json FILE] [--candidate DIR]
                           [--notes packaging/RELEASE_NOTES_vX.Y.Z.md]
                           [--expected-author github-actions[bot]]

Exit 0 when every requested check passed, 1 when any failed, 2 on usage errors.
"""
import argparse
import hashlib
import io
import json
from pathlib import Path
import re
import sys
import zipfile

__version__ = '0.3.0'
SUMS = 'SHA256SUMS.txt'
WORKFLOW_AUTHOR = 'github-actions[bot]'
KNOWN_ISSUES = re.compile(r'^#{2,3} Known issues \(added \d{4}-\d{2}-\d{2}', re.I)


def safe_stdout():
    if hasattr(sys.stdout, 'buffer'):
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', newline='\n')


def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(1 << 20), b''):
            h.update(chunk)
    return h.hexdigest()


def read_sums(path):
    rows = {}
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        if not line.strip():
            continue
        digest, name = line.split(None, 1)
        rows[name.lstrip('*').strip()] = digest.lower()
    return rows


def check_sums(assets, out):
    sums_path = assets / SUMS
    if not sums_path.is_file():
        out.append(('FAIL', 'no %s in %s' % (SUMS, assets)))
        return {}
    listed = read_sums(sums_path)
    present = {p.name: p for p in assets.iterdir() if p.is_file() and p.name != SUMS}
    actual = {}
    for name, want in sorted(listed.items()):
        if name not in present:
            out.append(('FAIL', 'listed but not downloaded: %s' % name))
            continue
        got = sha256(present[name])
        actual[name] = got
        out.append(('PASS' if got == want else 'FAIL',
                    '%s sha256 %s %s' % (name, got[:12], 'matches SHA256SUMS' if got == want else '!= ' + want[:12])))
    for name in sorted(set(present) - set(listed)):
        if name.endswith('.zip'):
            out.append(('FAIL', 'archive not listed in SHA256SUMS: %s' % name))
    return actual


def check_zips(assets, actual, version, out):
    for name in sorted(actual):
        if not name.endswith('.zip'):
            continue
        if version and ('-%s-' % version) not in name:
            out.append(('FAIL', '%s does not carry version %s' % (name, version)))
        try:
            with zipfile.ZipFile(assets / name) as z:
                bad = z.testzip()
                names = z.namelist()
            ok = bad is None and len(names) == len(set(names))
            out.append(('PASS' if ok else 'FAIL', '%s zip integrity (%d members)' % (name, len(names))))
        except zipfile.BadZipFile as e:
            out.append(('FAIL', '%s is not a valid zip: %s' % (name, e)))


def load_release(path, out):
    data = json.loads(Path(path).read_text(encoding='utf-8-sig'))
    if not isinstance(data, dict):
        out.append(('FAIL', 'release JSON must be ONE release object, not a %s; select it with '
                            "--jq '.[] | select(.tag_name==\"vX.Y.Z\")'" % type(data).__name__))
        return None
    return data


def count_downloads(assets, data, out):
    """Report first, so an incomplete download is visible before any per-file FAIL."""
    listed = [a.get('name') for a in data.get('assets', [])]
    got = sum(1 for n in listed if (assets / n).is_file())
    out.append(('INFO' if got == len(listed) else 'FAIL',
                'downloaded %d of %d listed assets' % (got, len(listed))))


def check_identity(data, version, expected_author, out):
    author = (data.get('author') or {}).get('login')
    title = data.get('name')
    out.append(('INFO', 'release author=%s title=%r' % (author, title)))
    if author != expected_author:
        out.append(('FAIL', 'release created by %s, not %s: hand-created releases are not allowed '
                            '(publish.md Never)' % (author, expected_author)))
    if version and not (title or '').endswith(' v' + version):
        out.append(('FAIL', 'release title %r does not end with " v%s" (workflow title is "<skill> v<version>")' % (title, version)))


def _norm(text):
    return '\n'.join(l.rstrip() for l in text.replace('\r\n', '\n').strip().split('\n'))


def check_body(data, notes_path, out):
    body = _norm(data.get('body') or '')
    notes = _norm(Path(notes_path).read_text(encoding='utf-8-sig'))
    if body == notes:
        out.append(('PASS', 'release body == %s' % Path(notes_path).name))
        return
    if body.startswith(notes):
        extra = body[len(notes):].lstrip('\n')
        if KNOWN_ISSUES.match(extra):
            out.append(('PASS', 'release body == notes file + appended dated Known issues section (publish.md section 5)'))
            return
    out.append(('FAIL', 'release body differs from %s (only an appended "## Known issues (added YYYY-MM-DD)" '
                        'section is allowed after publish)' % Path(notes_path).name))


def check_release_json(data, assets, version, out, expect_published=False, expect_immutable=False):
    tag = data.get('tag_name')
    if version and tag != 'v' + version:
        out.append(('FAIL', 'release tag %r is not v%s' % (tag, version)))
    out.append(('INFO', 'release %s draft=%s prerelease=%s immutable=%s' % (
        tag, data.get('draft'), data.get('prerelease'), data.get('immutable'))))
    if expect_published and data.get('draft') is not False:
        out.append(('FAIL', 'release is still a draft (or draft state unknown)'))
    if expect_immutable and data.get('immutable') is not True:
        out.append(('FAIL', 'release is not immutable'))
    gh = {a['name']: a for a in data.get('assets', [])}
    local = {p.name for p in assets.iterdir() if p.is_file()}
    for name in sorted(set(gh) - local):
        out.append(('FAIL', 'on GitHub but not downloaded: %s' % name))
    for name in sorted(set(gh) & local):
        a = gh[name]
        d = (a.get('digest') or '')
        if a.get('state') not in (None, 'uploaded'):
            out.append(('FAIL', '%s state is %s' % (name, a.get('state'))))
        if not d.startswith('sha256:'):
            out.append(('WARN', '%s: GitHub returned no sha256 digest; size-only check' % name))
            ok = a.get('size') == (assets / name).stat().st_size
            out.append(('PASS' if ok else 'FAIL', '%s size %s' % (name, a.get('size'))))
            continue
        got = sha256(assets / name)
        ok = d[7:].lower() == got
        out.append(('PASS' if ok else 'FAIL', '%s GitHub digest %s local' % (name, '==' if ok else '!=')))
    for name in sorted(local - set(gh)):
        out.append(('FAIL', 'downloaded file not on the GitHub release: %s' % name))


def check_candidate(candidate, assets, actual, out):
    cand = Path(candidate)
    names = sorted(n for n in actual if n.endswith('.zip'))
    cand_zips = {p.name for p in cand.glob('*.zip')}
    for name in names:
        if name not in cand_zips:
            out.append(('FAIL', 'no candidate archive named %s' % name))
            continue
        same = sha256(cand / name) == actual[name]
        out.append(('PASS' if same else 'FAIL', '%s %s local candidate' % (name, 'byte-identical to' if same else 'DIFFERS from')))
    for name in sorted(cand_zips - set(names)):
        out.append(('FAIL', 'candidate archive missing from release: %s' % name))


def main(argv=None):
    safe_stdout()
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--assets')
    ap.add_argument('--version', dest='release_version')
    ap.add_argument('--release-json')
    ap.add_argument('--candidate')
    ap.add_argument('--expect-published', action='store_true', help='FAIL if the release is a draft')
    ap.add_argument('--expect-immutable', action='store_true', help='FAIL if the release is not immutable')
    ap.add_argument('--notes', help='release notes file the body must equal (needs --release-json)')
    ap.add_argument('--expected-author', default=WORKFLOW_AUTHOR,
                    help='login that must have created the release (default %s)' % WORKFLOW_AUTHOR)
    if argv is None:
        argv = sys.argv[1:]
    if argv == ['--version']:
        print('verify_release ' + __version__)
        return 0
    args = ap.parse_args(argv)
    if not args.assets:
        print('need --assets DIR')
        return 2
    assets = Path(args.assets)
    if not assets.is_dir():
        print('assets folder not found: %s' % assets)
        return 2
    out = []
    data = None
    if args.release_json:
        data = load_release(args.release_json, out)
        if data is not None:
            count_downloads(assets, data, out)
    if args.notes and not args.release_json:
        print('--notes needs --release-json')
        return 2
    actual = check_sums(assets, out)
    check_zips(assets, actual, args.release_version, out)
    ran = ['checksums', 'zip integrity']
    if data is not None:
        check_release_json(data, assets, args.release_version, out,
                           args.expect_published, args.expect_immutable)
        check_identity(data, args.release_version, args.expected_author, out)
        ran.append('GitHub metadata')
        ran.append('author/title')
        if args.notes:
            check_body(data, args.notes, out)
            ran.append('notes body')
    if args.candidate:
        check_candidate(args.candidate, assets, actual, out)
        ran.append('local candidate')
    failed = sum(1 for s, _ in out if s == 'FAIL')
    for s, m in out:
        print('%-4s %s' % (s, m))
    print('CHECKS RUN: ' + ', '.join(ran))
    print('RESULT %s  (%d failed)' % ('FAIL' if failed else 'PASS', failed))
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
