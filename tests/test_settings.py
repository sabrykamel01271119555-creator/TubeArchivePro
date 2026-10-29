import json, tempfile, unittest
from pathlib import Path
import app.settings as sm


class Settings(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        d = Path(self.tmp.name)
        self.keep = (sm.CONFIG_DIR, sm.CURRENT_SETTINGS_FILE, sm.DEFAULT_SETTINGS_FILE)
        sm.CONFIG_DIR, sm.CURRENT_SETTINGS_FILE, sm.DEFAULT_SETTINGS_FILE = d, d / "current_settings.json", d / "default_settings.json"
        sm.DEFAULT_SETTINGS_FILE.write_text(json.dumps({"language": "en", "download_dir": "~/V", "default_quality": 0,
                                                        "show_success_dialog": True, "demo_seed_version": 0}))

    def tearDown(self):
        sm.CONFIG_DIR, sm.CURRENT_SETTINGS_FILE, sm.DEFAULT_SETTINGS_FILE = self.keep
        self.tmp.cleanup()

    def test_two_files_and_restore_defaults(self):
        s = sm.SettingsManager(); s.load_defaults(); s.load_current()
        self.assertTrue(sm.CURRENT_SETTINGS_FILE.exists())                      # user file is created from the defaults
        s.set("language", "ar"); s.set("default_quality", 720); s.set("show_success_dialog", False); s.set("demo_seed_version", 2)
        s.save()
        s2 = sm.SettingsManager(); s2.load_defaults(); s2.load_current()
        self.assertEqual((s2.get("language"), s2.get("default_quality"), s2.get("show_success_dialog")), ("ar", 720, False))
        s2.reset_to_defaults()                                                   # Restore Defaults
        self.assertEqual((s2.get("language"), s2.get("default_quality"), s2.get("show_success_dialog")), ("en", 0, True))
        self.assertEqual(s2.get("demo_seed_version"), 2)                         # not a preference: kept
        saved = json.loads(sm.CURRENT_SETTINGS_FILE.read_text())
        self.assertEqual(saved["language"], "en")                                # written to current_settings.json
        self.assertEqual(json.loads(sm.DEFAULT_SETTINGS_FILE.read_text())["language"], "en")   # defaults untouched

    def test_old_settings_get_the_new_concurrency_default_once(self):
        sm.DEFAULT_SETTINGS_FILE.write_text(json.dumps({"language": "en", "download_dir": "~/V", "max_concurrent": 3}))
        sm.CURRENT_SETTINGS_FILE.write_text(json.dumps({"language": "ar", "max_concurrent": 4}))       # saved by 1.0.14
        s = sm.SettingsManager(); s.load_defaults(); s.load_current()
        self.assertEqual((s.get("max_concurrent"), s.get("language")), (3, "ar"))
        s.set("max_concurrent", 6); s.save()                                      # the user's own choice is kept afterwards
        s2 = sm.SettingsManager(); s2.load_defaults(); s2.load_current()
        self.assertEqual(s2.get("max_concurrent"), 6)


if __name__ == "__main__":
    unittest.main()
