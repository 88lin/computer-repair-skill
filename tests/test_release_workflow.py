"""Run the release decision shell with local fakes; no GitHub calls or git writes."""
import os
from pathlib import Path
import re
import subprocess
import tempfile
import unittest

from test_installers import BASH, ROOT, shell_path


@unittest.skipUnless(BASH, "Bash required")
class ReleaseWorkflowTests(unittest.TestCase):
    def test_release_retry_states_and_api_errors(self):
        source = (ROOT / ".github/workflows/release.yml").read_text(encoding="utf-8")
        block = source.split("- name: Resolve version", 1)[1].split("- name:", 1)[0]
        commands = re.search(r"(?s)run: \|\n(.*)", block).group(1)
        commands = "\n".join(line[10:] for line in commands.splitlines() if line.strip())
        fakes = '''set -euo pipefail
gh() {
  case "$SCENARIO" in
    release) return 0 ;;
    api_error) printf 'HTTP 403\n' >&2; return 1 ;;
    *) printf 'HTTP 404\n' >&2; return 1 ;;
  esac
}
git() {
  [[ "$*" = show-ref* ]] || return 99
  [[ "$SCENARIO" = tag_only || "$SCENARIO" = release ]]
}
'''
        with tempfile.TemporaryDirectory(prefix="release-test-") as temp:
            root = Path(temp)
            script = root / "check.sh"
            script.write_text(fakes + commands + "\n", encoding="utf-8", newline="\n")
            for scenario, exists, tag_exists in (
                ("release", "true", "true"), ("tag_only", "false", "true"),
                ("new", "false", "false"), ("api_error", None, None),
            ):
                with self.subTest(scenario=scenario):
                    output = root / (scenario + ".out")
                    env = dict(os.environ, SCENARIO=scenario, RUNNER_TEMP=shell_path(root),
                               GITHUB_OUTPUT=shell_path(output), GITHUB_REPOSITORY="fixture/repo", PYTHONUTF8="1")
                    result = subprocess.run([BASH, shell_path(script)], cwd=ROOT, env=env,
                                            capture_output=True, timeout=20)
                    self.assertEqual(result.returncode == 0, scenario != "api_error", result.stderr)
                    data = output.read_text(encoding="utf-8")
                    if exists is not None:
                        self.assertIn("\nexists=" + exists + "\n", data)
                        self.assertIn("\ntag_exists=" + tag_exists + "\n", data)
                    else:
                        self.assertNotIn("exists=false", data)


if __name__ == "__main__":
    unittest.main()
