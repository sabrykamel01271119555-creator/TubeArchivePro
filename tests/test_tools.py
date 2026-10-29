# TubeArchive Pro | 2.0.5 | tests for finding yt-dlp / ffmpeg inside tools/ and its sub-folders
import tempfile
import unittest
from pathlib import Path

from app.resources import find_tool


class FindTool(unittest.TestCase):
    def test_direct_and_subfolder(self):
        with tempfile.TemporaryDirectory() as d:
            d = Path(d)
            self.assertIsNone(find_tool("ffmpeg", d))
            sub = d / "ffmpeg-2026-10-19-git-2344518cc5-full_build" / "bin"
            sub.mkdir(parents=True)
            (sub / "ffmpeg.exe").write_text("x")
            self.assertEqual(find_tool("ffmpeg", d), str(sub / "ffmpeg.exe"))
            (d / "ffmpeg.exe").write_text("x")                       # a file directly in tools/ wins
            self.assertEqual(find_tool("ffmpeg", d), str(d / "ffmpeg.exe"))


if __name__ == "__main__":
    unittest.main()
