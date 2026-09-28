"""Behavior regressions for offline build and release tooling (standard library only)."""
from __future__ import annotations

import contextlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))
import build_site
import extract_data
import release_notes


class GeneratorTests(unittest.TestCase):
    def test_rebuild_missing_data_artifact(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            output = root / "missing/assets/playbooks.js"
            with patch.multiple(extract_data, ROOT=root, OUTPUT=output), \
                    patch.object(sys, "argv", ["extract_data.py", "--check"]), \
                    contextlib.redirect_stderr(io.StringIO()), contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(extract_data.main(), 1)
                self.assertFalse(output.exists())
                with patch.object(sys, "argv", ["extract_data.py"]):
                    self.assertEqual(extract_data.main(), 0)
                self.assertEqual(extract_data.main(), 0)
                self.assertIn("window.CRS_DATA", output.read_text(encoding="utf-8"))

    def test_duplicate_index_is_rejected(self):
        rows = extract_data.read_index()
        with patch.object(extract_data, "read_index", return_value=rows + rows[:1]):
            with self.assertRaisesRegex(ValueError, "duplicate"):
                extract_data.build_data()

    def test_translation_escapes_plain_text_but_preserves_explicit_html(self):
        parser = build_site.EnglishRewriter({"plain": '<img src=x onerror="bad()"> & text',
                                           "html": '<strong>Safe markup</strong>'}, "")
        parser.feed('<p data-i18n="plain">原文</p><p data-i18n-html="html">原文</p>')
        result = "".join(parser.out)
        self.assertNotIn("<img", result)
        self.assertIn("&lt;img", result)
        self.assertIn("&amp; text", result)
        self.assertIn("<strong>Safe markup</strong>", result)

    def test_jsonld_cannot_close_script(self):
        rendered = build_site.render_jsonld({"name": "</script><script>alert(1)</script>"})
        self.assertEqual(rendered.count("</script>"), 1)
        value = json.loads(rendered.split('application/ld+json">', 1)[1].rsplit("</script>", 1)[0])
        self.assertEqual(value["name"], "</script><script>alert(1)</script>")

    def test_release_notes_only_include_requested_version(self):
        with tempfile.TemporaryDirectory() as temp:
            changelog = Path(temp) / "CHANGELOG.md"
            changelog.write_text("## [Unreleased]\n\nNext\n\n## [1.2.0] - 2026-09-09\n\nCurrent\n\n## [1.1.0] - 2026-08-01\n\nOld\n", encoding="utf-8")
            with patch.object(release_notes, "CHANGELOG", changelog):
                self.assertEqual(release_notes.extract_section("1.2.0"), ("2026-09-09", "Current"))
                with self.assertRaises(SystemExit):
                    release_notes.extract_section("9.9.9")
                changelog.write_text("## [1.2.0] - 2026-09-09\n\n", encoding="utf-8")
                with self.assertRaises(SystemExit):
                    release_notes.extract_section("1.2.0")

    def test_invalid_explicit_release_version_rejected(self):
        with patch.object(sys, "argv", ["release_notes.py", "--version", "bad\nvalue", "--print-version"]), \
                contextlib.redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as error:
                release_notes.main()
            self.assertEqual(error.exception.code, 2)


if __name__ == "__main__":
    unittest.main()
