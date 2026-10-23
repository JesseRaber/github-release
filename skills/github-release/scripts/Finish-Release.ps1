<#
.SYNOPSIS
  Owner-run finish for a draft-first GitHub release: merge -> tag -> wait for draft ->
  verify every asset against the gated build -> publish -> verify published -> file assets
  One confirmation; stops at the first failed check.

.DESCRIPTION
  GitHub Release v1.2.0 (https://github.com/JesseRaber/github-release), Jesse Raber.
  For steps an agent session cannot perform (merge, tag push, publish). The agent fills in
  every parameter from its gate; the owner runs it once. Each step detects work already done,
  so a re-run after a stop resumes safely. Nothing is retried blindly, deleted, force-pushed
  or overwritten. Requires PowerShell 7+, git and an authenticated GitHub CLI (gh auth login).

.EXAMPLE
  & ./Finish-Release.ps1 -Repo owner/repo -PullRequest 13 -Version 1.2.5 `
    -TestedHeadSha <sha> -ExpectedBaseSha <base-sha> -RequiredChecks @('test', 'validate') `
    -ExpectedSums C:\path\SHA256SUMS.txt -ExpectedNotes C:\path\notes.md `
    -ExpectedVisibility private -ImmutableReleases ON -ReleaseTitle "My Skill v1.2.5" `
    -CopyTo "C:\...\Release Packages\v1.2.5" -LogPath "C:\...\FINISH_RELEASE_v1.2.5.log"
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory)][ValidatePattern('^[\w.-]+/[\w.-]+$')][string]$Repo,
    [Parameter(Mandatory)][int]$PullRequest,
    [Parameter(Mandatory)][ValidatePattern('^\d+\.\d+\.\d+$')][string]$Version,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$TestedHeadSha,
    [Parameter(Mandatory)][string]$ExpectedSums,
    [Parameter(Mandatory)][ValidatePattern('^[0-9a-f]{40}$')][string]$ExpectedBaseSha,
    [Parameter(Mandatory)][string]$ExpectedNotes,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string[]]$RequiredChecks,
    [Parameter(Mandatory)][ValidateSet('ON', 'OFF')][string]$ImmutableReleases,
    [Parameter(Mandatory)][ValidateSet('private', 'public')][string]$ExpectedVisibility,
    [Parameter(Mandatory)][ValidateNotNullOrEmpty()][string]$ReleaseTitle,
    [ValidateSet('squash', 'merge')][string]$MergeMethod = 'squash',
    [string]$CopyTo,
    [string]$LogPath,
    [ValidateRange(1, 120)][int]$TimeoutMinutes = 20,
    [switch]$DryRun,
    [switch]$Yes,
    [string]$ApprovalReference
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$ScriptVersion = '1.2.0'
$Tag = "v$Version"
$receipt = [ordered]@{ script = "Finish-Release.ps1 $ScriptVersion"; repo = $Repo; version = $Version; dryRun = [bool]$DryRun; steps = [ordered]@{}; result = 'STARTED' }
if ($PSVersionTable.PSVersion.Major -lt 7) { throw 'PowerShell 7 or later is required (run with pwsh).' }

