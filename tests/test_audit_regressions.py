"""Release correctness regressions from the independently reproduced audit defects."""
import importlib.util
import json
from pathlib import Path
import re
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / 'packaging' / (name + '.py'))
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


V = module('verify_release')
B = module('build_packages')
C = module('check_versions')


def failed(out):
    return any(status == 'FAIL' for status, _ in out)


class VerificationTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.assets = Path(self.tmp.name)
        self.archive = self.assets / 'demo-1.0.0-UNIVERSAL-skill.zip'
        with zipfile.ZipFile(self.archive, 'w') as z:
            z.writestr('demo/SKILL.md', 'test')
        self.digest = V.sha256(self.archive)
        self.sums = self.assets / V.SUMS
        self.sums.write_text(self.digest + '  ' + self.archive.name + '\n', encoding='utf-8')

    def test_manifest_rejects_empty_duplicate_malformed_unsafe_and_no_archive(self):
        for text in ('', '\n', 'not-a-digest  x.zip\n', 'a\n',
                     self.digest + '  ../x.zip\n', self.digest + '  x.txt\n',
                     self.sums.read_text() * 2):
            with self.subTest(text=text):
                self.sums.write_text(text, encoding='utf-8')
                out = []
                V.check_sums(self.assets, out)
                self.assertTrue(failed(out), out)

    def test_unlisted_nonzip_fails(self):
        (self.assets / 'extra.txt').write_text('not hashed', encoding='utf-8')
        out = []
        V.check_sums(self.assets, out)
        self.assertTrue(failed(out))

    def test_local_evidence_validated_and_tampering_fails(self):
        evidence = self.assets / V.LOCAL_EVIDENCE
        evidence.write_text(json.dumps({'packages': {self.archive.name: {'sha256': self.digest}}}), encoding='utf-8')
        out = []
        V.check_sums(self.assets, out)
        self.assertFalse(failed(out), out)
        data = {'assets': [{'name': n, 'digest': 'sha256:' + V.sha256(self.assets / n)}
                           for n in (self.archive.name, V.SUMS)]}
        out = []
        V.check_release_json(data, self.assets, None, out)
        self.assertFalse(failed(out), out)  # local evidence is not a published asset
        evidence.write_text('{}', encoding='utf-8')
        out = []
        V.check_sums(self.assets, out)
        self.assertTrue(failed(out))

    def test_missing_digest_requires_explicit_opt_in_and_still_checks_size(self):
        data = {'assets': [{'name': self.archive.name, 'size': self.archive.stat().st_size}]}
        # Include the checksum asset so local set agreement is also checked.
        data['assets'].append({'name': V.SUMS, 'size': self.sums.stat().st_size})
        out = []
        V.check_release_json(data, self.assets, None, out)
        self.assertTrue(failed(out))
        out = []
        V.check_release_json(data, self.assets, None, out, allow_missing_digest=True)
        self.assertFalse(failed(out), out)
        self.assertTrue(any(status == 'WARN' for status, _ in out))
        data['assets'][0]['size'] += 1
        out = []
        V.check_release_json(data, self.assets, None, out, allow_missing_digest=True)
        self.assertTrue(failed(out))

    def test_candidate_missing_or_inconsistent_records_fail(self):
        out = []
        actual = V.check_sums(self.assets, out)
        V.check_candidate(self.assets / 'absent', self.assets, actual, out)
        self.assertTrue(failed(out))
        out = []
        V.check_candidate(self.assets, self.assets, actual, out)
        self.assertTrue(failed(out))  # candidate evidence is required

    def test_release_metadata_duplicate_and_traversal_rejected(self):
        path = self.assets / 'metadata.json'
        for entries in ([{'name': '../outside'}], [{'name': 'x'}, {'name': 'x'}], []):
            path.write_text(json.dumps({'assets': entries}), encoding='utf-8')
            out = []
            self.assertIsNone(V.load_release(path, out))
            self.assertTrue(failed(out))


class WorkflowLintTests(unittest.TestCase):
    def lint(self, script):
        with tempfile.TemporaryDirectory() as t:
            path = Path(t) / 'release.yml'
            path.write_text('run: |\n' + '\n'.join('  ' + line for line in script.splitlines()) + '\n', encoding='utf-8')
            out = []
            C.check_workflow(path, out)
            return out

    def test_quoted_hash_cannot_hide_undraft(self):
        out = self.lint('gh release create v1 --draft\necho "Issue #1"; gh release edit v1 --draft=false\ngh release view v1')
        self.assertTrue(failed(out), out)

    def test_quoted_title_continuation_and_valid_draft_forms(self):
        for flag in ('--draft', '--draft=true', '-d'):
            with self.subTest(flag=flag):
                script = 'gh release create v1 --title "Release #1" \\\n+  ' + flag + '\ngh release view v1 # real comment'
                out = self.lint(script)
                self.assertFalse(failed(out), out)

    def test_delete_upload_and_api_alternatives_fail(self):
        for command in ('gh release delete v1', 'gh release delete-asset v1 x',
                        'gh release upload v1 x --clobber', 'gh api repos/o/r/releases/1 -f draft=false'):
            out = self.lint('gh release create v1 --draft\ngh release view v1\n' + command)
            self.assertTrue(failed(out), command)

    def test_short_undraft_and_equals_flags_fail(self):
        for suffix in ('-d=false', '-d false', '--clobber=true', '--generate-notes=true'):
            out = self.lint('gh release create v1 --draft ' + suffix + '\ngh release view v1')
            self.assertTrue(failed(out), suffix)

    def test_comment_and_echo_are_not_create_commands(self):
        out = self.lint('# gh release create v1 --draft\necho "gh release create v1 --draft"\ngh release view v1')
        self.assertTrue(failed(out), out)


class BuilderSafetyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.repo_patch = patch.object(B, 'REPO', self.root)
        self.repo_patch.start()
        self.addCleanup(self.repo_patch.stop)

    def test_source_and_archive_paths_cannot_escape(self):
        for path in ('../secret', '/secret', 'C:/secret', 'a\\b', 'a/../b', './x', 'a//b'):
            with self.subTest(path=path):
                with self.assertRaises(ValueError):
                    B.repo_path(path)
                with self.assertRaises(ValueError):
                    B.write_zip(self.root / 'bad.zip', {path: b'x'}, False)

    def test_parent_links_and_metadata_links_refused(self):
        folder = self.root / 'linked'
        folder.mkdir()
        (folder / 'x.json').write_text('{}', encoding='utf-8')
        original = Path.is_symlink
        with patch.object(Path, 'is_symlink', lambda p: p == folder or original(p)):
            with self.assertRaises(ValueError):
                B.repo_path('linked/x.json')
            with self.assertRaises(ValueError):
                B.build_one({'layout': 'plugin', 'metadata': 'linked'}, {'SKILL.md': b'x'}, 'demo')

    def test_broken_source_link_refused_before_file_filter(self):
        skill = self.root / 'skills' / 'demo'
        skill.mkdir(parents=True)
        link = skill / 'broken'
        link.write_text('placeholder', encoding='utf-8')
        original_link, original_file = Path.is_symlink, Path.is_file
        with patch.object(Path, 'is_symlink', lambda p: p == link or original_link(p)), \
             patch.object(Path, 'is_file', lambda p: False if p == link else original_file(p)):
            with self.assertRaises(ValueError):
                B.source_files(skill)

    def test_archive_target_and_added_source_traversal_refused(self):
        for spec in ({'layout': 'skill', 'add': {'../escape': 'LICENSE'}},
                     {'layout': 'skill', 'add': {'LICENSE': '../secret'}}):
            with self.assertRaises(ValueError):
                B.build_one(spec, {'SKILL.md': b'x'}, 'demo')

    def test_regular_file_type_and_readable_payload(self):
        archive = self.root / 'good.zip'
        B.write_zip(archive, {'demo/file.txt': b'payload'}, True)
        with zipfile.ZipFile(archive) as z:
            self.assertEqual(stat.S_IFMT(z.getinfo('demo/file.txt').external_attr >> 16), stat.S_IFREG)
            self.assertEqual(z.read('demo/file.txt'), b'payload')

    def test_case_and_dotfile_filtering(self):
        self.assertTrue(B.excluded('helper.PS1', {'exclude_suffix': ['.ps1']}))
        self.assertTrue(B.excluded('.env', {'exclude_no_suffix': True}))
        self.assertFalse(B.excluded('.config.json', {'exclude_no_suffix': True}))

    def test_frontmatter_delimiters_and_body_version(self):
        data = b'---\nname: demo\ndescription: "one --- two"\nmetadata:\n  version: "1.2.3"\n---\n  version: "9.9.9"\n'
        skill = self.root / 'skills/demo'
        skill.mkdir(parents=True)
        (skill / 'SKILL.md').write_bytes(data)
        self.assertEqual(B.skill_version(skill, 'demo'), '1.2.3')
        self.assertIn('one --- two', B.opal_skill_md(data).decode())
        (skill / 'SKILL.md').write_bytes(b'---\nname: demo\ndescription: x\n---\nmetadata:\n  version: "9.9.9"\n')
        with self.assertRaises(SystemExit):
            B.skill_version(skill, 'demo')

    def test_opal_multiline_rejected_instead_of_truncated(self):
        for desc in ('description: first\n  second', 'description: >\n  first', 'description: |\n  first',
                     'description: "first\nsecond"', "description: 'first\nsecond'"):
            with self.assertRaises(ValueError):
                B.opal_skill_md(('---\nname: demo\n' + desc + '\n---\nbody\n').encode())

    def test_invalid_template_python_is_checked(self):
        items = {'demo/templates/build_packages.py': b'not python ???'}
        archive = self.root / 'template.zip'
        dirs = B.write_zip(archive, items, True)
        with self.assertRaises(SyntaxError):
            B.verify(archive, 'UNIVERSAL-skill', {'layout': 'skill'}, items, dirs, '1.0.0', set(), [], set())


class PreviousVersionTests(unittest.TestCase):
    def test_changelog_inference_and_boundaries(self):
        with tempfile.TemporaryDirectory() as t:
            root = Path(t)
            (root / 'CHANGELOG.md').write_text('## 2.0.0\n\n## 1.0.0\n', encoding='utf-8')
            self.assertEqual(C.previous_from_changelog(root, '2.0.0'), '1.0.0')
            with self.assertRaises(ValueError):
                C.previous_from_changelog(root, '3.0.0')
            (root / 'test.md').write_text('1.0.0.1 rev1.0.0 dev1.0.0\n', encoding='utf-8')
            out = []
            C.check_previous(root, {'history': ['CHANGELOG.md']}, '1.0.0', out)
            self.assertFalse(failed(out), out)
            (root / 'test.md').write_text('Loaded v1.0.0.\n', encoding='utf-8')
            out = []
            C.check_previous(root, {'history': ['CHANGELOG.md']}, '1.0.0', out)
            self.assertTrue(failed(out), out)


if __name__ == '__main__':
    unittest.main()
