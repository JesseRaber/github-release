"""Regression tests for the github-release builder and helpers. Standard library only."""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

REPO = Path(__file__).resolve().parents[1]
SKILL = REPO / 'skills' / 'github-release'
PY = sys.executable


def run(*args):
    return subprocess.run([PY, *map(str, args)], capture_output=True, text=True)


def sha(p):
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


class BuilderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = Path(tempfile.mkdtemp(prefix='gr-test-'))
        for n in ('a', 'b'):
            r = run(REPO / 'packaging/build_packages.py', cls.tmp / n)
            assert r.returncode == 0, r.stderr
        cls.version = json.loads(r.stdout)['version']

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.tmp)

    def test_deterministic(self):
        a = (self.tmp / 'a' / 'SHA256SUMS.txt').read_text()
        b = (self.tmp / 'b' / 'SHA256SUMS.txt').read_text()
        self.assertEqual(a, b)
        self.assertEqual(len(a.splitlines()), 6)

    def test_template_matches_packaged_copy(self):
        self.assertEqual(sha(REPO / 'packaging/build_packages.py'), sha(SKILL / 'templates/build_packages.py'))
        self.assertEqual(sha(REPO / 'packaging/check_versions.py'), sha(SKILL / 'scripts/check_versions.py'))
        self.assertEqual(sha(REPO / 'packaging/verify_release.py'), sha(SKILL / 'scripts/verify_release.py'))
        for wf in ('release.yml', 'ci.yml'):
            self.assertEqual(sha(REPO / '.github/workflows' / wf), sha(SKILL / 'templates' / wf))

    def test_windows_build_identical(self):
        # Simulate a Windows builder: on win32 zipfile.ZipInfo defaults create_system to 0.
        out = self.tmp / 'win'
        code = ('import sys, runpy, zipfile; orig = zipfile.ZipInfo.__init__\n'
                'def init(self, *a, **k):\n    orig(self, *a, **k); self.create_system = 0\n'
                'zipfile.ZipInfo.__init__ = init\n'
                'sys.argv = ["build_packages.py", %r]; '
                'runpy.run_path(%r, run_name="__main__")') % (str(out), str(REPO / 'packaging/build_packages.py'))
        r = subprocess.run([PY, '-c', code], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual((out / 'SHA256SUMS.txt').read_text(), (self.tmp / 'a' / 'SHA256SUMS.txt').read_text())

    def test_gemini_omits_yml(self):
        z = zipfile.ZipFile(self.tmp / 'a' / ('github-release-%s-gemini-apps-only.zip' % self.version))
        self.assertFalse([n for n in z.namelist() if n.endswith(('.yml', '.yaml', '.ps1'))])
        self.assertIn('github-release/scripts/verify_release.py', z.namelist())

    def test_gemini_omits_extensionless(self):
        z = zipfile.ZipFile(self.tmp / 'a' / ('github-release-%s-gemini-apps-only.zip' % self.version))
        files = [n for n in z.namelist() if not n.endswith('/')]
        self.assertFalse([n for n in files if '.' not in n.rsplit('/', 1)[-1]])
        u = zipfile.ZipFile(self.tmp / 'a' / ('github-release-%s-UNIVERSAL-skill.zip' % self.version))
        self.assertIn('github-release/templates/gitattributes', u.namelist())

    def test_opal_flat_lf(self):
        z = zipfile.ZipFile(self.tmp / 'a' / ('github-release-%s-opal-only.zip' % self.version))
        names = z.namelist()
        self.assertTrue(all(n.endswith('.md') and not n.endswith('/') for n in names))
        self.assertTrue(all(b'\r' not in z.read(n) for n in names))
        front = z.read('github-release/SKILL.md').decode().split('---')[1]
        self.assertEqual([l.split(':')[0] for l in front.strip().splitlines()], ['name', 'description'])

    def test_verify_release_pass_and_tamper(self):
        assets = self.tmp / 'a'
        r = run(SKILL / 'scripts/verify_release.py', '--assets', assets, '--version', self.version,
                '--candidate', self.tmp / 'b')
        self.assertEqual(r.returncode, 0, r.stdout)
        bad = self.tmp / 'bad'
        shutil.copytree(assets, bad)
        z = next(bad.glob('*opal-only.zip'))
        z.write_bytes(z.read_bytes() + b'x')
        r = run(SKILL / 'scripts/verify_release.py', '--assets', bad, '--candidate', self.tmp / 'b')
        self.assertEqual(r.returncode, 1)
        self.assertIn('DIFFERS', r.stdout)


class CheckVersionsTests(unittest.TestCase):
    def test_repo_versions_and_workflow(self):
        v = json.loads((REPO / '.claude-plugin/plugin.json').read_text())['version']
        r = run(SKILL / 'scripts/check_versions.py', '--repo', REPO, '--version', v,
                '--workflow', '.github/workflows/release.yml')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_wrong_version_fails(self):
        r = run(SKILL / 'scripts/check_versions.py', '--repo', REPO, '--version', '9.9.9')
        self.assertEqual(r.returncode, 1)

    def test_clobber_workflow_fails(self):
        with tempfile.TemporaryDirectory() as t:
            wf = Path(t) / 'release.yml'
            wf.write_text('run: gh release upload v1 dist/*.zip --clobber\n', encoding='utf-8')
            r = run(SKILL / 'scripts/check_versions.py', '--repo', REPO, '--version',
                    json.loads((REPO / '.claude-plugin/plugin.json').read_text())['version'], '--workflow', wf)
            self.assertEqual(r.returncode, 1)
            self.assertIn('FAIL workflow never replaces existing assets', r.stdout)

    def test_undraft_workflow_fails(self):
        with tempfile.TemporaryDirectory() as t:
            wf = Path(t) / 'release.yml'
            wf.write_text('run: |\n  gh release create v1 dist/*.zip\n  gh release edit v1 --draft=false\n'
                          '# --draft\n  gh release view v1\n', encoding='utf-8')
            r = run(SKILL / 'scripts/check_versions.py', '--repo', REPO, '--version',
                    json.loads((REPO / '.claude-plugin/plugin.json').read_text())['version'], '--workflow', wf)
            self.assertEqual(r.returncode, 1)
            self.assertIn('FAIL workflow every `gh release create` uses --draft', r.stdout)

    def test_version_prefix_not_matched(self):
        with tempfile.TemporaryDirectory() as t:
            (Path(t) / 'v.md').write_text('Loaded v1.2.10\n', encoding='utf-8')
            cfg = Path(t) / 'c.json'
            cfg.write_text(json.dumps({'files': [{'path': 'v.md', 'pattern': 'v{v}'}]}), encoding='utf-8')
            r = run(SKILL / 'scripts/check_versions.py', '--repo', t, '--version', '1.2.1', '--config', cfg)
            self.assertIn('FAIL v.md does not match', r.stdout)

    def test_release_list_json_rejected(self):
        with tempfile.TemporaryDirectory() as t:
            j = Path(t) / 'rel.json'
            j.write_text('[{"tag_name": "v1"}]', encoding='utf-8')
            r = run(SKILL / 'scripts/verify_release.py', '--assets', REPO, '--release-json', j)
            self.assertEqual(r.returncode, 1)
            self.assertIn('ONE release object', r.stdout)

    def test_extra_root_previous_scan(self):
        with tempfile.TemporaryDirectory() as td:
            wiki = Path(td) / 'wiki'
            wiki.mkdir()
            (wiki / 'Home.md').write_text('Current release: v0.0.1\n', encoding='utf-8')
            v = json.loads((REPO / '.claude-plugin/plugin.json').read_text())['version']
            r = run(SKILL / 'scripts/check_versions.py', '--repo', REPO, '--version', v,
                    '--previous', '0.0.1', '--extra-root', wiki)
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('wiki/Home.md', r.stdout)
            r = run(SKILL / 'scripts/check_versions.py', '--repo', REPO, '--version', v,
                    '--previous', '0.0.1', '--extra-root', Path(td) / 'missing')
            self.assertNotEqual(r.returncode, 0)
            self.assertIn('extra root not found', r.stdout)

    def test_helper_versions(self):
        for s in ('check_versions.py', 'verify_release.py', 'check_skill_duplicates.py'):
            r = run(SKILL / 'scripts' / s, '--version')
            self.assertEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()


DUP = SKILL / 'scripts' / 'check_skill_duplicates.py'


def write_skill(folder, name, version):
    folder.mkdir(parents=True, exist_ok=True)
    (folder / 'SKILL.md').write_text(
        '---\nname: %s\ndescription: test\nmetadata:\n  version: "%s"\n---\n# x\n' % (name, version),
        encoding='utf-8')


class DuplicateSkillTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp(prefix='gr-dup-')) / 'skills'
        write_skill(self.root / 'demo', 'demo', '1.7.1')
        write_skill(self.root / 'other', 'other', '0.1.0')

    def tearDown(self):
        shutil.rmtree(self.root.parent)

    def test_clean_install_passes(self):
        r = run(DUP, self.root, '--name', 'demo', '--expect-version', '1.7.1')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('PASS', r.stdout)

    def test_backup_inside_scanned_folder_fails(self):
        # The 2026-10-09 Codex incident: old copy moved to skills/_backups/<name>.pre-v<new>-<stamp>.
        write_skill(self.root / '_backups' / 'demo.pre-v1.7.1-20261009', 'demo', '1.7.0')
        r = run(DUP, self.root, '--name', 'demo', '--expect-version', '1.7.1', '--json')
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        out = json.loads(r.stdout)
        self.assertEqual(out['result'], 'FAIL')
        paths = sorted(e['path'] for e in out['duplicates']['demo'])
        self.assertEqual(len(paths), 2)
        self.assertTrue(any('_backups' in p for p in paths))
        backup = [e for e in out['entries'] if '_backups' in e['path']][0]
        self.assertTrue(backup['backup_like_path'])
        self.assertEqual(backup['version'], '1.7.0')
        # Without --name the duplicate is still a failure.
        self.assertEqual(run(DUP, self.root).returncode, 1)

    def test_renamed_backup_is_not_loaded(self):
        b = self.root / '_backups' / 'demo.pre-v1.7.1-20261009'
        write_skill(b, 'demo', '1.7.0')
        (b / 'SKILL.md').rename(b / 'SKILL.backup-not-loaded.md')
        r = run(DUP, self.root, '--name', 'demo', '--expect-version', '1.7.1')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)

    def test_backup_beside_skills_folder_passes(self):
        write_skill(self.root.parent / 'skill-backups' / 'demo.pre-v1.7.1', 'demo', '1.7.0')
        self.assertEqual(run(DUP, self.root, '--name', 'demo').returncode, 0)
        # Scanning both folders would see it, proving the check covers every root given.
        self.assertEqual(run(DUP, self.root, self.root.parent / 'skill-backups', '--name', 'demo').returncode, 1)

    def test_wrong_version_fails(self):
        r = run(DUP, self.root, '--name', 'demo', '--expect-version', '1.8.0')
        self.assertEqual(r.returncode, 1)
        self.assertIn('expected 1.8.0', r.stdout)

    def test_missing_skill_and_bad_root(self):
        self.assertEqual(run(DUP, self.root, '--name', 'absent').returncode, 1)
        self.assertEqual(run(DUP, self.root / 'nope').returncode, 2)

    def test_lowercase_filename_counts(self):
        d = self.root / 'copy'
        write_skill(d, 'demo', '1.7.0')
        (d / 'SKILL.md').rename(d / 'skill.md')
        self.assertEqual(run(DUP, self.root, '--name', 'demo').returncode, 1)

    def test_read_only(self):
        write_skill(self.root / '_backups' / 'x', 'demo', '1.7.0')
        before = sorted((str(p), p.stat().st_mtime_ns) for p in self.root.rglob('*'))
        run(DUP, self.root, '--name', 'demo')
        after = sorted((str(p), p.stat().st_mtime_ns) for p in self.root.rglob('*'))
        self.assertEqual(before, after)


