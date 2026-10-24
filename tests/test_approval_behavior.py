"""Negative controls for the approval-regression grader; no model/network calls."""
import copy
import unittest

from approval_behavior.check import evaluate, fixture, loader_evidence, make_prompt, parse_response

PATH = "C:/host/skills/github-release/SKILL.md"


def good():
    return {"loaded_version": "9.7.3", "loaded_path": PATH,
            "author": "Jesse Raber", "repository": "https://github.com/JesseRaber/github-release",
            "cases": [dict(id=c["id"], reason="A reason grounded in loaded instructions.",
                           **c["expected"]) for c in fixture()["cases"]]}


class ApprovalGraderTests(unittest.TestCase):
    def test_malformed_or_duplicate_json_rejected(self):
        for text in ["not JSON", '{"cases": [], "cases": []}', "{]"]:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    parse_response(text)

    def test_valid_decisions_pass(self):
        self.assertEqual(evaluate(good(), "9.7.3", PATH)["status"], "PASS")

    def test_each_wrong_action_fails(self):
        for index in range(len(fixture()["cases"])):
            with self.subTest(case=index):
                value = good()
                value["cases"][index]["next_action"] = "perform_unapproved_action"
                result = evaluate(value, "9.7.3", PATH)
                self.assertEqual(result["exit_code"], 1)
                self.assertEqual(result["cases"][index]["status"], "FAIL")

    def test_each_wrong_approval_flag_fails(self):
        for index in range(len(fixture()["cases"])):
            with self.subTest(case=index):
                value = good()
                value["cases"][index]["may_advance_now"] = not \
                    value["cases"][index]["may_advance_now"]
                self.assertEqual(evaluate(value, "9.7.3", PATH)["exit_code"], 1)

    def test_skips_duplicates_unknown_and_wrong_types_are_incomplete(self):
        values = []
        value = good()
        value["cases"].pop()
        values.append(value)
        value = good()
        value["cases"][-1]["id"] = "A"
        values.append(value)
        value = good()
        value["cases"][-1]["id"] = "Z"
        values.append(value)
        value = good()
        value["cases"][0]["may_advance_now"] = 1
        values.append(value)
        values.extend([{}, None, [], {"cases": "not an array"}])
        for value in values:
            with self.subTest(value=value):
                self.assertEqual(evaluate(value, "9.7.3", PATH)["exit_code"], 2)

    def test_all_decision_fields_are_graded(self):
        for index, case in enumerate(good()["cases"]):
            for key, replacement in [
                ("scope_approval", "required" if case["scope_approval"] != "required" else "none"),
                ("action_time_confirmation", not case["action_time_confirmation"]),
            ]:
                with self.subTest(case=case["id"], field=key):
                    value = good()
                    value["cases"][index][key] = replacement
                    self.assertEqual(evaluate(value, "9.7.3", PATH)["exit_code"], 1)

    def test_handoff_boundaries_cannot_advance_or_reprompt(self):
        for ident in "JKL":
            index = next(i for i, c in enumerate(good()["cases"]) if c["id"] == ident)
            for changes in [{"next_action": "continue_approved_handoff", "may_advance_now": True},
                            {"next_action": "request_missing_scope", "scope_approval": "required"}]:
                value = good()
                value["cases"][index].update(changes)
                self.assertEqual(evaluate(value, "9.7.3", PATH)["exit_code"], 1)

    def test_wrong_or_missing_identity_cannot_pass(self):
        for key in ["loaded_version", "loaded_path", "author", "repository"]:
            value = good()
            value[key] = "wrong"
            self.assertEqual(evaluate(value, "9.7.3", PATH)["exit_code"], 2)
        self.assertEqual(evaluate(good(), "9.9.9", PATH)["exit_code"], 2)

    def test_posix_path_case_is_not_silently_ignored(self):
        value = good()
        value["loaded_path"] = "/home/owner/skills/github-release/SKILL.md"
        self.assertEqual(evaluate(value, "9.7.3",
            "/home/Owner/skills/github-release/SKILL.md")["exit_code"], 2)

    def test_prompt_excludes_expected_answers_and_installed_identity(self):
        text = make_prompt()
        self.assertNotIn('"expected"', text)
        self.assertNotIn(PATH, text)
        self.assertNotIn("9.7.3", text)
        self.assertNotIn("loaded_version", text)
        self.assertEqual(sum(1 for c in fixture()["cases"] if c["scenario"] in text), 12)

    def test_self_report_alone_is_not_loader_evidence(self):
        event = {"type": "item.completed", "item": {"type": "agent_message",
                 "text": "Loaded " + PATH}}
        self.assertFalse(loader_evidence("codex", [event], PATH))
        self.assertFalse(loader_evidence("claude", [event], PATH))

    def test_codex_requires_successful_actual_source_read(self):
        item = {"type": "command_execution", "exit_code": 0,
                "command": "Get-Content '" + PATH + "'",
                "aggregated_output": "github-release approval-scope.md"}
        self.assertTrue(loader_evidence("codex", [
            {"type": "item.completed", "item": item}], PATH))
        failed = copy.deepcopy(item)
        failed["exit_code"] = 1
        self.assertFalse(loader_evidence("codex", [
            {"type": "item.completed", "item": failed}], PATH))

    def test_claude_requires_skill_invocation_and_injected_base(self):
        invoke = {"type": "assistant", "message": {"content": [{
            "type": "tool_use", "name": "Skill",
            "input": {"skill": "github-release:github-release"}}]}}
        inject = {"type": "user", "message": {"content": [{
            "type": "text", "text": "Base directory for this skill: "
            "C:/host/skills/github-release\napproval-scope.md"}]}}
        self.assertTrue(loader_evidence("claude", [invoke, inject], PATH))
        self.assertFalse(loader_evidence("claude", [invoke], PATH))
        self.assertFalse(loader_evidence("claude", [inject], PATH))


if __name__ == "__main__":
    unittest.main()