function Step([string]$name, [string]$state, [string]$detail = '') {
    $receipt.steps[$name] = [ordered]@{ state = $state; detail = $detail; at = (Get-Date).ToString('o') }
    $color = switch ($state) { 'PASS' { 'Green' } 'DONE' { 'Green' } 'SKIP' { 'Yellow' } 'PLAN' { 'Cyan' } default { 'Red' } }
    Write-Host ("[{0}] {1}{2}" -f $state, $name, $(if ($detail) { " - $detail" } else { '' })) -ForegroundColor $color
}
function Fail([string]$name, [string]$detail) { Step $name 'FAIL' $detail; throw "STOPPED at '$name': $detail" }
$GhExe = 'gh'  # resolved by preflight inside the guarded error/receipt path
function Invoke-GhJson([string[]]$ghArgs, [switch]$AllowNotFound) {
    $out = & $GhExe @ghArgs 2>&1
    if ($LASTEXITCODE -ne 0 -and $AllowNotFound -and ($out | Out-String) -match '\(HTTP 404\)') { return $null }
    if ($LASTEXITCODE -ne 0) { throw "gh $($ghArgs -join ' ') failed: $out" }
    $text = ($out | Out-String).Trim()
    if ($text) { return $text | ConvertFrom-Json -Depth 50 } else { return $null }
}
function Api([string]$path) { Invoke-GhJson @('api', "repos/$Repo/$path") }
function ApiOptional([string]$path) { Invoke-GhJson -ghArgs @('api', "repos/$Repo/$path") -AllowNotFound }
function ApiList([string]$path) { Invoke-GhJson @('api', '--paginate', '--slurp', "repos/$Repo/$path") | ForEach-Object { $_ } | ForEach-Object { $_ } }
function Check-State([string]$sha) {
    $runs = @(ApiList "commits/$sha/check-runs?per_page=100" | ForEach-Object { $_.check_runs })
    # Select the latest result per check name; never accept an earlier green retry.
    $latest = @($runs | Group-Object name | ForEach-Object { $_.Group | Sort-Object id -Descending | Select-Object -First 1 })
    $missing = @($RequiredChecks | Where-Object { $_ -notin @($latest | ForEach-Object { $_.name }) })
    $failed = @($latest | Where-Object { $_.status -eq 'completed' -and $_.conclusion -ne 'success' })
    if ($failed) { Fail 'CI' ("non-passing checks: " + (($failed | ForEach-Object { "$($_.name)=$($_.conclusion)" }) -join ', ')) }
    return ($latest.Count -gt 0 -and -not $missing -and -not @($latest | Where-Object { $_.status -ne 'completed' }))
}
function Check-Pr($pr) {
    if ($pr.head.sha -ne $TestedHeadSha) { Fail 'PR' 'head differs from tested head, including on resume' }
    if ($pr.base.repo.full_name -ine $Repo -or $pr.base.ref -ne $repoInfo.default_branch) { Fail 'PR' 'wrong repository or base branch' }
    if (-not $pr.merged -and $pr.base.sha -ne $ExpectedBaseSha) { Fail 'PR' 'base changed; re-review and rerun affected gate checks' }
}
function Check-Release($release) {
    if ($release.tag_name -ne $Tag -or $release.author.login -ne 'github-actions[bot]' -or $release.name -ne $ReleaseTitle -or $release.prerelease) { Fail 'release' 'tag, workflow author, title or stable channel mismatch' }
    if (($release.body -replace "`r`n", "`n").TrimEnd() -cne $notesText.TrimEnd()) { Fail 'release' 'release notes differ from reviewed notes' }
}
function Get-TagWorkflow {
    $runs = @((Api "actions/workflows/release.yml/runs?event=push&head_sha=$mergeSha&per_page=100").workflow_runs | Where-Object { $_.head_sha -eq $mergeSha -and $_.head_branch -eq $Tag -and $_.path -eq '.github/workflows/release.yml' })
    return $runs | Sort-Object id -Descending | Select-Object -First 1
}
function Check-Policy {
    $info = Invoke-GhJson @('api', "repos/$Repo")
    $actualVisibility = if ($info.private) { 'private' } else { 'public' }
    if ($actualVisibility -ne $ExpectedVisibility) { Fail 'scope' 'repository audience differs from approved gate' }
    $policy = Api 'immutable-releases'
    if ([bool]$policy.enabled -ne ($ImmutableReleases -eq 'ON')) { Fail 'scope' 'immutable-release setting changed from approved gate' }
}
function Check-Tag {
    $ref = ApiOptional "git/ref/tags/$Tag"
    if (-not $ref) { Fail 'tag' 'expected tag disappeared; reconcile remote state' }
    $sha = $ref.object.sha
    if ($ref.object.type -eq 'tag') { $sha = (Api "git/tags/$sha").object.sha }
    if ($sha -ne $mergeSha) { Fail 'tag' 'existing tag differs from reviewed merge commit' }
    return $sha
}
function Sha256([string]$file) { (Get-FileHash -Algorithm SHA256 -LiteralPath $file).Hash.ToLowerInvariant() }
function Get-Asset($asset, [string]$dir) {
    # Byte-safe download: copy gh's raw stdout stream to the file. PowerShell text pipelines and
    # Start-Process redirection re-encode output and corrupt binary assets.
    $dest = Join-Path $dir $asset.name
    $psi = [Diagnostics.ProcessStartInfo]::new($GhExe)
    foreach ($a in @('api', '-H', 'Accept: application/octet-stream', "repos/$Repo/releases/assets/$($asset.id)")) { $psi.ArgumentList.Add($a) }
    $psi.RedirectStandardOutput = $true; $psi.RedirectStandardError = $true; $psi.UseShellExecute = $false
    $proc = [Diagnostics.Process]::Start($psi)
    $errTask = $proc.StandardError.ReadToEndAsync()
    $fs = [IO.File]::Create($dest)
    try { $proc.StandardOutput.BaseStream.CopyTo($fs) } finally { $fs.Dispose() }
    $proc.WaitForExit()
    if ($proc.ExitCode -ne 0) { throw "Download of $($asset.name) failed: $($errTask.Result)" }
    return $dest
}
function Get-ReleaseByTag {
    $all = @(ApiList 'releases?per_page=100')
    return $all | Where-Object { $_.tag_name -eq $Tag } | Select-Object -First 1
}
function Test-Assets($release, [string]$dir, [hashtable]$expected, [string]$label) {
    $names = @($release.assets | ForEach-Object { $_.name })
    $want = @($expected.Keys) + 'SHA256SUMS.txt'
    if (@($names | Select-Object -Unique).Count -ne $names.Count) { Fail "$label assets" 'duplicate asset names' }
    $extra = @($names | Where-Object { $_ -notin $want }); $missing = @($want | Where-Object { $_ -notin $names })
    if ($extra -or $missing) { Fail "$label assets" "asset set differs (missing: $($missing -join ', '); unexpected: $($extra -join ', '))" }
    foreach ($a in $release.assets) {
        $file = Get-Asset $a $dir
        $h = Sha256 $file
        if ($a.PSObject.Properties['digest'] -and $a.digest -and $a.digest -ne "sha256:$h") { Fail "$label assets" "$($a.name): GitHub digest $($a.digest) differs from downloaded bytes" }
        if ($a.name -eq 'SHA256SUMS.txt') {
            $got = (Get-Content -Raw -LiteralPath $file) -replace "`r`n", "`n"
            if ($got.Trim() -ne $script:ExpectedText.Trim()) { Fail "$label assets" 'SHA256SUMS.txt differs from the gated build' }
        } elseif ($h -ne $expected[$a.name]) { Fail "$label assets" "$($a.name): $h, expected $($expected[$a.name])" }
    }
    Step "$label assets" 'PASS' "$($names.Count) assets byte-match the gated build"
}

