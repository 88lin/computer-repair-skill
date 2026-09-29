"""Exercise installers only inside temporary fixtures; never touch real Agent installs."""
from __future__ import annotations

import os
import re
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = "computer-repair-skill"
PWSH = shutil.which("pwsh") or shutil.which("powershell")
BASH = shutil.which("bash")
if not BASH and Path("C:/Program Files/Git/bin/bash.exe").is_file():
    BASH = "C:/Program Files/Git/bin/bash.exe"
BACKENDS = [name for name, executable in (("ps", PWSH), ("bash", BASH)) if executable]


def shell_path(path: Path) -> str:
    value = path.as_posix()
    if os.name == "nt" and len(value) > 1 and value[1] == ":":
        value = "/" + value[0].lower() + value[2:]
    return value


@unittest.skipUnless(BACKENDS, "PowerShell or Bash required")
class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix="repair installer ")
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name)
        self.repo = self.base / "repo"
        shutil.copytree(ROOT / "scripts", self.repo / "scripts")
        self.source = self.repo / "skills" / SKILL
        self.source.mkdir(parents=True)
        for name in ("SKILL.md", "LICENSE", "NOTICE", "agents/openai.yaml",
                     "references/playbook-index.md", "scripts/git_storage_audit.py"):
            file = self.source / name
            file.parent.mkdir(parents=True, exist_ok=True)
            file.write_text("fixture " + name, encoding="utf-8")

    def run_install(self, backend, dest, force=False, fail_cutover=False):
        env = dict(os.environ, PYTHONUTF8="1")
        if backend == "ps":
            script = self.repo / "scripts/install.ps1"
            cmd = [PWSH, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass"]
            if fail_cutover:
                wrapper = self.base / "fail-cutover.ps1"
                wrapper.write_text('''param($Installer, $Destination)
function Move-Item {
    param($LiteralPath, $Destination)
    if ((Split-Path $LiteralPath -Leaf) -like '.computer-repair-skill.install-*') {
        throw 'Injected cutover failure'
    }
    Microsoft.PowerShell.Management\\Move-Item -LiteralPath $LiteralPath -Destination $Destination
}
& $Installer -Target custom -Destination $Destination -Force
''', encoding="utf-8-sig")
                cmd += ["-File", str(wrapper), str(script), str(dest)]
            else:
                cmd += ["-File", str(script), "-Target", "custom", "-Destination", str(dest)]
                if force:
                    cmd.append("-Force")
        else:
            cmd = [BASH, shell_path(self.repo / "scripts/install.sh"), "--target", "custom",
                   "--destination", shell_path(dest) if isinstance(dest, Path) else dest]
            if force:
                cmd.append("--force")
            if fail_cutover:
                wrapper = self.repo / "scripts/fail-cutover.sh"
                wrapper.write_text('''#!/usr/bin/env bash
mv() {
  case "$2" in */.computer-repair-skill.install[.-]*) return 73 ;; esac
  command mv "$@"
}
installer="$1"
shift
source "$installer" "$@"
''', encoding="utf-8", newline="\n")
                cmd.insert(1, shell_path(wrapper))
        return subprocess.run(cmd, cwd=self.repo, env=env, capture_output=True, timeout=30)

    def assert_result(self, result, success):
        self.assertEqual(result.returncode == 0, success,
                         (result.stdout + result.stderr).decode("utf-8", errors="replace"))

    def test_install_refuse_and_backup(self):
        for backend in BACKENDS:
            with self.subTest(backend=backend):
                dest = self.base / backend / "skills with spaces"
                self.assert_result(self.run_install(backend, dest), True)
                old = dest / SKILL / "local-marker.txt"
                old.write_text("keep this", encoding="utf-8")
                self.assert_result(self.run_install(backend, dest), False)
                self.assertTrue(old.is_file())
                self.assert_result(self.run_install(backend, dest, force=True), True)
                self.assertFalse(old.exists())
                backups = list((dest.parent / "external").rglob("local-marker.txt"))
                self.assertEqual(len(backups), 1)
                self.assertEqual(backups[0].read_text(), "keep this")
                self.assertEqual((dest / SKILL / "SKILL.md").read_bytes(), (self.source / "SKILL.md").read_bytes())
                self.assertEqual((dest / SKILL / "scripts/git_storage_audit.py").read_bytes(),
                                 (self.source / "scripts/git_storage_audit.py").read_bytes())
                self.assertFalse(list(dest.glob(".computer-repair-skill.install*")))

    def test_overlapping_source_refused(self):
        for backend in BACKENDS:
            for dest in (self.source.parent, self.source, self.source / "nested"):
                with self.subTest(backend=backend, dest=dest):
                    self.assert_result(self.run_install(backend, dest, force=True), False)
                    self.assertEqual((self.source / "SKILL.md").read_text(), "fixture SKILL.md")
                    self.assertFalse(list(self.source.rglob(".computer-repair-skill.install*")))

    def test_regular_file_target_refused(self):
        for backend in BACKENDS:
            dest = self.base / backend / "skills"
            dest.mkdir(parents=True)
            target = dest / SKILL
            target.write_text("not an install", encoding="utf-8")
            self.assert_result(self.run_install(backend, dest, force=True), False)
            self.assertEqual(target.read_text(), "not an install")

    def test_existing_lock_refused(self):
        for backend in BACKENDS:
            for kind in ("file", "directory"):
                with self.subTest(backend=backend, kind=kind):
                    dest = self.base / backend / kind / "skills"
                    dest.mkdir(parents=True)
                    lock = dest / ".computer-repair-skill.install.lock"
                    if kind == "file":
                        lock.write_text("active install", encoding="utf-8")
                    else:
                        lock.mkdir()
                    self.assert_result(self.run_install(backend, dest, force=True), False)
                    self.assertTrue(lock.exists())
                    self.assertFalse((dest / SKILL).exists())

    def test_cutover_failure_restores_old_install(self):
        for backend in BACKENDS:
            with self.subTest(backend=backend):
                dest = self.base / backend / "skills"
                self.assert_result(self.run_install(backend, dest), True)
                old = dest / SKILL / "local-marker.txt"
                old.write_text("restore me", encoding="utf-8")
                self.assert_result(self.run_install(backend, dest, force=True, fail_cutover=True), False)
                self.assertEqual(old.read_text(), "restore me")
                self.assertFalse(list(dest.glob(".computer-repair-skill.install*")))

    def test_incomplete_source_refused(self):
        (self.source / "NOTICE").unlink()
        for backend in BACKENDS:
            dest = self.base / backend / "skills"
            self.assert_result(self.run_install(backend, dest), False)
            self.assertFalse((dest / SKILL).exists())

    def test_link_target_refused(self):
        self.check_link_target(dangling=False)

    def test_dangling_link_target_refused(self):
        self.check_link_target(dangling=True)

    def check_link_target(self, dangling):
        target = self.base / "managed-source"
        target.mkdir()
        (target / "marker").write_text("preserve", encoding="utf-8")
        for backend in BACKENDS:
            dest = self.base / backend / "skills"
            dest.mkdir(parents=True)
            link = dest / SKILL
            if os.name == "nt":
                if not PWSH:
                    self.skipTest("PowerShell required to create a junction")
                env = dict(os.environ, TEST_LINK=str(link), TEST_TARGET=str(target))
                result = subprocess.run([PWSH, "-NoProfile", "-Command",
                    "New-Item -ItemType Junction -Path $env:TEST_LINK -Target $env:TEST_TARGET | Out-Null"],
                    env=env, capture_output=True, timeout=15)
                self.assert_result(result, True)
            else:
                link.symlink_to(target, target_is_directory=True)
            if dangling:
                (target / "marker").unlink()
                target.rmdir()
            self.assert_result(self.run_install(backend, dest, force=True), False)
            if dangling:
                self.assertFalse(target.exists())
            else:
                self.assertEqual((target / "marker").read_text(), "preserve")
            # Remove only the fixture link; never recurse into its target.
            if os.name == "nt":
                link.rmdir()
            else:
                link.unlink()
            if dangling:
                target.mkdir()
                (target / "marker").write_text("preserve", encoding="utf-8")

    @unittest.skipUnless(BASH, "Bash required")
    def test_quoted_tilde_expansion(self):
        # Exercise expansion without writing to the real home or overriding HOME.
        source = (self.repo / "scripts/install.sh").read_text(encoding="utf-8")
        function = re.search(r"(?ms)^expand_user_path\(\) \{.*?^\}", source).group()
        result = subprocess.run([BASH, "-c", function + '\nactual=$(expand_user_path "~/tilde skills")\n'
            + 'test "$actual" = "$HOME/tilde skills"'], capture_output=True, timeout=15)
        self.assert_result(result, True)


if __name__ == "__main__":
    unittest.main()
