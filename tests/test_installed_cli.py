from __future__ import annotations

import shutil
import subprocess
import unittest
from importlib import metadata
from pathlib import Path

import rootfileviewer


REPO_ROOT = Path(__file__).resolve().parents[1]
SAMPLE_FILE = REPO_ROOT / "examples" / "sample.root"


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

    def test_distribution_exposes_both_commands(self) -> None:
        entry_points = {
            entry_point.name: entry_point.value
            for entry_point in metadata.distribution("rootfileviewer").entry_points
            if entry_point.group == "console_scripts"
        }
        expected = "rootfileviewer.cli:main"
        self.assertEqual(entry_points.get("rootfileviewer"), expected)
        self.assertEqual(entry_points.get("rfv"), expected)

    def test_package_version(self) -> None:
        self.assertEqual(rootfileviewer.__version__, "0.5.0")

    def test_both_commands_report_their_invoked_name(self) -> None:
        for command in ("rootfileviewer", "rfv"):
            with self.subTest(command=command):
                result = self.run_cli(command, "--version")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), f"{command} 0.5.0")

    def test_both_commands_read_the_sample_file(self) -> None:
        for command in ("rootfileviewer", "rfv"):
            with self.subTest(command=command):
                result = self.run_cli(command, str(SAMPLE_FILE), "--terse")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"summary\tpath\t{SAMPLE_FILE}", result.stdout)
                self.assertIn("object\tevents\tTTree", result.stdout)


if __name__ == "__main__":
    unittest.main()
