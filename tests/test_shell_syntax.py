"""Release snippet syntax and controls proving parsing does not execute code."""
from pathlib import Path
import tempfile
import unittest

from shell_syntax import examples, inventory, markdown_runs, parse, workflow_runs

ROOT = Path(__file__).resolve().parents[1]


class ShellSyntaxTests(unittest.TestCase):
    def test_repository_shell_snippets_parse(self):
        checks = inventory(ROOT)
        self.assertTrue(checks)
        self.assertEqual({c[0] for c in checks}, {'bash', 'pwsh'})
        for shell, code, source in checks:
            with self.subTest(source=source, shell=shell):
                result = parse(shell, code)
                self.assertEqual(result.returncode, 0, source + '\n' + result.stdout + result.stderr)

    def test_malformed_control_flow_is_rejected(self):
        for shell, code in [('bash', 'if true; then echo ok; fi; fi'),
                            ('bash', 'if true; then echo missing'),
                            ('pwsh', 'if ($true) { Write-Output missing')]:
            with self.subTest(shell=shell, code=code):
                self.assertNotEqual(parse(shell, code).returncode, 0)

    def test_parse_only_never_executes_snippet(self):
        with tempfile.TemporaryDirectory() as folder:
            sentinel = Path(folder) / 'MUST_NOT_EXIST'
            for shell, code in [('bash', "echo unsafe > '" + sentinel.as_posix() + "'"),
                                ('pwsh', "Set-Content -LiteralPath '" + str(sentinel) + "' -Value unsafe")]:
                self.assertEqual(parse(shell, code).returncode, 0)
                self.assertFalse(sentinel.exists())

    def test_workflow_shell_after_run_and_literal_heredoc(self):
        text = "steps:\n  - name: demo\n    run: |\n      cat <<'PY'\n      print('test')\n      PY\n  - run: Write-Output ok\n    shell: pwsh\n"
        checks = workflow_runs(text, 'control.yml')
        self.assertEqual([x[0] for x in checks], ['bash', 'pwsh'])
        self.assertIn('\nPY', checks[0][1])
        for shell, code, _ in checks:
            self.assertEqual(parse(shell, code).returncode, 0)

    def test_unsupported_forms_are_not_silent_passes(self):
        for text in ['steps:\n  - run: >\n      echo ok', 'steps:\n  - run: *alias',
                     'defaults:\n  run:\n    shell: pwsh', 'steps:\n  - run: echo ok\n    shell: python',
                     'steps:\n  - {run: fi}']:
            with self.subTest(text=text):
                with self.assertRaises(ValueError):
                    workflow_runs(text, 'control.yml')

    def test_markdown_fences_and_placeholders(self):
        checks = markdown_runs('```bash\necho <owner>/<repo>\n```\n```yaml\nsteps:\n  - run: echo ${{ inputs.version }}\n```', 'doc.md')
        self.assertEqual(len(checks), 2)
        self.assertEqual(checks[0][1], 'echo EXAMPLE/EXAMPLE')
        self.assertEqual(checks[1][1], 'echo EXPRESSION')
        self.assertIn("<<'PY'", examples("cat <<'PY'\nhello\nPY"))
        with self.assertRaises(ValueError):
            markdown_runs('```bash\necho ok', 'broken.md')

    def test_runner_defaults_and_step_first_shell(self):
        checks = workflow_runs('runs-on: windows-latest\nsteps:\n  - run: Write-Output ok\n', 'windows.yml')
        self.assertEqual(checks[0][0], 'pwsh')
        checks = workflow_runs('steps:\n  - shell: pwsh\n    run: Write-Output ok\n', 'step.yml')
        self.assertEqual(checks[0][0], 'pwsh')
        with self.assertRaises(ValueError):
            workflow_runs('runs-on: ${{ matrix.os }}\nsteps:\n  - run: echo ok\n', 'matrix.yml')

    def test_workflow_redirection_is_not_rewritten_as_doc_placeholder(self):
        checks = workflow_runs('steps:\n  - run: cat <input>\n', 'bad.yml')
        self.assertIn('<input>', checks[0][1])
        self.assertNotEqual(parse(checks[0][0], checks[0][1]).returncode, 0)
