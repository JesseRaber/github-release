"""Build and verify host-specific install archives for one Agent Skill.

Template from the github-release skill. Never tags, uploads, publishes or installs.

Usage:
    python packaging/build_packages.py NEW_OUTPUT_DIRECTORY [--config packaging/packages.json]
                                       [--status TEXT]

Repository layout expected (paths are relative to the repository root):
    skills/<name>/SKILL.md          skill source; frontmatter has name and metadata.version
    packaging/packages.json         which archives to build and what each one omits
    .claude-plugin/, .codex-plugin/ plugin manifests (only if a plugin layout is configured)

The output directory must not exist. Every archive is rebuilt from source,
re-read, byte-compared and smoke-tested before SHA256SUMS.txt is written.
ZIPs are deterministic: fixed timestamp, sorted members, fixed permissions.
"""
import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import subprocess
import sys
import tempfile
import zipfile

__version__ = '1.0.2'
STAMP = (2026, 1, 1, 0, 0, 0)
REPO = Path(__file__).resolve().parents[1]
OPAL_SIZE_WARN = 48 * 1024  # observed Opal per-file rejection ~48-79 KB (approximate, 2026-10-03)
# Checked independently of packages.json so a config typo cannot ship a file a host rejects.
HOST_INVARIANTS = {
    'microsoft-copilot-agent-only': ('.ps1',),
    'gemini-apps-only': ('.ps1', '.yml', '.yaml'),
}
# Hosts whose uploader rejects files without an extension (Gemini Apps: observed 2026-10-08,
# "unsupported file type" on templates/gitattributes; same package without it was accepted).
HOST_NO_EXTENSIONLESS = {'gemini-apps-only'}
# Package names that may appear in packages.json. A renamed package must be added here
# deliberately, so it cannot silently escape its host invariants.
KNOWN_PACKAGES = {'UNIVERSAL-skill', 'claude-code-plugin', 'codex-chatgpt-plugin',
                  'microsoft-copilot-agent-only', 'gemini-apps-only', 'opal-only'}


def check(condition, *detail):
    """Explicit check that still runs under python -O (assert would not)."""
    if not condition:
        raise SystemExit('package check failed: %r' % (detail or ('',),))


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_config(path):
    cfg = json.loads(path.read_text(encoding='utf-8'))
    for key in ('skill', 'packages'):
        if key not in cfg:
            raise SystemExit('packages.json missing ' + key)
    return cfg


def safe_relative(rel):
    if (not isinstance(rel, str) or not rel or '\\' in rel or ':' in rel
            or rel.startswith('/') or any(p in ('', '.', '..') for p in rel.rstrip('/').split('/'))):
        raise ValueError('Unsafe relative path: %r' % rel)
    return rel


def repo_path(rel):
    """Refuse traversal and linked ancestors, including Windows junctions."""
    safe_relative(rel)
    path = REPO
    for part in PurePosixPath(rel).parts:
        path = path / part
        if path.is_symlink() or (hasattr(path, 'is_junction') and path.is_junction()):
            raise ValueError('Refusing linked repo path: %s' % path)
        if path.exists() and getattr(path.lstat(), 'st_file_attributes', 0) & 0x400:
            raise ValueError('Refusing reparse point: %s' % path)
    try:
        path.resolve().relative_to(REPO.resolve())
    except ValueError:
        raise ValueError('Refusing external repo path: %s' % rel)
    return path


def frontmatter(data):
    text = data.decode('utf-8').replace('\r\n', '\n')
    lines = text.splitlines(keepends=True)
    if not lines or lines[0] != '---\n':
        raise ValueError('SKILL.md needs line-delimited YAML frontmatter')
    end = next((i for i in range(1, len(lines)) if lines[i].rstrip('\n') == '---'), None)
    if end is None:
        raise ValueError('SKILL.md missing closing frontmatter delimiter')
    return ''.join(lines[1:end]), ''.join(lines[end + 1:])


def skill_version(skill_dir, name):
    text, _ = frontmatter((skill_dir / 'SKILL.md').read_bytes())
    names = re.findall(r'^name:[ \t]*(\S+)[ \t]*$', text, re.M)
    if names != [name]:
        raise SystemExit('SKILL.md name does not match packages.json skill: %r' % name)
    metadata = re.search(r'^metadata:[ \t]*\n((?:[ \t]+[^\n]*\n|\n)+)', text + '\n', re.M)
    versions = re.findall(r'^  version: "(\d+\.\d+\.\d+)"[ \t]*$', metadata.group(1), re.M) if metadata else []
    if len(versions) != 1:
        raise SystemExit('SKILL.md needs metadata.version as:  version: "X.Y.Z"')
    return versions[0]


def source_files(skill_dir):
    repo_path(skill_dir.relative_to(REPO).as_posix())
    files = {}
    for p in sorted(skill_dir.rglob('*')):
        repo_path(p.relative_to(REPO).as_posix())
        if '__pycache__' in p.parts or p.suffix == '.pyc' or not p.is_file():
            continue
        if p.is_symlink():
            raise ValueError('Refusing linked package source: %s' % p)
        files[p.relative_to(skill_dir).as_posix()] = p.read_bytes()
    return files


