"""2.2.7: sound effects - files exist, the setting switches them off, unknown names / missing files never raise."""
import unittest
import wave

from app import sounds


class Fake:
    def __init__(self, on):
        self.on = on

    def get(self, key, fb=None):
        return self.on if key == "sounds_enabled" else fb


class Sounds(unittest.TestCase):
    def test_files(self):
        for n in sounds.NAMES:
            with wave.open(str(sounds.SOUND_DIR / f"{n}.wav")) as w:
                self.assertGreater(w.getnframes(), 500)

    def test_switch(self):
        sounds.attach(Fake(False))
        self.assertFalse(sounds.play("click"))
        sounds.attach(Fake(True))
        self.assertFalse(sounds.play("nothing"))
        self.assertTrue(sounds.enabled())
        sounds.attach(None)


if __name__ == "__main__":
    unittest.main()
