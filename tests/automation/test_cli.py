"""popia-kit entry point: dispatch, version and errors."""
import io
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import cli  # noqa: E402


class TestCli(unittest.TestCase):
    def run_cli(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(list(args))
        return code, out.getvalue(), err.getvalue()

    def test_help_and_version(self):
        code, out, _ = self.run_cli()
        self.assertEqual(code, 0)
        self.assertIn("scan", out)
        self.assertIn("not legal advice", out)
        code, out, _ = self.run_cli("version")
        self.assertEqual((code, out.strip()), (0, "popia-kit " + cli.VERSION))

    def test_unknown_command(self):
        code, _, err = self.run_cli("nope")
        self.assertEqual(code, 2)
        self.assertIn("unknown command", err)

    def test_scan_dispatch(self):
        code, out, _ = self.run_cli("scan", str(ROOT / "tests" / "fixtures" / "demo-app"), "--format", "json")
        self.assertIn('"summary"', out)
        self.assertIn(code, (0, 1))

    def test_id_does_not_echo_number(self):
        code, out, _ = self.run_cli("id", "mask", "5912280409005")
        self.assertEqual(code, 0)
        self.assertNotIn("5912280409", out)

    def test_versions_agree(self):
        import json
        import re
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        self.assertIn('version = "%s"' % cli.VERSION, pyproject)
        pkg = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
        self.assertEqual(pkg["version"], cli.VERSION)
        self.assertTrue(re.match(r"^\d+\.\d+\.\d+$", cli.VERSION))


if __name__ == "__main__":
    unittest.main()