CV = SKILL / 'scripts' / 'check_versions.py'
VR = SKILL / 'scripts' / 'verify_release.py'


def mini_repo(t, notes_text, version='1.0.0'):
    """A minimal repository with one touch point and a notes file."""
    root = Path(t)
    (root / 'packaging').mkdir()
    (root / 'v.md').write_text('v%s\n' % version, encoding='utf-8')
    (root / 'packaging' / ('RELEASE_NOTES_v%s.md' % version)).write_text(notes_text, encoding='utf-8', newline='\n')
    cfg = root / 'cfg.json'
    cfg.write_text(json.dumps({'files': [{'path': 'v.md', 'pattern': 'v{v}'}]}), encoding='utf-8')
    return root, cfg


class NotesLintTests(unittest.TestCase):
    def check(self, text):
        with tempfile.TemporaryDirectory() as t:
            root, cfg = mini_repo(t, text)
            return run(CV, '--repo', root, '--version', '1.0.0', '--config', cfg)

    def test_clean_notes_pass(self):
        r = self.check('# demo 1.0.0\n\n## Changes\n\n- Adds a lint.\n')
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('PASS notes body lint', r.stdout)

    def test_candidate_status_fails(self):
        # Observed: two immutable releases whose body said "(candidate)" and "not released".
        for text in ('# demo 1.0.0 (candidate)\n', 'Status: local candidate; not committed\n',
                     'This is not released yet.\n', 'Released 2026-10-06.\n', '## Changes\n\n- \n',
                     '# SKILL-NAME X.Y.Z\n', 'Items: TBD\n', '## Verification required before release\n'):
            r = self.check(text)
            self.assertEqual(r.returncode, 1, text + r.stdout)

    def test_internal_ids_warn_only(self):
        r = self.check('- Fix (session 9ea792fb-1111-2222-3333-444455556666, R-051).\n')
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('WARN', r.stdout)
        self.assertIn('session UUID', r.stdout)
        self.assertIn('register/tracker row ID', r.stdout)


