"""Opt-in live CLI regression run; never part of offline CI and never publishes."""
import argparse
import datetime
import hashlib
import json
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

from check import evaluate, loader_evidence, make_prompt, parse_response, response_schema, HERE


def stamp():
    return datetime.datetime.now().astimezone().isoformat()


def save(path, data):
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--host", choices=["codex", "claude"], required=True)
    ap.add_argument("--output", required=True, help="new evidence directory")
    ap.add_argument("--expected-skill", required=True,
                    help="installed SKILL.md; never passed to model")
    ap.add_argument("--handoff-template", help="candidate handoff guidance to test without installing; source evidence, not installed behavior")
    ap.add_argument("--timeout", type=int, default=300)
    args = ap.parse_args()
    out = Path(args.output).resolve()
    out.mkdir(parents=True, exist_ok=False)
    skill = Path(args.expected_skill).resolve()
    metadata = {"host": args.host, "started_at": stamp(),
                "expected_skill": str(skill), "kind": "read-only decision simulation",
                "limits": "PASS checks declared decision fields, not remote execution "
                          "or arbitrary reasoning; inspect reasons as well"}
    result = {"status": "INCOMPLETE", "exit_code": 2, "errors": [], "cases": []}
    try:
        files = [skill, skill.parent / "references/approval-scope.md",
                 skill.parent / "references/publish.md"]
        snapshot = {str(p): p.read_bytes() for p in files}
        source = snapshot[str(skill)]
        fixture_bytes = (HERE / "scenarios.json").read_bytes()
        match = re.search(r'^\s*version:\s*["\']?([0-9]+\.[0-9]+\.[0-9]+)',
                          source.decode("utf-8"), re.M)
        if not match:
            raise ValueError("installed skill version not found")
        metadata.update(expected_version=match.group(1),
                        skill_sha256=hashlib.sha256(source).hexdigest(),
                        guidance_sha256={p: hashlib.sha256(b).hexdigest()
                                         for p, b in snapshot.items()},
                        fixture_sha256=hashlib.sha256(
                            fixture_bytes).hexdigest(),
                        harness_sha256={p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                                        for p in [HERE / "run.py", HERE / "check.py"]})
        prompt = make_prompt()
        if args.handoff_template:
            handoff = Path(args.handoff_template).resolve()
            snapshot[str(handoff)] = handoff.read_bytes()
            metadata["candidate_handoff"] = str(handoff)
            metadata["candidate_handoff_sha256"] = hashlib.sha256(snapshot[str(handoff)]).hexdigest()
            metadata["kind"] = "installed identity plus candidate handoff decision simulation"
            prompt += ("\n\nAdditional reviewed candidate handoff guidance (not installed/released; "
                       "apply its scope rules to these hypothetical handoffs):\n" +
                       snapshot[str(handoff)].decode("utf-8"))
        (out / "prompt.txt").write_text(prompt, encoding="utf-8")
        save(out / "response-schema.json", response_schema())
        executable = shutil.which(args.host)
        if not executable:
            raise ValueError("host executable unavailable")
        metadata["executable"] = executable
        cli = subprocess.run([executable, "--version"], capture_output=True,
                             encoding="utf-8", timeout=15)
        metadata["cli_version"] = cli.stdout.strip()
        metadata["cli_version_exit"] = cli.returncode
        with tempfile.TemporaryDirectory(prefix="approval-regression-") as work:
            metadata["temporary_cwd"] = work
            if args.host == "codex":
                command = [executable, "exec", "--sandbox", "read-only",
                           "--skip-git-repo-check", "--ephemeral", "-C", work,
                           "--json", "--output-schema", str(out / "response-schema.json"),
                           "--output-last-message", str(out / "response.json"), "-"]
                stdin = prompt.encode("utf-8")
            else:
                command = [executable, "--print", "--verbose", "--output-format",
                           "stream-json", "--no-session-persistence", "--tools",
                           "Skill,Read", "--allowedTools", "Skill,Read",
                           "--permission-mode", "dontAsk",
                           "--json-schema", json.dumps(response_schema()), prompt]
                stdin = None
            # No model override, plugin-dir injection, config rewrite, remote writes
            # or expected-answer material. Host controls and denials still apply.
            with (out / "events.jsonl").open("wb") as stdout, \
                    (out / "stderr.txt").open("wb") as stderr:
                proc = subprocess.run(command, input=stdin, cwd=work, stdout=stdout,
                                      stderr=stderr, timeout=args.timeout)
        metadata["host_exit"] = proc.returncode
        if proc.returncode:
            raise ValueError("host failed; inspect private stderr/events evidence")
        events = []
        for line in (out / "events.jsonl").read_text(encoding="utf-8").splitlines():
            if line.strip():
                events.append(json.loads(line))
        if args.host == "claude":
            terminal = [e for e in events if e.get("type") == "result"]
            if len(terminal) != 1 or terminal[0].get("is_error"):
                raise ValueError("missing or failed Claude result")
            data = terminal[0].get("structured_output")
            if not isinstance(data, dict):
                data = parse_response(terminal[0].get("result", ""))
            save(out / "response.json", data)
        else:
            data = parse_response((out / "response.json").read_text(encoding="utf-8"))
        result = evaluate(data, metadata["expected_version"], skill)
        metadata["loader_evidence"] = loader_evidence(args.host, events, skill)
        if not metadata["loader_evidence"]:
            result["errors"].append("actual loader tool evidence missing")
            result.update(status="INCOMPLETE", exit_code=2)
        if any(Path(p).read_bytes() != b for p, b in snapshot.items()):
            result["errors"].append("installed source changed during run")
            result.update(status="INCOMPLETE", exit_code=2)
        if (HERE / "scenarios.json").read_bytes() != fixture_bytes:
            result["errors"].append("fixture changed during run")
            result.update(status="INCOMPLETE", exit_code=2)
        (out / "fixture-snapshot.json").write_bytes(fixture_bytes)
    except (ValueError, OSError, TypeError, subprocess.TimeoutExpired) as exc:
        result = {"status": "INCOMPLETE", "exit_code": 2,
                  "errors": [str(exc)], "cases": []}
    metadata["ended_at"] = stamp()
    save(out / "run.json", metadata)
    save(out / "report.json", result)
    print(args.host + ": " + result["status"])
    for case in result["cases"]:
        print(case["id"] + " " + case["status"] +
              (" " + ",".join(case["mismatches"]) if case["mismatches"] else ""))
    for error in result["errors"]:
        print("ERROR: " + error)
    return result["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