$transcriptStarted = $false
$work = Join-Path ([IO.Path]::GetTempPath()) ("finish-release-" + [guid]::NewGuid().ToString('N'))
$exitCode = 1
try {
    if ($LogPath) {
        if ([IO.Path]::GetExtension($LogPath) -eq '.json') { throw 'LogPath must not use .json (reserved for the separate receipt)' }
        $LogPath = [IO.Path]::GetFullPath($LogPath)
        New-Item -ItemType Directory -Force -Path (Split-Path -Parent $LogPath) | Out-Null
        Start-Transcript -LiteralPath $LogPath -Append | Out-Null; $transcriptStarted = $true
    }
    # ---- Preflight -------------------------------------------------------------------------
    foreach ($cmd in 'gh', 'git') { if (-not (Get-Command $cmd -CommandType Application -ErrorAction SilentlyContinue)) { Fail 'preflight' "$cmd is not installed or not on PATH" } }
    $GhExe = (Get-Command gh -CommandType Application | Select-Object -First 1).Source
    try { $null = Invoke-GhJson @('api', 'user') } catch { Fail 'preflight' 'gh cannot reach GitHub as a signed-in user; run: gh auth login' }
    if (-not (Test-Path -LiteralPath $ExpectedSums -PathType Leaf)) { Fail 'preflight' 'expected checksum file missing' }
    if (-not (Test-Path -LiteralPath $ExpectedNotes -PathType Leaf)) { Fail 'preflight' 'reviewed notes file missing' }
    $notesText = (Get-Content -Raw -LiteralPath $ExpectedNotes) -replace "`r`n", "`n"
    if (-not $notesText.Trim()) { Fail 'preflight' 'reviewed notes are empty' }
    if ($Yes -and -not $ApprovalReference) { Fail 'approval' '-Yes requires a recorded approval reference covering this workflow' }
    $receipt.approvalReference = $ApprovalReference
    $receipt.immutableExpected = $ImmutableReleases
    $script:ExpectedText = Get-Content -Raw -LiteralPath $ExpectedSums
    $script:ExpectedText = $script:ExpectedText -replace "`r`n", "`n"
    $expected = @{}
    foreach ($line in ($script:ExpectedText -split "`n" | Where-Object { $_.Trim() })) {
        if ($line -notmatch '^([0-9a-fA-F]{64})\s+\*?([^\s/\\:]+\.zip)$') { Fail 'preflight' "unreadable SHA256SUMS line: $line" }
        if ($expected.ContainsKey($Matches[2])) { Fail 'preflight' 'duplicate checksum filename' }
        $expected[$Matches[2]] = $Matches[1].ToLowerInvariant()
    }
    if ($expected.Count -lt 1) { Fail 'preflight' 'no expected hashes supplied' }
    $repoInfo = Invoke-GhJson @('api', "repos/$Repo")
    if ($CopyTo -and (Test-Path -LiteralPath $CopyTo)) {
        if (-not (Test-Path -LiteralPath $CopyTo -PathType Container)) { Fail 'preflight' 'filing destination is not a directory' }
        foreach ($name in @($expected.Keys) + 'SHA256SUMS.txt') {
            $dest = Join-Path $CopyTo $name
            if (Test-Path -LiteralPath $dest) {
                $hash = if ($name -eq 'SHA256SUMS.txt') { Sha256 $ExpectedSums } else { $expected[$name] }
                if ((Sha256 $dest) -ne $hash) { Fail 'preflight' 'filing conflict; no remote action taken' }
            }
        }
    }
    $pr = Api "pulls/$PullRequest"
    Check-Pr $pr
    Check-Policy
    $protection = Api ("branches/{0}/protection" -f $repoInfo.default_branch)
    if (-not $protection.required_status_checks -or -not @($protection.required_status_checks.contexts).Count) { Fail 'preflight' 'required branch checks unavailable or unconfigured' }
    foreach ($name in $protection.required_status_checks.contexts) { if ($name -notin $RequiredChecks) { Fail 'preflight' "required check omitted from gate: $name" } }
    $me = Invoke-GhJson @('api', 'user')
    Step 'preflight' 'PASS' ("{0} ({1}), PR #{2} '{3}', signed in as {4}, {5} expected assets" -f $Repo, $(if ($repoInfo.private) { 'private' } else { 'PUBLIC' }), $PullRequest, $pr.title, $me.login, $expected.Count)

    Write-Host ''
    Write-Host "This run will, stopping at the first failed check:" -ForegroundColor Cyan
    Write-Host "  1. merge PR #$PullRequest ($MergeMethod) if its head is $($TestedHeadSha.Substring(0,12)) and every check passed"
    Write-Host "  2. confirm the merged tree equals the tested tree and CI on the merge commit is green"
    Write-Host "  3. create annotated tag $Tag on the merge commit (as $($me.login))"
    Write-Host "  4. wait for the release workflow's DRAFT and verify every asset byte-for-byte"
    Write-Host "  5. publish the draft, then re-download and re-verify the published assets"
    if ($CopyTo) { Write-Host "  6. save the published assets to $CopyTo (never overwrites different files)" }
    if ($DryRun) { Write-Host '  DRY RUN: read-only checks only; nothing will change.' -ForegroundColor Yellow }
    elseif (-not $Yes) {
        $answer = Read-Host "Type $Tag to approve all steps above"
        if ($answer -ne $Tag) { Fail 'approval' 'not approved; nothing changed' }
    }
    if ($DryRun) { $receipt.checkedBy = $me.login } else { $receipt.approvedBy = $me.login }
    $receipt.testedHead = $TestedHeadSha; $receipt.expectedBase = $ExpectedBaseSha
    $receipt.expectedVisibility = $ExpectedVisibility; $receipt.requiredChecks = $RequiredChecks
    $receipt.checksumSha256 = Sha256 $ExpectedSums; $receipt.notesSha256 = Sha256 $ExpectedNotes

    # ---- 1. Merge --------------------------------------------------------------------------
    if ($pr.merged) {
        $mergeSha = $pr.merge_commit_sha
        Step 'merge' 'DONE' "already merged as $mergeSha"
    } else {
        if ($pr.state -ne 'open') { Fail 'merge' "PR is $($pr.state) and not merged" }
        if ($pr.head.sha -ne $TestedHeadSha) { Fail 'merge' "PR head is $($pr.head.sha), not the tested $TestedHeadSha" }
        if (-not (Check-State $TestedHeadSha)) { Fail 'merge' 'required checks missing or pending on tested head' }
        $predicted = Api "git/commits/$($pr.merge_commit_sha)"
        if ($predicted.tree.sha -ne (Api "git/commits/$TestedHeadSha").tree.sha) { Fail 'merge' 'base changes alter tested tree; re-review candidate' }
        if ($DryRun) { Step 'merge' 'PLAN' "would merge PR #$PullRequest (required checks green)"; $mergeSha = $null }
        else {
            Check-Pr (Api "pulls/$PullRequest")
            $m = Invoke-GhJson @('api', '-X', 'PUT', "repos/$Repo/pulls/$PullRequest/merge", '-f', "merge_method=$MergeMethod", '-f', "sha=$TestedHeadSha")
            if (-not $m.merged) { Fail 'merge' "GitHub did not merge: $($m.message)" }
            $mergeSha = $m.sha
            Step 'merge' 'DONE' "merged as $mergeSha"
        }
    }
    $receipt.mergeSha = $mergeSha

    # ---- 2. Tree + CI on the merge commit -------------------------------------------------
    if ($mergeSha) {
        $t1 = (Api "git/commits/$mergeSha").tree.sha; $t2 = (Api "git/commits/$TestedHeadSha").tree.sha
        if ($t1 -ne $t2) { Fail 'tree' "merge tree $t1 differs from tested tree $t2" }
        Step 'tree' 'PASS' "merge tree equals tested tree ($t1)"
        $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
        while ($true) {
            if (Check-State $mergeSha) { break }
            if ((Get-Date) -gt $deadline) { Fail 'merge CI' 'timed out waiting for CI on the merge commit' }
            if ($DryRun) { Fail 'merge CI' 'required checks missing/pending; dry run cannot certify readiness' }
            Start-Sleep -Seconds 20
        }
        Step 'merge CI' 'PASS' 'all required checks succeeded'
    } else { Step 'tree' 'PLAN' 'checked after merge' }

    # ---- 3. Tag ----------------------------------------------------------------------------
    $tagSha = $null
    $ref = ApiOptional "git/ref/tags/$Tag"
    if ($ref) {
        $tagSha = $ref.object.sha
        if ($ref.object.type -eq 'tag') { $tagSha = (Api "git/tags/$($ref.object.sha)").object.sha }
        if (-not $mergeSha -or $tagSha -ne $mergeSha) { Fail 'tag' "$Tag already exists on $tagSha, not the merge commit $mergeSha" }
        Step 'tag' 'DONE' "$Tag already on $tagSha"
    } elseif ($DryRun -or -not $mergeSha) { Step 'tag' 'PLAN' "would tag $Tag on the merge commit" }
    else {
        if ((Api "git/ref/heads/$($repoInfo.default_branch)").object.sha -ne $mergeSha) { Fail 'tag' 'main advanced since reviewed merge; re-review before tagging' }
        New-Item -ItemType Directory -Force -Path $work | Out-Null
        $clone = Join-Path $work 'repo'
        & git -c core.autocrlf=false clone --quiet --filter=blob:none --no-checkout "https://github.com/$Repo.git" $clone
        if ($LASTEXITCODE -ne 0) { Fail 'tag' 'temporary clone failed' }
        $email = "$($me.id)+$($me.login)@users.noreply.github.com"; $name = if ($me.name) { $me.name } else { $me.login }
        $msg = if ($ReleaseTitle) { $ReleaseTitle } else { "$($Repo.Split('/')[1]) $Tag" }
        & git -C $clone -c "user.name=$name" -c "user.email=$email" tag -a $Tag $mergeSha -m $msg
        if ($LASTEXITCODE -ne 0) { Fail 'tag' 'git tag failed' }
        & git -C $clone push --quiet origin "refs/tags/$Tag"
        if ($LASTEXITCODE -ne 0) { Fail 'tag' 'tag push failed (check GitHub sign-in for git)' }
        $tagSha = Check-Tag
        if (-not $tagSha) { Fail 'tag' 'pushed tag not visible on expected commit' }
        Step 'tag' 'DONE' "$Tag pushed on $mergeSha"
    }
    $receipt.tag = $Tag

    # ---- 4. Wait for the draft and verify --------------------------------------------------
    $rel = $null
    if ($tagSha) {
        $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
        while ($true) {
            $rel = Get-ReleaseByTag
            if ($rel -and @($rel.assets).Count -ge ($expected.Count + 1)) { break }
            $wf = Get-TagWorkflow
            if ($wf -and $wf.status -eq 'completed' -and $wf.conclusion -ne 'success') { Fail 'draft' 'exact-tag release workflow failed; reconcile before continuing' }
            if ((Get-Date) -gt $deadline) { Fail 'draft' 'timed out waiting for the release workflow' }
            if ($DryRun) { break }
            Start-Sleep -Seconds 20
        }
    }
    if (-not $rel) { Step 'draft' 'PLAN' 'verified after the tag is pushed' }
    else {
        $null = Check-Tag
        Check-Release $rel
        $deadline = (Get-Date).AddMinutes($TimeoutMinutes)
        while ($true) {
            $workflowRun = Get-TagWorkflow
            if ($workflowRun -and $workflowRun.status -eq 'completed') {
                if ($workflowRun.conclusion -ne 'success') { Fail 'draft' 'exact-tag release workflow failed' }
                break
            }
            if ($DryRun) { Fail 'draft' 'exact-tag workflow is missing/pending; dry run cannot certify readiness' }
            if ((Get-Date) -gt $deadline) { Fail 'draft' 'timed out waiting for exact-tag workflow success' }
            Start-Sleep -Seconds 20
        }
        $receipt.releaseWorkflowRun = $workflowRun.id
        $dl = Join-Path $work 'draft'; New-Item -ItemType Directory -Force -Path $dl | Out-Null
        Test-Assets $rel $dl $expected $(if ($rel.draft) { 'draft' } else { 'release' })
        $receipt.releaseId = $rel.id

        # ---- 5. Publish ---------------------------------------------------------------------
        if (-not $rel.draft) { Step 'publish' 'DONE' "already published $($rel.published_at)" }
        elseif ($DryRun) { Step 'publish' 'PLAN' "would publish release $($rel.id)" }
        else {
            $null = Check-Tag
            Check-Policy
            $fresh = Api "releases/$($rel.id)"
            Check-Release $fresh
            if (-not $fresh.draft) { Fail 'publish' 'draft changed during verification; reconcile before retry' }
            $freshDir = Join-Path $work 'before-publish'; New-Item -ItemType Directory -Force -Path $freshDir | Out-Null
            Test-Assets $fresh $freshDir $expected 'before-publish'
            $null = Invoke-GhJson @('api', '-X', 'PATCH', "repos/$Repo/releases/$($rel.id)", '-F', 'draft=false', '-f', 'make_latest=true')
            Step 'publish' 'DONE' 'draft published'
        }
        if (-not $DryRun -or -not $rel.draft) {
            $pub = Api "releases/tags/$Tag"
            Check-Release $pub
            if ($ImmutableReleases -eq 'ON' -and (-not $pub.PSObject.Properties['immutable'] -or -not $pub.immutable)) { Fail 'published' 'expected immutable release not confirmed' }
            if ($pub.draft) { Fail 'published' 'release is still a draft' }
            $pd = Join-Path $work 'published'; New-Item -ItemType Directory -Force -Path $pd | Out-Null
            Test-Assets $pub $pd $expected 'published'
            $receipt.publishedAt = $pub.published_at; $receipt.releaseUrl = $pub.html_url
            $receipt.immutable = if ($pub.PSObject.Properties['immutable']) { $pub.immutable } else { 'not reported' }

            # ---- 6. File the published assets ----------------------------------------------
            if ($CopyTo) {
                if ($DryRun) { Step 'file assets' 'PLAN' "would save to $CopyTo" }
                else {
                    New-Item -ItemType Directory -Force -Path $CopyTo | Out-Null
                    foreach ($f in Get-ChildItem -LiteralPath $pd -File) {
                        $dest = Join-Path $CopyTo $f.Name
                        if (Test-Path -LiteralPath $dest) {
                            if ((Sha256 $dest) -ne (Sha256 $f.FullName)) { Fail 'file assets' "$dest exists with different content; not overwritten" }
                        } else { Copy-Item -LiteralPath $f.FullName -Destination $dest }
                    }
                    foreach ($f in Get-ChildItem -LiteralPath $pd -File) { if ((Sha256 (Join-Path $CopyTo $f.Name)) -ne (Sha256 $f.FullName)) { Fail 'file assets' "$($f.Name) did not copy intact" } }
                    Step 'file assets' 'DONE' "$CopyTo"
                }
            }


        }
    }
    $receipt.result = if ($DryRun) { 'DRY RUN: verified only existing state; planned steps are not certified' } else { 'PASS' }
    $exitCode = 0
}
catch {
    $receipt.result = 'STOPPED'
    $receipt.error = $_.Exception.Message
    Write-Host $_.Exception.Message -ForegroundColor Red
}
finally {
    # Keep evidence for reconciliation after an uncertain remote outcome; no automatic deletion.
    if (Test-Path -LiteralPath $work) { $receipt.evidenceDirectory = $work }
    $json = $receipt | ConvertTo-Json -Depth 6
    if ($LogPath -and $transcriptStarted) {
        $rp = [IO.Path]::ChangeExtension($LogPath, '.json')
        [IO.File]::WriteAllText($rp, $json + "`n", [Text.UTF8Encoding]::new($false))
        Write-Host "Receipt: $rp"
        if ($transcriptStarted) { Stop-Transcript | Out-Null }
    } else { Write-Host $json }
    Write-Host ("RESULT: " + $receipt.result) -ForegroundColor $(if ($exitCode -eq 0) { 'Green' } else { 'Red' })
}
exit $exitCode
