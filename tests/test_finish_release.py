"""Offline orchestration tests: replace only process/network boundary functions.

Run a copy of the production script in pwsh with deterministic API state. No
GitHub calls, git commands, merge, tag or publication can escape this harness.
"""
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/github-release/scripts/Finish-Release.ps1'
HEAD, BASE, MERGE, TREE = ('a' * 40, 'b' * 40, 'c' * 40, 'd' * 40)

MOCK = r'''
$fixture = Get-Content -Raw (Join-Path $PSScriptRoot 'fixture.json') | ConvertFrom-Json -AsHashtable
$script:mutations = [Collections.Generic.List[string]]::new()
$script:merged = $fixture.merged
$script:tagged = $fixture.tagged
$script:published = $fixture.published
function Save-Mutation([string]$value) {
    $script:mutations.Add($value)
    [IO.File]::WriteAllText((Join-Path $PSScriptRoot 'mutations.json'), (ConvertTo-Json -InputObject @($script:mutations)))
}
function Get-Command { param($Name, $CommandType, $ErrorAction) [pscustomobject]@{ Source = 'MOCK-ONLY' } }
function Get-Asset($asset, [string]$dir) {
    $path = Join-Path $dir $asset.name
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot $asset.name) -Destination $path
    return $path
}
function git {
    $global:LASTEXITCODE = 0
    if ($args -contains 'push') { Save-Mutation 'tag'; $script:tagged = $true }
}
function ApiOptional([string]$path) {
    if ($fixture.tagReadError) { throw 'simulated HTTP 403' }
    if (-not $script:tagged) { return $null }
    return [pscustomobject]@{ object = [pscustomobject]@{ sha = $fixture.merge; type = 'commit' } }
}
function ApiList([string]$path) {
    if ($path -eq 'releases?per_page=100') {
        if ($script:tagged) { return Invoke-GhJson @('api', 'repos/o/r/releases/1') }
        return @()
    }
    return [pscustomobject]@{ check_runs = @($fixture.checks | ForEach-Object { [pscustomobject]$_ }) }
}
function Invoke-GhJson([string[]]$ghArgs, [switch]$AllowNotFound) {
    $joined = $ghArgs -join ' '
    if ($joined -match '-X PUT') { Save-Mutation 'merge'; $script:merged = $true; return [pscustomobject]@{ merged = $true; sha = $fixture.merge } }
    if ($joined -match '-X PATCH') { Save-Mutation 'publish'; $script:published = $true; return $null }
    $path = $ghArgs[-1] -replace '^repos/o/r/?', ''
    if ($path -eq 'user') { return [pscustomobject]@{ login = 'owner'; id = 1; name = 'Owner' } }
    if (-not $path) { return [pscustomobject]@{ private = $true; default_branch = 'main' } }
    if ($path -match '^pulls/') {
        return [pscustomobject]@{ head = [pscustomobject]@{sha = $fixture.head}; base = [pscustomobject]@{sha = $fixture.base; ref = 'main'; repo = [pscustomobject]@{full_name = 'o/r'}}; merged = $script:merged; state = 'open'; merge_commit_sha = $fixture.merge; title = 'Release' }
    }
    if ($path -eq 'immutable-releases') { return [pscustomobject]@{enabled = $fixture.repoImmutable} }
    if ($path -match '^branches/') { return [pscustomobject]@{ required_status_checks = [pscustomobject]@{contexts = @('test')} } }
    if ($path -match '^git/commits/') {
        return [pscustomobject]@{tree = [pscustomobject]@{sha = $(if ($fixture.wrongTree -and $path.EndsWith($fixture.merge)) {'wrong'} else {$fixture.tree})} }
    }
    if ($path -match '^git/ref/heads/') { return [pscustomobject]@{object = [pscustomobject]@{sha = $fixture.merge}} }
    if ($path -match '^git/ref/tags/') { return ApiOptional $path }
    if ($path -match '^actions/workflows/') { return [pscustomobject]@{workflow_runs = @([pscustomobject]@{id=10;head_sha=$fixture.merge;head_branch='v1.3.0';path='.github/workflows/release.yml';status='completed';conclusion=$fixture.workflow})} }
    if ($path -match '^actions/runs') { return [pscustomobject]@{workflow_runs = @()} }
    if ($path -match '^releases/') {
        return [pscustomobject]@{ id = 1; tag_name = 'v1.3.0'; author = [pscustomobject]@{login='github-actions[bot]'}; name = 'Skill v1.3.0'; prerelease = $false; draft = -not $script:published; body = $fixture.notes; immutable = $fixture.immutable; published_at = 'date'; html_url = 'https://example.invalid'; assets = @([pscustomobject]@{name='a.zip';id=1},[pscustomobject]@{name='SHA256SUMS.txt';id=2}) }
    }
    throw "Unexpected API (no network permitted): $joined"
}
'''


