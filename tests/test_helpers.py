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

    def test_helper_versions(self):
        for s in ('check_versions.py', 'verify_release.py'):
            r = run(SKILL / 'scripts' / s, '--version')
            self.assertEqual(r.returncode, 0)


if __name__ == '__main__':
    unittest.main()
