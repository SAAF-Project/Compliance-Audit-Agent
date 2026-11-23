"""Synthetic public-entry-point tests; never import or reconstruct private code."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

SOURCE = Path(__file__).resolve().parents[2] / "scripts/orchestration.py"


class PublicLauncher(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.script_dir = self.root / "scripts"
        self.script_dir.mkdir()
        self.script = self.script_dir / "orchestration.py"
        shutil.copyfile(SOURCE, self.script)
        self.guidelines = self.root / "guidelines.json"
        self.guidelines.write_text('{"27": "Synthetic guideline only."}', encoding="utf-8")
        self.progress = self.root / "progress"
        self.marker = self.root / "unexpected-import"

    def run_cli(self, *args):
        env = {"PATH": os.defpath, "HOME": str(self.root), "TMPDIR": str(self.root)}
        return subprocess.run([sys.executable, "-I", "-S", str(self.script),
            "--guideline-file", str(self.guidelines), "--progress-path", str(self.progress), *args],
            cwd=self.root, env=env, capture_output=True, text=True, timeout=5)

    def stub(self, result="{'status': 'synthetic'}", missing="[]", extra=""):
        (self.script_dir / "utils.py").write_text(
            "OFFLINE_MISSING_REPLIES = " + missing + "\n"
            "def configure(*args): pass\n"
            "def main(*args): return " + result + "\n" + extra, encoding="utf-8")

    def test_public_missing_runtime_fails_without_output_or_working_directory_import(self):
        (self.root / "utils.py").write_text("raise AssertionError('cwd helper executed')")
        self.guidelines.unlink()
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("not distributed", result.stderr)
        self.assertNotIn("AssertionError", result.stderr)
        self.assertFalse(self.progress.exists())

    def test_status_requires_no_private_runtime_or_inputs(self):
        self.guidelines.unlink()
        self.stub(extra="raise AssertionError('status loaded private runtime')\n")
        result = self.run_cli("--status")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse(json.loads(result.stdout)["pipeline_verified"])
        self.assertFalse(self.progress.exists())

    def test_import_does_not_parse_arguments_read_inputs_or_import_runtime(self):
        self.stub(extra="raise AssertionError('import loaded private runtime')\n")
        spec = importlib.util.spec_from_file_location("public_launcher_test", self.script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        self.assertTrue(callable(module.main))
        self.assertFalse(self.progress.exists())

    def test_symlink_runtime_is_refused(self):
        target = self.root / "elsewhere.py"
        target.write_text("raise AssertionError('symlink runtime executed')")
        (self.script_dir / "utils.py").symlink_to(target)
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("not distributed", result.stderr)

    def test_malformed_missing_or_wrong_type_guidelines_fail_before_runtime_import(self):
        self.stub(extra="raise AssertionError('invalid input loaded runtime')\n")
        for data in ["{broken", "[]", "{}", '{"27": []}', '{"27": "  "}']:
            with self.subTest(data=data):
                self.guidelines.write_text(data)
                result = self.run_cli()
                self.assertEqual(result.returncode, 2)
                self.assertNotIn("AssertionError", result.stderr)
                self.assertFalse(self.progress.exists())

    def test_duplicate_guideline_keys_fail_before_private_code(self):
        self.stub(extra="raise AssertionError('duplicate input loaded runtime')\n")
        self.guidelines.write_text('{"27":"first synthetic version","27":"conflicting version"}')
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("duplicate key", result.stderr)
        self.assertNotIn("AssertionError", result.stderr)
        self.assertFalse(self.progress.exists())

    def test_private_system_exit_cannot_announce_success_or_expose_content(self):
        for stage in ["import", "configure", "main"]:
            for value in ["0", "'SYNTHETIC_PRIVATE_EXIT_SENTINEL'"]:
                with self.subTest(stage=stage, value=value):
                    if stage == "import":
                        extra = "raise SystemExit(" + value + ")\n"
                    else:
                        extra = "def " + stage + "(*args): raise SystemExit(" + value + ")\n"
                    self.stub(extra=extra)
                    result = self.run_cli()
                    self.assertEqual(result.returncode, 2)
                    self.assertIn("incomplete", result.stderr)
                    self.assertNotIn("SYNTHETIC_PRIVATE_EXIT_SENTINEL", result.stderr)
                    self.assertEqual(list(self.progress.glob("output_combined*")), [])

    def test_same_second_retry_preserves_existing_combined_evidence(self):
        self.stub()
        self.progress.mkdir()
        existing = self.progress / "output_combined_20000101_000000.json"
        original = b'{"synthetic_previous_evidence":true}\n'
        existing.write_bytes(original)
        spec = importlib.util.spec_from_file_location("collision_launcher_test", self.script)
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        stderr = io.StringIO()
        with mock.patch.object(module, "datetime") as clock, mock.patch.dict(sys.modules), \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(stderr):
            clock.now.return_value.strftime.return_value = "20000101_000000"
            code = module.main(["--guideline-file", str(self.guidelines),
                                "--progress-path", str(self.progress)])
        self.assertEqual(code, 2)
        self.assertIn("FileExistsError", stderr.getvalue())
        self.assertEqual(existing.read_bytes(), original)
        self.assertEqual(len(list(self.progress.glob("output_combined*"))), 1)

    def test_only_explicit_sibling_runtime_is_used(self):
        (self.root / "utils.py").write_text("raise AssertionError('cwd helper executed')")
        self.stub()
        result = self.run_cli()
        self.assertEqual(result.returncode, 0, result.stderr)
        outputs = list(self.progress.glob("output_combined_*.json"))
        self.assertEqual(len(outputs), 1)
        self.assertEqual(json.loads(outputs[0].read_text()), [{"status": "synthetic"}])

    def test_no_results_is_incomplete_not_success(self):
        self.stub(result="None")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("No guideline produced results", result.stderr)
        self.assertEqual(list(self.progress.glob("output_combined*")), [])

    def test_missing_saved_reply_retains_partial_artifact_but_returns_incomplete(self):
        self.stub(missing="['synthetic-stage']")
        result = self.run_cli("--load-progress", "synthetic-run")
        self.assertEqual(result.returncode, 2)
        output = json.loads(next(self.progress.glob("output_combined*" )).read_text())
        self.assertIn("incomplete", output["note"])
        self.assertNotIn("no API calls were made", output["note"])

    def test_private_failure_does_not_expose_exception_content(self):
        self.stub(extra="raise ValueError('SYNTHETIC_PRIVATE_ERROR_SENTINEL')\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("ValueError", result.stderr)
        self.assertNotIn("SYNTHETIC_PRIVATE_ERROR_SENTINEL", result.stderr)
        self.assertFalse(self.progress.exists())

    def test_incomplete_runtime_contract_is_refused(self):
        (self.script_dir / "utils.py").write_text("def main(*args): return {}\n")
        result = self.run_cli()
        self.assertEqual(result.returncode, 2)
        self.assertIn("required entry-point contract", result.stderr)

    def test_inconsistent_replay_flags_are_refused(self):
        for flags in [["--no-data-testmode"], ["--no-data-testmode", "--validate"]]:
            result = self.run_cli(*flags)
            self.assertEqual(result.returncode, 2)
            self.assertIn("requires both", result.stderr)
            self.assertFalse(self.progress.exists())


if __name__ == "__main__":
    unittest.main()