class FinishReleaseBehaviorTests(unittest.TestCase):
    def run_case(self, **changes):
        pwsh = shutil.which('pwsh')
        if not pwsh:
            self.skipTest('PowerShell 7 required for offline orchestration tests')
        with tempfile.TemporaryDirectory() as tmp:
            d = Path(tmp)
            fixture = dict(head=HEAD, base=BASE, merge=MERGE, tree=TREE,
                           merged=False, tagged=False, published=False,
                           tagReadError=False, wrongTree=False, notes='Reviewed notes',
                           immutable=True, repoImmutable=True, workflow='success',
                           checks=[dict(id=1, name='test', status='completed', conclusion='success')])
            fixture.update(changes)
            payload = b'fixture package bytes; no executable release commands'
            (d / 'a.zip').write_bytes(payload)
            sums = hashlib.sha256(payload).hexdigest() + '  a.zip\n'
            (d / 'SHA256SUMS.txt').write_text(sums, encoding='utf-8')
            (d / 'notes.md').write_text('Reviewed notes', encoding='utf-8')
            if changes.get('corruptAsset'):
                (d / 'a.zip').write_bytes(b'wrong asset')
            if changes.get('duplicateSums'):
                (d / 'SHA256SUMS.txt').write_text(sums + sums, encoding='utf-8')
            if changes.get('unsafeSums'):
                (d / 'SHA256SUMS.txt').write_text(hashlib.sha256(payload).hexdigest() + '  ../a.zip\n')
            (d / 'fixture.json').write_text(json.dumps(fixture), encoding='utf-8')
            source = SCRIPT.read_text(encoding='utf-8')
            # Boundary overrides are injected only in a temporary test copy.
            marker = '$transcriptStarted = $false'
            self.assertEqual(source.count(marker), 1)
            (d / 'test.ps1').write_text(source.replace(marker, MOCK + '\n' + marker), encoding='utf-8')
            args = [pwsh, '-NoProfile', '-File', str(d / 'test.ps1'), '-Repo', 'o/r',
                    '-PullRequest', '19', '-Version', '1.3.0', '-TestedHeadSha', HEAD,
                    '-ExpectedBaseSha', BASE, '-RequiredChecks', 'test',
                    '-ExpectedSums', str(d / 'SHA256SUMS.txt'), '-ExpectedNotes', str(d / 'notes.md'),
                    '-ReleaseTitle', 'Skill v1.3.0', '-ImmutableReleases', 'ON', '-ExpectedVisibility', 'private',
                    '-Yes', '-ApprovalReference', 'offline owner scope fixture']
            if changes.get('dryRun'):
                args += ['-DryRun']
            if changes.get('noApproval'):
                args = args[:-2]
            if changes.get('filingConflict'):
                target = d / 'filed'
                target.mkdir()
                (target / 'a.zip').write_bytes(b'existing owner bytes')
                args += ['-CopyTo', str(target)]
            result = subprocess.run(args, capture_output=True, text=True, encoding='utf-8', timeout=30)
            calls = json.loads((d / 'mutations.json').read_text()) if (d / 'mutations.json').exists() else []
            return result, calls

    def test_full_planned_path_offline(self):
        r, calls = self.run_case()
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(calls, ['merge', 'tag', 'publish'])

    def test_resume_never_repeats_completed_mutations(self):
        r, calls = self.run_case(merged=True, tagged=True, published=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(calls, [])

    def test_unreviewed_head_on_resume_stops(self):
        r, calls = self.run_case(merged=True, head='e' * 40)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(calls, [])

    def test_changed_base_or_predicted_tree_blocks_merge(self):
        for changes in [dict(base='e' * 40), dict(wrongTree=True)]:
            r, calls = self.run_case(**changes)
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertEqual(calls, [])

    def test_missing_skipped_neutral_failed_pending_checks_stop(self):
        for checks in [[], *[[dict(id=1, name='test', status='completed', conclusion=c)]
                            for c in ['skipped', 'neutral', 'failure']],
                       [dict(id=1, name='test', status='in_progress', conclusion=None)]]:
            r, calls = self.run_case(checks=checks)
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertEqual(calls, [])

    def test_draft_notes_or_workflow_failure_blocks_publication(self):
        for changes in [dict(notes='Unreviewed changes'), dict(workflow='failure')]:
            r, calls = self.run_case(merged=True, tagged=True, **changes)
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertEqual(calls, [])

    def test_permission_error_never_becomes_missing_tag(self):
        r, calls = self.run_case(merged=True, tagReadError=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(calls, [])

    def test_unsafe_manifest_fails_before_mutation(self):
        r, calls = self.run_case(unsafeSums=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(calls, [])

    def test_dry_run_performs_no_remote_mutations(self):
        r, calls = self.run_case(dryRun=True)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(calls, [])

    def test_expected_immutable_state_is_enforced(self):
        r, calls = self.run_case(merged=True, tagged=True, published=True, immutable=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(calls, [])

    def test_changed_immutable_setting_blocks_all_actions(self):
        r, calls = self.run_case(repoImmutable=False)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(calls, [])

    def test_merge_commit_ci_failure_blocks_tag(self):
        r, calls = self.run_case(merged=True, checks=[dict(id=1, name='test', status='completed', conclusion='failure')])
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(calls, [])

    def test_duplicate_manifest_and_filing_conflict_block_all_actions(self):
        for changes in [dict(duplicateSums=True), dict(filingConflict=True)]:
            r, calls = self.run_case(**changes)
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertEqual(calls, [])

    def test_wrong_asset_blocks_publication(self):
        r, calls = self.run_case(merged=True, tagged=True, corruptAsset=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(calls, [])

    def test_unattended_run_requires_approval_record(self):
        r, calls = self.run_case(noApproval=True)
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(calls, [])

    def test_later_skipped_retry_cannot_reuse_earlier_green(self):
        r, calls = self.run_case(checks=[dict(id=1, name='test', status='completed', conclusion='success'),
                                      dict(id=2, name='test', status='completed', conclusion='skipped')])
        self.assertNotEqual(r.returncode, 0)
        self.assertEqual(calls, [])

    def test_optional_conditional_skip_does_not_block_required_success(self):
        for conclusion in ['skipped', 'neutral']:
            checks = [dict(id=1, name='test', status='completed', conclusion='success'),
                      dict(id=2, name='draft', status='completed', conclusion=conclusion)]
            r, calls = self.run_case(checks=checks)
            self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
            self.assertEqual(calls, ['merge', 'tag', 'publish'])

    def test_optional_real_failure_still_blocks_mutations(self):
        for conclusion in ['failure', 'cancelled', 'timed_out']:
            checks = [dict(id=1, name='test', status='completed', conclusion='success'),
                      dict(id=2, name='extra-validation', status='completed', conclusion=conclusion)]
            r, calls = self.run_case(checks=checks)
            self.assertNotEqual(r.returncode, 0, r.stdout)
            self.assertEqual(calls, [])
