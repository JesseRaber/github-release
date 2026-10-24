"""Channel discovery snapshots and exact-tag verification; no network/mutations."""
import importlib.util
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / 'packaging/verify_release.py'
spec = importlib.util.spec_from_file_location('channel_verifier', HELPER)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def release(tag, preview=False, draft=False, date='2026-10-24T08:00:00Z'):
    return dict(tag_name=tag, prerelease=preview, draft=draft,
                published_at=None if draft else date)


class ReleaseChannelTests(unittest.TestCase):
    def test_stable_does_not_silently_select_newer_preview(self):
        rows = [release('v9.0.0', True), release('v1.0.0', date='2026-10-20T08:00:00Z')]
        result = verifier.release_status(rows, 'stable', True)
        self.assertEqual(result['status'], 'FOUND')
        self.assertEqual(result['selected']['tag_name'], 'v1.0.0')
        self.assertEqual(result['published_preview'], 1)
        self.assertEqual(verifier.release_status(rows, 'preview', True)['selected']['tag_name'], 'v9.0.0')

    def test_preview_only_is_not_no_published_release(self):
        result = verifier.release_status([release('v1.0.0', True)], 'stable', True)
        self.assertEqual(result['status'], 'NO_STABLE_RELEASE')
        self.assertEqual(result['published_preview'], 1)
        self.assertIsNone(result['selected'])

    def test_exact_tag_never_falls_back_or_infers_channel_from_name(self):
        rows = [release('v1.0.0', True), release('v0.9.0', date='2026-10-20T08:00:00Z')]
        self.assertEqual(verifier.release_status(rows, 'stable', True, 'v1.0.0')['status'], 'CHANNEL_MISMATCH')
        self.assertEqual(verifier.release_status(rows, 'preview', True, 'v1.0.0')['status'], 'FOUND')
        self.assertEqual(verifier.release_status(rows, 'stable', True, 'v404')['status'], 'NO_TAG_MATCH')
        for bad_tag in ('', ' ', ' v1.0.0'):
            self.assertEqual(verifier.release_status(rows, 'stable', True, bad_tag)['status'], 'INCOMPLETE')

    def test_drafts_are_distinct_and_never_selected(self):
        rows = [release('v2', True, True), release('v1', False, True)]
        result = verifier.release_status(rows, 'preview', True)
        self.assertEqual(result['status'], 'NO_PUBLISHED_RELEASE')
        self.assertEqual(result['drafts'], 2)
        self.assertEqual(verifier.release_status(rows, 'preview', True, 'v2')['status'], 'DRAFT_ONLY')

    def test_partial_list_and_http_errors_never_prove_absence(self):
        for data in [[], [release('v1')]]:
            self.assertEqual(verifier.release_status(data, 'stable')['status'], 'INCOMPLETE')
        for error in [{'message': 'Not Found', 'status': '404'}, {'message': 'Forbidden', 'status': '403'}, None]:
            self.assertEqual(verifier.release_status(error, 'stable', True)['status'], 'INCOMPLETE')
        self.assertEqual(verifier.release_status([], 'stable', True)['status'], 'NO_PUBLISHED_RELEASE')

    def test_pagination_and_publication_time_not_tag_order(self):
        pages = [[release('v99', date='2026-10-20T08:00:00Z')], [release('v2')]]
        self.assertEqual(verifier.release_status(pages, 'stable', True)['selected']['tag_name'], 'v2')

    def test_unknown_flags_duplicate_tags_bad_dates_and_ties_block(self):
        bad = []
        for key, value in [('draft', None), ('prerelease', 'false'), ('published_at', 'bad'),
                           ('published_at', '2026-10-24T08:00:00'), ('tag_name', '')]:
            row = release('v1'); row[key] = value; bad.append([row])
        bad.extend([[release('v1'), release('v1')], [release('v1'), release('v2')], [None],
                    [[release('v1')], release('v2')]])
        for rows in bad:
            with self.subTest(rows=rows):
                self.assertEqual(verifier.release_status(rows, 'stable', True)['status'], 'INCOMPLETE')

    def test_exact_tag_channel_guard_rejects_wrong_or_unknown_state(self):
        with tempfile.TemporaryDirectory() as folder:
            for preview, channel, passed in [(True, 'preview', True), (False, 'stable', True),
                                             (True, 'stable', False), (None, 'preview', False)]:
                out = []
                row = dict(tag_name='v1.0.0', draft=False, prerelease=preview, immutable=True, assets=[])
                verifier.check_release_json(row, Path(folder), '1.0.0', out, True, True,
                                            expect_channel=channel)
                self.assertEqual(not any(s == 'FAIL' for s, _ in out), passed)
            out = []
            verifier.check_release_json(release('vOTHER', True), Path(folder), '1.0.0', out,
                                        expect_channel='preview')
            self.assertTrue(any(s == 'FAIL' and 'tag' in msg for s, msg in out))

    def test_cli_snapshot_modes_exit_codes_and_no_writes(self):
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / 'snapshot.json'
            for data, flags, code, status in [
                ([release('v1', True)], ['--list-complete'], 0, 'FOUND'),
                ([release('v1')], ['--list-complete'], 1, 'NO_PREVIEW_RELEASE'),
                ([], [], 2, 'INCOMPLETE'),
                ({'message': 'Not Found'}, ['--list-complete'], 2, 'INCOMPLETE')]:
                path.write_text(json.dumps(data), encoding='utf-8')
                before = path.read_bytes()
                result = subprocess.run([sys.executable, str(HELPER), '--release-list-json', str(path),
                                         '--channel', 'preview'] + flags, capture_output=True, text=True)
                self.assertEqual(result.returncode, code, result.stdout + result.stderr)
                self.assertEqual(json.loads(result.stdout)['status'], status)
                self.assertEqual(path.read_bytes(), before)
                self.assertEqual(list(Path(folder).iterdir()), [path])

    def test_cli_does_not_mix_snapshot_with_asset_verification(self):
        for args in [ ['--release-list-json', 'missing.json'],
                      ['--release-list-json', 'missing.json', '--channel', 'stable', '--assets', '.'],
                      ['--channel', 'preview'], ['--expect-channel', 'preview', '--assets', '.'] ]:
            result = subprocess.run([sys.executable, str(HELPER)] + args, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)

    def test_packaged_and_repo_helpers_are_exact_copies(self):
        self.assertEqual(HELPER.read_bytes(), (ROOT / 'skills/github-release/scripts/verify_release.py').read_bytes())
