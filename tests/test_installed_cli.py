from __future__ import annotations

import importlib.util
import shutil
import subprocess
import unittest
from importlib import metadata
from pathlib import Path

import rootfileviewer


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FILE = REPO_ROOT / "examples" / "sample.root"
SAMPLE_PARQUET = REPO_ROOT / "examples" / "sample.parquet"
HAVE_PYARROW = importlib.util.find_spec("pyarrow") is not None


class InstalledCliTests(unittest.TestCase):
    def run_cli(self, command: str, *args: str) -> subprocess.CompletedProcess[str]:
        executable = shutil.which(command)
        self.assertIsNotNone(executable, f"{command} is not installed")
        return subprocess.run(
            [executable, *args],
            cwd=REPO_ROOT,
            check=False,
            capture_output=True,
            text=True,
        )

    def test_distribution_exposes_all_commands(self) -> None:
        entry_points = {
            entry_point.name: entry_point.value
            for entry_point in metadata.distribution("rootfileviewer").entry_points
            if entry_point.group == "console_scripts"
        }
        expected = "rootfileviewer.cli:main"
        self.assertEqual(entry_points.get("rootfileviewer"), expected)
        self.assertEqual(entry_points.get("rfv"), expected)
        self.assertEqual(entry_points.get("rfvt"), "rootfileviewer.cli:main_tui")

    def test_package_version(self) -> None:
        self.assertEqual(rootfileviewer.__version__, "0.7.1")

    def test_all_commands_report_their_invoked_name(self) -> None:
        for command in ("rootfileviewer", "rfv", "rfvt"):
            with self.subTest(command=command):
                result = self.run_cli(command, "--version")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), f"{command} 0.7.1")

    def test_both_commands_read_the_sample_file(self) -> None:
        for command in ("rootfileviewer", "rfv"):
            with self.subTest(command=command):
                result = self.run_cli(command, str(SAMPLE_FILE), "--terse")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"summary\tpath\t{SAMPLE_FILE}", result.stdout)
                self.assertIn("object\tevents\tTTree", result.stdout)

    def test_rfvt_implies_tui_mode(self) -> None:
        # rfvt is `rootfileviewer --tui`; --terse is mutually exclusive with
        # --tui, so passing it should hit that guard rather than run terse
        # output. This confirms --tui was injected without launching the
        # actual interactive TUI (which needs a terminal).
        result = self.run_cli("rfvt", str(SAMPLE_FILE), "--terse")
        self.assertEqual(result.returncode, 1)
        self.assertIn("--tui and --terse/-t are mutually exclusive", result.stderr)

    @unittest.skipUnless(HAVE_PYARROW, "pyarrow not installed (pip install rootfileviewer[parquet])")
    def test_both_commands_read_the_sample_parquet_file(self) -> None:
        for command in ("rootfileviewer", "rfv"):
            with self.subTest(command=command):
                result = self.run_cli(command, str(SAMPLE_PARQUET), "--terse")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"summary\tpath\t{SAMPLE_PARQUET}", result.stdout)
                self.assertIn("summary\tformat\tparquet", result.stdout)
                self.assertIn("object\ttable\tParquetTable", result.stdout)
                self.assertIn("branch\ttable\tpt\tdouble", result.stdout)
                self.assertIn("branch\ttable\tn_jets\tint32", result.stdout)

    @unittest.skipIf(HAVE_PYARROW, "pyarrow is installed; this exercises the missing-dependency path")
    def test_parquet_file_without_pyarrow_reports_install_instructions(self) -> None:
        result = self.run_cli("rootfileviewer", str(SAMPLE_PARQUET))
        self.assertEqual(result.returncode, 1)
        self.assertIn("pip install 'rootfileviewer[parquet]'", result.stderr)
        self.assertIn("pip install pyarrow", result.stderr)


if __name__ == "__main__":
    unittest.main()
