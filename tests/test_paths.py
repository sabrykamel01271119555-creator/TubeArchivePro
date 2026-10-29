"""2.3.0: program folder (read only) and user data folder (%APPDATA%) are separate; migration of an older portable copy."""
import tempfile
import unittest
from pathlib import Path

from app import paths


class UserDir(unittest.TestCase):
    def test_resolve(self):
        app = Path("C:/Program Files/TubeArchive Pro")
        self.assertEqual(paths.resolve_user_dir(False, app), app)                       # python main.py: project folder
        self.assertEqual(paths.resolve_user_dir(True, app, "C:/Users/me/AppData/Roaming"),
                         Path("C:/Users/me/AppData/Roaming") / "TubeArchivePro")        # installed
        self.assertEqual(paths.resolve_user_dir(True, app, "C:/x", portable=True), app)  # portable.txt

    def test_dev_layout_unchanged(self):
        self.assertEqual(paths.CURRENT_SETTINGS_FILE, paths.DATA_DIR / "config" / "current_settings.json")
        self.assertEqual(paths.DEFAULT_SETTINGS_FILE.name, "default_settings.json")
        self.assertTrue(str(paths.LANG_DIR).startswith(str(paths.APP_DIR)))             # shipped files: program folder
        self.assertTrue(str(paths.HISTORY_FILE).startswith(str(paths.USER_DIR)))        # written files: user folder

    def test_migrate_old_data(self):
        with tempfile.TemporaryDirectory() as a, tempfile.TemporaryDirectory() as b:
            a, b = Path(a), Path(b)
            (a / "data" / "config").mkdir(parents=True)
            (a / "data" / "config" / "current_settings.json").write_text('{"language": "ar"}')
            (a / "data" / "history").mkdir()
            (a / "data" / "history" / "history.json").write_text("[]")
            (a / "assets" / "ads").mkdir(parents=True)
            (a / "assets" / "ads" / "x.gif").write_bytes(b"GIF89a")
            (b / "data" / "config").mkdir(parents=True)
            (b / "data" / "config" / "current_settings.json").write_text('{"language": "en"}')   # already there: kept
            done = paths.migrate_old_data(a, b)
            self.assertIn("data/history", done)
            self.assertIn("assets/ads", done)
            self.assertNotIn("data/config/current_settings.json", done)
            self.assertEqual((b / "data" / "config" / "current_settings.json").read_text(), '{"language": "en"}')
            self.assertTrue((b / "data" / "history" / "history.json").exists())
            self.assertEqual(paths.migrate_old_data(a, b), [])                          # second run: nothing
            self.assertEqual(paths.migrate_old_data(a, a), [])                          # same folder: nothing


if __name__ == "__main__":
    unittest.main()
