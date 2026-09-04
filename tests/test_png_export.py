from __future__ import annotations

import importlib.util
import tempfile
import unittest
from pathlib import Path

from rootfileviewer.png_export import _bin_widths

HAVE_MATPLOTLIB = importlib.util.find_spec("matplotlib") is not None


class BinWidthsTests(unittest.TestCase):
    """Pure math, no matplotlib needed -- runs unconditionally."""

    def test_evenly_spaced_centers_get_equal_widths(self) -> None:
        widths = _bin_widths([1.0, 2.0, 3.0, 4.0])
        self.assertEqual(len(widths), 4)
        self.assertTrue(all(abs(w - 1.0) < 1e-9 for w in widths))

    def test_geometrically_spaced_centers_get_increasing_widths(self) -> None:
        # log-x bins: ratio between consecutive centers is constant, so
        # widths should increase monotonically (each bin wider than the last).
        centers = [10.0**i for i in range(5)]
        widths = _bin_widths(centers)
        self.assertEqual(len(widths), 5)
        self.assertTrue(all(widths[i] < widths[i + 1] for i in range(len(widths) - 1)))

    def test_single_center_does_not_crash(self) -> None:
        self.assertEqual(_bin_widths([5.0]), [1.0])


@unittest.skipUnless(HAVE_MATPLOTLIB, "matplotlib not installed (pip install rootfileviewer[matplotlib])")
class ExportPngTests(unittest.TestCase):
    def _tmp_path(self) -> str:
        return str(Path(tempfile.mkdtemp()) / "test.png")

    def test_linear_plot_produces_a_valid_png(self) -> None:
        from rootfileviewer.png_export import export_png

        path = self._tmp_path()
        export_png(path, "pt", "sample.root — 2,000 entries", [1.0, 2.0, 3.0], [5, 3, 8])
        self.assertTrue(Path(path).exists())
        self.assertGreater(Path(path).stat().st_size, 0)
        with open(path, "rb") as f:
            self.assertEqual(f.read(8), b"\x89PNG\r\n\x1a\n")

    def test_log_x_and_log_y_plot_produces_a_valid_png(self) -> None:
        from rootfileviewer.png_export import export_png

        path = self._tmp_path()
        centers = [10.0**i for i in range(5)]
        values = [5, 4, 6, 3, 8]
        export_png(path, "pt", "log test", centers, values, log_x=True, log_y=True)
        self.assertTrue(Path(path).exists())
        self.assertGreater(Path(path).stat().st_size, 0)


@unittest.skipIf(HAVE_MATPLOTLIB, "matplotlib is installed; this exercises the missing-dependency path")
class ExportPngWithoutMatplotlibTests(unittest.TestCase):
    def test_export_png_raises_import_error(self) -> None:
        from rootfileviewer.png_export import export_png

        with self.assertRaises(ImportError):
            export_png("unused.png", "pt", "subtitle", [1.0, 2.0], [1, 2])


if __name__ == "__main__":
    unittest.main()