class RecordEncodingTests(unittest.TestCase):
    def run_with(self, name, data):
        with tempfile.TemporaryDirectory() as t:
            root, cfg = mini_repo(t, '# demo 1.0.0\n')
            (root / name).write_bytes(data)
            return run(CV, '--repo', root, '--version', '1.0.0', '--config', cfg)

    def test_clean_record_passes(self):
        r = self.run_with('CHANGELOG.md', b'# Changelog\n')
        self.assertEqual(r.returncode, 0, r.stdout)

    def test_damaged_records_fail(self):
        # Observed: a PowerShell 5.1 `>>` append wrote UTF-16LE (NUL bytes) into a UTF-8 file.
        for data, label in ((b'\xef\xbb\xbf# x\n', 'BOM'), (b'# x\n' + 'row\n'.encode('utf-16-le'), 'NUL'),
                            (b'# x\r\n', 'CRLF'), (b'# \xff\n', 'not UTF-8')):
            r = self.run_with('CHANGELOG.md', data)
            self.assertEqual(r.returncode, 1, label)
            self.assertIn(label, r.stdout)

    def test_install_log_single_header(self):
        head = b'| Date (TZ) | Version |\n|---|---|\n'
        self.assertEqual(self.run_with('HOST_INSTALL_LOG.md', head).returncode, 0)
        r = self.run_with('HOST_INSTALL_LOG.md', head + head)
        self.assertEqual(r.returncode, 1)
        self.assertIn('repeated identical table header', r.stdout)
        # A schema change appends a new table with a different header: allowed.
        newer = b'\n| Date (TZ) | Version | Channel |\n|---|---|---|\n'
        self.assertEqual(self.run_with('HOST_INSTALL_LOG.md', head + newer).returncode, 0)


