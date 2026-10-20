"""popia-kit init: rules files, workflow and .popiaignore, without clobbering anything."""
import io
import os
import shutil
import sys
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

import cli  # noqa: E402
import popia_init  # noqa: E402


class TestInit(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp(prefix="popia-init-"))

    def tearDown(self):
        shutil.rmtree(self.dir, ignore_errors=True)

    def init(self, *args):
        out, err = io.StringIO(), io.StringIO()
        with redirect_stdout(out), redirect_stderr(err):
            code = cli.main(["init", str(self.dir), *args])
        return code, out.getvalue(), err.getvalue()

    def read(self, rel):
        return (self.dir / rel).read_text(encoding="utf-8")

    def test_empty_project_gets_agents_workflow_and_ignore(self):
        code, out, _ = self.init()
        self.assertEqual(code, 0)
        self.assertIn(popia_init.START, self.read("AGENTS.md"))
        self.assertIn("POPIA scan", self.read(".github/workflows/popia-scan.yml"))
        self.assertTrue((self.dir / ".popiaignore").is_file())
        self.assertIn("not legal advice", out)

    def test_detects_tools_in_use(self):
        (self.dir / ".cursor").mkdir()
        (self.dir / "CLAUDE.md").write_text("# House rules\n", encoding="utf-8")
        self.assertEqual(popia_init.detect(self.dir), ["claude", "cursor"])
        self.init()
        self.assertTrue((self.dir / ".cursor" / "rules" / "popia.mdc").is_file())
        self.assertFalse((self.dir / "AGENTS.md").exists())

    def test_shared_file_keeps_user_content_and_updates_in_place(self):
        (self.dir / "CLAUDE.md").write_text("# House rules\n\nUse tabs.\n", encoding="utf-8")
        self.init("--tools", "claude")
        first = self.read("CLAUDE.md")
        self.assertTrue(first.startswith("# House rules\n\nUse tabs.\n\n" + popia_init.START))
        code, out, _ = self.init("--tools", "claude")
        self.assertEqual(self.read("CLAUDE.md"), first)
        self.assertIn("already up to date", out)

        stale = first.replace("Minimise", "OLD WORDING")
        (self.dir / "CLAUDE.md").write_text(stale + "\nMore of my notes.\n", encoding="utf-8")
        self.init("--tools", "claude")
        text = self.read("CLAUDE.md")
        self.assertNotIn("OLD WORDING", text)
        self.assertEqual(text.count(popia_init.START), 1)
        self.assertTrue(text.endswith("More of my notes.\n"))

    def test_existing_dedicated_file_left_alone_unless_forced(self):
        dest = self.dir / ".github" / "workflows" / "popia-scan.yml"
        dest.parent.mkdir(parents=True)
        dest.write_text("mine\n", encoding="utf-8")
        self.init("--tools", "agents")
        self.assertEqual(dest.read_text(encoding="utf-8"), "mine\n")
        self.init("--tools", "agents", "--force")
        self.assertIn("POPIA scan", dest.read_text(encoding="utf-8"))

    def test_dry_run_writes_nothing(self):
        code, out, _ = self.init("--dry-run")
        self.assertEqual(code, 0)
        self.assertIn("dry run", out)
        self.assertEqual(list(self.dir.iterdir()), [])

    def test_opt_outs(self):
        self.init("--tools", "gemini", "--no-workflow", "--no-ignore")
        self.assertEqual(sorted(p.name for p in self.dir.iterdir()), ["GEMINI.md"])

    def test_unknown_tool(self):
        code, _, err = self.init("--tools", "notepad")
        self.assertEqual(code, 2)
        self.assertIn("unknown tool", err)

    @unittest.skipIf(os.name == "nt", "symlinks need privileges on Windows")
    def test_never_writes_through_a_symlink(self):
        outside = Path(tempfile.mkdtemp(prefix="popia-outside-"))
        try:
            (self.dir / ".github").symlink_to(outside, target_is_directory=True)
            code, out, _ = self.init("--tools", "copilot", "--no-ignore")
            self.assertEqual(code, 1)
            self.assertIn("refuse", out)
            self.assertEqual(list(outside.iterdir()), [])
        finally:
            shutil.rmtree(outside, ignore_errors=True)

    def test_every_adapter_source_exists(self):
        for tool, (src, _, _) in popia_init.TOOLS.items():
            self.assertTrue((popia_init.ADAPTERS_DIR / src).is_file(), tool)


if __name__ == "__main__":
    unittest.main()
