"""2.0.2: pages and windows scale their texts with the size of their area (theme.font_qss / area_scale / scale_html)."""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import qt_stub
qt_stub.install()

from app.infodoc import render_text, scale_html           # noqa: E402
from app.ui import theme                                   # noqa: E402


class ScaleTests(unittest.TestCase):
    def test_area_scale_uses_the_smaller_side_and_limits(self):
        self.assertEqual(theme.area_scale(660, 520), 1.0)
        self.assertEqual(theme.area_scale(1320, 400), 0.75)          # low window: the height decides
        self.assertEqual(theme.area_scale(200, 200), 0.7)            # lower limit
        self.assertEqual(theme.area_scale(3000, 3000), 1.5)          # upper limit

    def test_font_qss_scales_every_font_size_of_the_theme(self):
        base = {m.group(1).strip(): int(m.group(2)) for m in
                re.finditer(r"([^{}]+)\{[^{}]*?font-size:\s*(\d+)px", theme.STYLE)}
        self.assertGreater(len(base), 30)
        q = theme.font_qss(1.5)
        got = {m.group(1).strip(): int(m.group(2)) for m in re.finditer(r"([^{}]+)\{\s*font-size:\s*(\d+)px", q)}
        self.assertEqual(set(got), set(base))
        for sel, size in base.items():
            self.assertEqual(got[sel], max(8, round(size * 1.5)), sel)
        self.assertEqual(theme.font_qss(1.0), theme.font_qss(1.01))  # steps of 0.05 are cached

    def test_info_html_scales(self):
        html = render_text("# Title\n\nSome text")
        sizes = lambda h: [int(x) for x in re.findall(r"font-size:\s*(\d+)px", h)]      # noqa: E731
        base = sizes(html)
        self.assertTrue(base)
        self.assertEqual(sizes(scale_html(html, 1.0)), base)
        self.assertEqual(sizes(scale_html(html, 2.0)), [max(9, round(x * 2)) for x in base])


if __name__ == "__main__":
    unittest.main()