class DriftTests(unittest.TestCase):
    def test_this_repo_has_no_drift(self):
        v = json.loads((REPO / '.claude-plugin/plugin.json').read_text())['version']
        r = run(CV, '--repo', REPO, '--version', v, '--drift-against', SKILL)
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('drift: 0 stale copies', r.stdout)

    def test_stale_copy_fails(self):
        with tempfile.TemporaryDirectory() as t:
            root, cfg = mini_repo(t, '# demo 1.0.0\n')
            (root / 'packaging' / 'check_versions.py').write_text('# old copy\n', encoding='utf-8')
            (root / 'HOST_INSTALL_LOG.md').write_text('| Date | Version |\n|---|---|\n', encoding='utf-8')
            r = run(CV, '--repo', root, '--version', '1.0.0', '--config', cfg, '--drift-against', SKILL)
            self.assertEqual(r.returncode, 1)
            self.assertIn('packaging/check_versions.py differs from', r.stdout)
            self.assertIn('HOST_INSTALL_LOG.md current (last) table header differs', r.stdout)


class VerifyReleaseMetadataTests(unittest.TestCase):
    def setUp(self):
        self.t = Path(tempfile.mkdtemp(prefix='gr-vr-'))
        self.assets = self.t / 'assets'
        self.assets.mkdir()
        z = self.assets / 'demo-1.0.0-UNIVERSAL-skill.zip'
        with zipfile.ZipFile(z, 'w') as zf:
            zf.writestr('demo/SKILL.md', 'x')
        (self.assets / 'SHA256SUMS.txt').write_text('%s  %s\n' % (sha(z), z.name), encoding='utf-8')
        self.notes = self.t / 'RELEASE_NOTES_v1.0.0.md'
        self.notes.write_text('# demo 1.0.0\n\n- Change.\n', encoding='utf-8')
        self.rel = {'tag_name': 'v1.0.0', 'draft': False, 'immutable': True, 'name': 'demo v1.0.0',
                    'author': {'login': 'github-actions[bot]'}, 'body': '# demo 1.0.0\r\n\r\n- Change.\r\n',
                    'assets': [{'name': n, 'state': 'uploaded', 'digest': 'sha256:' + sha(self.assets / n)}
                               for n in (z.name, 'SHA256SUMS.txt')]}

    def tearDown(self):
        shutil.rmtree(self.t)

    def verify(self, **change):
        rel = dict(self.rel, **change)
        j = self.t / 'rel.json'
        j.write_text(json.dumps(rel), encoding='utf-8')
        return run(VR, '--assets', self.assets, '--version', '1.0.0', '--release-json', j, '--notes', self.notes)

    def test_workflow_release_passes(self):
        r = self.verify()
        self.assertEqual(r.returncode, 0, r.stdout)
        self.assertIn('downloaded 2 of 2 listed assets', r.stdout)
        self.assertIn('release author=github-actions[bot]', r.stdout)

    def test_hand_created_or_bad_title_fails(self):
        r = self.verify(author={'login': 'someone'})
        self.assertEqual(r.returncode, 1)
        self.assertIn('hand-created', r.stdout)
        r = self.verify(name='v1.0.0 draft')
        self.assertEqual(r.returncode, 1)

    def test_incomplete_download_reported_first(self):
        assets = list(self.rel['assets']) + [{'name': 'extra.zip', 'state': 'uploaded', 'digest': 'sha256:00'}]
        r = self.verify(assets=assets)
        self.assertEqual(r.returncode, 1)
        first = [l for l in r.stdout.splitlines() if l.strip()][0]
        self.assertIn('downloaded 2 of 3 listed assets', first)

    def test_body_edit_policy(self):
        ok = self.rel['body'] + '\n## Known issues (added 2026-10-10)\n\n- See 1.0.1.\n'
        self.assertEqual(self.verify(body=ok).returncode, 0)
        r = self.verify(body='# demo 1.0.0\n\n- Different change.\n')
        self.assertEqual(r.returncode, 1)
        self.assertIn('release body differs', r.stdout)


class CiTemplateTests(unittest.TestCase):
    def test_ci_runs_on_release_branches_and_dispatch(self):
        text = (SKILL / 'templates' / 'ci.yml').read_text(encoding='utf-8')
        self.assertIn('workflow_dispatch', text)
        self.assertIn("'release/**'", text)

    def test_actions_pinned_by_sha(self):
        import re
        for wf in ('ci.yml', 'release.yml'):
            for line in (SKILL / 'templates' / wf).read_text(encoding='utf-8').splitlines():
                if 'uses: actions/' in line:
                    self.assertRegex(line, r'@[0-9a-f]{40} # v\d+\.\d+\.\d+$', line)