def excluded(rel, spec):
    return (rel.startswith(tuple(spec.get('exclude_prefix', [])))
            or rel.lower().endswith(tuple(s.lower() for s in spec.get('exclude_suffix', [])))
            or rel in spec.get('exclude_files', [])
            or (spec.get('exclude_no_suffix') and not PurePosixPath(rel).suffix))


def opal_skill_md(data):
    """Opal accepts only name and description in the frontmatter, LF endings."""
    front, body = frontmatter(data)
    keep = [line for line in front.splitlines() if line.startswith(('name:', 'description:'))]
    if len(keep) != 2 or not any(line.startswith('name:') for line in keep) or not any(line.startswith('description:') for line in keep):
        raise ValueError('SKILL.md frontmatter needs single-line name and description')
    for line in keep:
        value = line.split(':', 1)[1].strip()
        if not value or value[0] in '>|':
            raise ValueError('Opal needs single-line, non-empty name and description: %r' % line)
        if value[0] in "\"'":
            quote, i, closed = value[0], 1, False
            while i < len(value):
                if quote == '"' and value[i] == '\\':
                    i += 2
                    continue
                if value[i] == quote:
                    if quote == "'" and value[i:i + 2] == "''":
                        i += 2
                        continue
                    tail = value[i + 1:].strip()
                    closed = not tail or tail.startswith('#')
                    break
                i += 1
            if not closed:
                raise ValueError('Opal requires a complete single-line quoted scalar: %r' % line)
    active = None
    for line in front.splitlines():
        if not line.strip() or line.lstrip().startswith('#'):
            continue
        if not line[0].isspace():
            active = line.split(':', 1)[0]
        elif active in ('name', 'description'):
            raise ValueError('Opal requires single-line %s; multiline continuation refused' % active)
    return ('---\n' + '\n'.join(keep) + '\n---\n' + body).encode('utf-8')


def build_one(spec, files, name):
    root = name + '/'
    layout = spec['layout']
    safe_relative(name)
    repo = lambda rel: repo_path(rel).read_bytes()
    kept = {n: d for n, d in files.items() if not excluded(n, spec)}
    if layout == 'skill':
        items = {root + n: d for n, d in kept.items()}
    elif layout == 'plugin':
        items = {root + 'skills/' + name + '/' + n: d for n, d in kept.items()}
        meta = spec['metadata']
        for p in sorted(repo_path(meta).glob('*.json')):
            repo_path(p.relative_to(REPO).as_posix())
            items[root + meta + '/' + p.name] = p.read_bytes()
    elif layout == 'opal':
        items = {root + 'SKILL.md': opal_skill_md(files['SKILL.md'])}
        for n, d in kept.items():
            if n.startswith('references/') and n.count('/') == 1 and n.endswith('.md'):
                items[root + n] = d.replace(b'\r\n', b'\n')
    elif layout == 'subtree':
        src, dst = spec['from'], spec['to']
        safe_relative(src)
        safe_relative(dst)
        items = {dst + n[len(src):]: d for n, d in kept.items() if n.startswith(src)}
    else:
        raise SystemExit('unknown layout ' + layout)
    for target, source in spec.get('add', {}).items():
        safe_relative(target)
        items[root + target] = repo(source)
    return items, spec.get('folder_entries', layout != 'opal')


def write_zip(archive, items, folder_entries):
    for name in items:
        safe_relative(name)
    names = sorted(items)
    dirs = set()
    if folder_entries:
        for n in names:
            parts = n.split('/')[:-1]
            for i in range(1, len(parts) + 1):
                dirs.add('/'.join(parts[:i]) + '/')
    with zipfile.ZipFile(archive, 'x', compression=zipfile.ZIP_DEFLATED) as z:
        for d in sorted(dirs):
            info = zipfile.ZipInfo(d, date_time=STAMP)
            info.create_system = 3  # same bytes on Windows and POSIX builders
            info.external_attr = 0o40755 << 16 | 0x10
            z.writestr(info, b'')
        for n in names:
            info = zipfile.ZipInfo(n, date_time=STAMP)
            info.create_system = 3
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o100644 << 16
            z.writestr(info, items[n])
    return dirs


