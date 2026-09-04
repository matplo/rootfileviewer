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
SAMPLE_HDF5 = REPO_ROOT / "examples" / "sample.h5"
SAMPLE_NPZ = REPO_ROOT / "examples" / "sample.npz"
SAMPLE_NPY = REPO_ROOT / "examples" / "sample.npy"
SAMPLE_CSV = REPO_ROOT / "examples" / "sample.csv"
SAMPLE_PICKLE = REPO_ROOT / "examples" / "sample.pkl"
HAVE_PYARROW = importlib.util.find_spec("pyarrow") is not None
HAVE_H5PY = importlib.util.find_spec("h5py") is not None
HAVE_PANDAS = importlib.util.find_spec("pandas") is not None


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
        self.assertEqual(rootfileviewer.__version__, "0.10.0")

    def test_all_commands_report_their_invoked_name(self) -> None:
        for command in ("rootfileviewer", "rfv", "rfvt"):
            with self.subTest(command=command):
                result = self.run_cli(command, "--version")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(result.stdout.strip(), f"{command} 0.10.0")

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

    @unittest.skipUnless(HAVE_H5PY, "h5py not installed (pip install rootfileviewer[hdf5])")
    def test_both_commands_read_the_sample_hdf5_file(self) -> None:
        for command in ("rootfileviewer", "rfv"):
            with self.subTest(command=command):
                result = self.run_cli(command, str(SAMPLE_HDF5), "--terse")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"summary\tpath\t{SAMPLE_HDF5}", result.stdout)
                self.assertIn("summary\tformat\thdf5", result.stdout)
                self.assertIn("object\taux\tHDF5Group", result.stdout)
                self.assertIn("object\tpt\tfloat64[2000]\tentries=2000", result.stdout)
                self.assertIn("object\ttracks_energy\tvlen<float64>[2000]\tentries=2000", result.stdout)
                self.assertIn("object\tjet\tHDF5FeatureSet\tentries=500\tbranches=3", result.stdout)
                self.assertIn("branch\tjet\teta\tfloat32", result.stdout)

    @unittest.skipIf(HAVE_H5PY, "h5py is installed; this exercises the missing-dependency path")
    def test_hdf5_file_without_h5py_reports_install_instructions(self) -> None:
        result = self.run_cli("rootfileviewer", str(SAMPLE_HDF5))
        self.assertEqual(result.returncode, 1)
        self.assertIn("pip install 'rootfileviewer[hdf5]'", result.stderr)
        self.assertIn("pip install h5py", result.stderr)

    def test_both_commands_read_the_sample_npz_file(self) -> None:
        # numpy is always available (uproot's own dependency), so this needs
        # no skip guard, unlike the parquet/hdf5 tests above.
        for command in ("rootfileviewer", "rfv"):
            with self.subTest(command=command):
                result = self.run_cli(command, str(SAMPLE_NPZ), "--terse")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"summary\tpath\t{SAMPLE_NPZ}", result.stdout)
                self.assertIn("summary\tformat\tnumpy", result.stdout)
                self.assertIn("object\tpt\tfloat64[2000]\tentries=2000", result.stdout)
                self.assertIn("object\ttracks_energy\tragged<float64>[2000]\tentries=2000", result.stdout)

    def test_both_commands_read_the_sample_npy_file(self) -> None:
        for command in ("rootfileviewer", "rfv"):
            with self.subTest(command=command):
                result = self.run_cli(command, str(SAMPLE_NPY), "--terse")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"summary\tpath\t{SAMPLE_NPY}", result.stdout)
                self.assertIn("object\tsample\tfloat64[2000]\tentries=2000", result.stdout)

    @unittest.skipUnless(HAVE_PANDAS, "pandas not installed (pip install rootfileviewer[pandas])")
    def test_both_commands_read_the_sample_csv_file(self) -> None:
        for command in ("rootfileviewer", "rfv"):
            with self.subTest(command=command):
                result = self.run_cli(command, str(SAMPLE_CSV), "--terse")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn(f"summary\tpath\t{SAMPLE_CSV}", result.stdout)
                self.assertIn("summary\tformat\tpandas", result.stdout)
                self.assertIn("object\ttable\tDataFrameTable", result.stdout)
                self.assertIn("branch\ttable\tpt\tfloat64", result.stdout)

    @unittest.skipUnless(HAVE_PANDAS, "pandas not installed (pip install rootfileviewer[pandas])")
    def test_both_commands_read_the_sample_pickle_file_with_ragged_column(self) -> None:
        for command in ("rootfileviewer", "rfv"):
            with self.subTest(command=command):
                result = self.run_cli(command, str(SAMPLE_PICKLE), "--terse")
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertIn("branch\ttable\ttracks_energy\tragged<float64>", result.stdout)

    @unittest.skipIf(HAVE_PANDAS, "pandas is installed; this exercises the missing-dependency path")
    def test_csv_file_without_pandas_reports_install_instructions(self) -> None:
        result = self.run_cli("rootfileviewer", str(SAMPLE_CSV))
        self.assertEqual(result.returncode, 1)
        self.assertIn("reading .csv files needs: pandas", result.stderr)
        self.assertIn("pip install 'rootfileviewer[pandas]'", result.stderr)
        self.assertIn("pip install pandas", result.stderr)


if __name__ == "__main__":
    unittest.main()
