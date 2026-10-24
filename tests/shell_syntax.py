"""Parser-only checks for the repository's literal workflow and document snippets."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

SHELLS = {'bash': 'bash', 'sh': 'bash', 'shell': 'bash',
          'pwsh': 'pwsh', 'powershell': 'pwsh'}


def examples(text):
    # Replace documentation value fields, not shell redirections or heredocs.
    text = re.sub(r'<([A-Za-z0-9][A-Za-z0-9 _./:|()-]*)>', 'EXAMPLE', text)
    text = re.sub(r'\$\{\{[^\n]*?\}\}', 'EXPRESSION', text)
    if '${{' in text:
        raise ValueError('unsupported multiline workflow expression')
    return text


def workflow_runs(text, source, documentation=False):
    """Constrained literal YAML extractor, not a general YAML parser.

    Supports inline runs and |/|-/|+ blocks, step-level shell before/after
    run, and implicit Bash for this repo's Linux runs. Unsupported defaults,
    folded blocks, aliases and custom shells fail instead of being skipped.
    """
    lines = text.splitlines()
    if re.search(r'^\s*defaults:', text, re.M):
        raise ValueError(source + ': defaults need explicit shell resolution')
    if re.search(r'^\s*-?\s*\{.*\brun\s*:', text, re.M):
        raise ValueError(source + ': flow-mapping run unsupported')
    result, body_lines = [], set()
    for i, line in enumerate(lines):
        if i in body_lines:
            continue
        match = re.match(r'^( *)(?:- )?run:\s*(.*)$', line)
        if not match:
            continue
        indent = len(match[1]) + (2 if line.lstrip().startswith('- ') else 0)
        value = match[2]
        start = i
        while start > 0 and not re.match(r'^ {0,%d}- ' % indent, lines[start]):
            start -= 1
        end = i + 1
        while end < len(lines):
            if lines[end].strip() and len(lines[end]) - len(lines[end].lstrip()) < indent:
                break
            end += 1
        shell = None
        for item in lines[start:end]:
            sm = re.match(r'^(?: {%d}| {%d}- )shell:\s*([^#]+?)\s*(?:#.*)?$' % (indent, indent - 2), item)
            if sm:
                name = sm[1].strip().strip('\"\'')
                if name not in SHELLS:
                    raise ValueError(source + ': unsupported shell ' + name)
                shell = SHELLS[name]
        if shell is None:
            runners = re.findall(r'^\s*runs-on:\s*(.+)$', '\n'.join(lines[:i]), re.M)
            runner = runners[-1].strip() if runners else 'ubuntu-latest'
            if '${{' in runner:
                raise ValueError(source + ': dynamic runner requires explicit shell')
            shell = 'pwsh' if 'windows-' in runner.lower() else 'bash'
        if value in ('|', '|-', '|+'):
            body, j = [], i + 1
            while j < len(lines) and (not lines[j].strip() or len(lines[j]) - len(lines[j].lstrip()) > indent):
                body.append(lines[j])
                j += 1
            nonempty = [len(x) - len(x.lstrip()) for x in body if x.strip()]
            if not nonempty:
                raise ValueError(source + ': empty run block')
            width = min(nonempty)
            code = '\n'.join(x[width:] if x.strip() else '' for x in body)
            body_lines.update(range(i + 1, j))
        elif not value or value.startswith(('>', '*', '&', '!', '{', '[')):
            raise ValueError(source + ': unsupported run scalar ' + value)
        elif value.startswith('"'):
            code = json.loads(value)
        elif value.startswith("'"):
            if not value.endswith("'"):
                raise ValueError(source + ': multiline quoted run unsupported')
            code = value[1:-1].replace("''", "'")
        else:
            code = value
        # Workflow expressions are opaque values; only docs have angle placeholders.
        if documentation:
            code = examples(code)
        else:
            code = re.sub(r'\$\{\{[^\n]*?\}\}', 'EXPRESSION', code)
            if '${{' in code:
                raise ValueError(source + ': multiline expression unsupported')
        result.append((shell, code, source + ':' + str(i + 1)))
    return result


def markdown_runs(text, source):
    result, fence, body, line = [], None, [], 0
    for index, value in enumerate(text.splitlines(), 1):
        m = re.match(r'^\s*(`{3,}|~{3,})([A-Za-z0-9_-]*)\s*$', value)
        if fence is None:
            if m:
                fence = (m[1][0], len(m[1]), m[2].lower())
                body, line = [], index
        elif m and m[1][0] == fence[0] and len(m[1]) >= fence[1] and not m[2]:
            language, code = fence[2], '\n'.join(body)
            if language in SHELLS:
                result.append((SHELLS[language], examples(code), source + ':' + str(line)))
            elif language in ('yaml', 'yml'):
                result.extend(workflow_runs(code, source + ':fence' + str(line), documentation=True))
            fence = None
        else:
            body.append(value)
    if fence is not None:
        raise ValueError(source + ': unclosed Markdown fence')
    return result


def inventory(root):
    root, result = Path(root), []
    paths = list((root / '.github/workflows').glob('*.y*ml'))
    paths += list((root / 'skills/github-release/templates').glob('*.y*ml'))
    for path in sorted(paths):
        result.extend(workflow_runs(path.read_text(encoding='utf-8'), str(path.relative_to(root))))
    for path in sorted((root / 'skills/github-release').rglob('*.md')) + [root / 'README.md']:
        result.extend(markdown_runs(path.read_text(encoding='utf-8'), str(path.relative_to(root))))
    for suffix, shell in (('*.ps1', 'pwsh'), ('*.sh', 'bash')):
        for path in sorted((root / 'skills/github-release').rglob(suffix)):
            result.append((shell, path.read_text(encoding='utf-8'), str(path.relative_to(root))))
    return result


def parser(shell):
    if shell == 'bash' and os.name == 'nt':
        # Prefer Git Bash over Windows' WSL launcher.
        for base in (os.environ.get('ProgramFiles', 'C:/Program Files'), os.environ.get('LOCALAPPDATA', '')):
            path = Path(base) / 'Git/bin/bash.exe'
            if path.is_file():
                return str(path)
    found = shutil.which(shell)
    if not found:
        raise RuntimeError('required syntax parser unavailable: ' + shell)
    return found


def parse(shell, code):
    executable = parser(shell)
    if shell == 'bash':
        env = {k: v for k, v in os.environ.items()
               if k not in ('BASH_ENV', 'ENV', 'SHELLOPTS', 'BASHOPTS')}
        return subprocess.run([executable, '--noprofile', '--norc', '-n'], input=code,
                              text=True, encoding='utf-8', capture_output=True, timeout=30, env=env)
    with tempfile.TemporaryDirectory(prefix='shell-syntax-') as folder:
        path = Path(folder) / 'snippet.ps1'
        path.write_text(code, encoding='utf-8')
        command = ("$e=$null;$t=$null;$null=[System.Management.Automation.Language.Parser]::ParseFile("
                   "($env:R086_SYNTAX_FILE),[ref]$t,[ref]$e);"
                   "if($e){$e|ForEach-Object {$_.Message};exit 1};exit 0")
        env = dict(os.environ, R086_SYNTAX_FILE=str(path))
        return subprocess.run([executable, '-NoLogo', '-NoProfile', '-NonInteractive', '-Command', command],
                              text=True, encoding='utf-8', capture_output=True, timeout=30, env=env)


if __name__ == '__main__':
    checks = inventory(Path(__file__).resolve().parents[1])
    for shell, code, source in checks:
        status = parse(shell, code)
        print(('PASS' if status.returncode == 0 else 'FAIL'), shell, source)
        if status.returncode:
            raise SystemExit(status.stdout + status.stderr)
    print('PASS', len(checks), 'parser-only snippets')