def verify(archive, flavor, spec, items, dirs, version, smoke, warnings, smoked, checked=None):
    checked = set() if checked is None else checked
    with zipfile.ZipFile(archive) as z:
        check(z.testzip() is None)
        listed = z.namelist()
        check(len(listed) == len(set(listed)), 'duplicate members')
        check(set(listed) == set(items) | dirs, sorted(set(listed) ^ (set(items) | dirs)))
        for n, d in items.items():
            check(z.read(n) == d, n)
        files_only = [n for n in listed if not n.endswith('/')]
        for suffix, banned in HOST_INVARIANTS.items():
            if flavor == suffix:
                bad = [n for n in files_only if n.lower().endswith(banned)]
                check(not bad, ('host invariant: %s must not contain %s' % (flavor, banned), bad))
        if flavor in HOST_NO_EXTENSIONLESS:
            bad = [n for n in files_only if not PurePosixPath(n).suffix]
            check(not bad, ('host invariant: %s must not contain files without an extension' % flavor, bad))
        if spec['layout'] == 'opal':
            check(all(n.endswith('.md') for n in files_only))
            check(not any(n.endswith('/') for n in listed))
            check(all(n.endswith('.md') for n in listed))
            check(all(b'\r' not in z.read(n) for n in listed))
            for n in listed:
                if len(z.read(n)) > OPAL_SIZE_WARN:
                    warnings.append('%s: %s is %d bytes; Opal rejected files above ~48-79 KB (observed)'
                                    % (archive.name, n, len(z.read(n))))
            return
        scripts = [n for n in files_only if n.endswith('.py')]
        for n in scripts:
            key = ('compile', digest(z.read(n)))
            if key not in checked:
                compile(z.read(n), n, 'exec')
                checked.add(key)
        scripts = [n for n in scripts if '/scripts/' in n and PurePosixPath(n).name in smoke]
        for n in scripts:
            if ('smoke', PurePosixPath(n).name, digest(z.read(n))) in checked:
                smoked.add(PurePosixPath(n).name)
        scripts = [n for n in scripts if ('smoke', PurePosixPath(n).name, digest(z.read(n))) not in checked]
        if not scripts:
            return
        with tempfile.TemporaryDirectory(prefix='skill-package-') as tmp:
            z.extractall(tmp)  # members were constructed above, not accepted from input
            for n in scripts:
                path = Path(tmp) / n
                if '/scripts/' in n and path.name in smoke:
                    smoked.add(path.name)
                    out = subprocess.run([sys.executable, str(path), '--version'],
                                         capture_output=True, text=True, check=True)
                    check(out.stdout.strip().endswith(version), (n, out.stdout))
                    checked.add(('smoke', path.name, digest(z.read(n))))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('output', nargs='?')
    parser.add_argument('--describe', action='store_true', help='print skill name and version without building')
    parser.add_argument('--config', default=str(REPO / 'packaging/packages.json'))
    parser.add_argument('--status', default='local candidate, not published')
    parser.add_argument('--version', action='version', version='build_packages ' + __version__)
    args = parser.parse_args()
    cfg = read_config(Path(args.config))
    name = cfg['skill']
    if not re.fullmatch(r'[a-z0-9]+(?:-[a-z0-9]+)*', name):
        raise SystemExit('Invalid skill name')
    skill_dir = repo_path('skills/' + name)
    version = skill_version(skill_dir, name)
    if args.describe:
        print(json.dumps({'skill': name, 'version': version}))
        return
    if not args.output:
        parser.error('output directory required unless --describe is used')
    for spec in cfg['packages'].values():
        meta = spec.get('metadata')
        if meta:
            got = json.loads(repo_path(meta + '/plugin.json').read_text(encoding='utf-8'))['version']
            check(got == version, (meta, got, version))
    files = source_files(skill_dir)
    output = Path(args.output).resolve()
    output.mkdir(parents=True, exist_ok=False)
    warnings = []
    smoke = set(cfg.get('smoke_version_scripts', []))
    smoked = set()
    checked = set()
    evidence = {'skill': name, 'version': version, 'status': args.status,
                'source_files': {n: digest(b) for n, b in files.items()}, 'packages': {}}
    unknown = set(cfg['packages']) - KNOWN_PACKAGES - set(cfg.get('extra_packages', []))
    if unknown:
        raise SystemExit('unknown package names %s; add them to "extra_packages" in packages.json '
                         'after checking which host rules apply' % sorted(unknown))
    for flavor, spec in cfg['packages'].items():
        items, folder_entries = build_one(spec, files, name)
        archive = output / ('%s-%s-%s.zip' % (name, version, flavor))
        dirs = write_zip(archive, items, folder_entries)
        verify(archive, flavor, spec, items, dirs, version, smoke, warnings, smoked, checked)
        evidence['packages'][archive.name] = {'sha256': digest(archive.read_bytes()),
                                              'files': len(items), 'byte_verified': True}
    missing = smoke - smoked
    if missing:
        raise SystemExit('smoke_version_scripts never found in any package: %s' % sorted(missing))
    with (output / 'SHA256SUMS.txt').open('x', encoding='utf-8', newline='\n') as f:
        f.write(''.join(r['sha256'] + '  ' + n + '\n' for n, r in sorted(evidence['packages'].items())))
    evidence['warnings'] = warnings
    with (output / 'BUILD_EVIDENCE.json').open('x', encoding='utf-8') as f:
        json.dump(evidence, f, indent=2)
    print(json.dumps({'version': version, 'packages': evidence['packages'], 'warnings': warnings}, indent=2))


if __name__ == '__main__':
    main()
