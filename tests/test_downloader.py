"""Run:  python -m unittest discover -s tests -v   (no Qt, no internet, no yt-dlp needed)"""
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import importlib.util

spec = importlib.util.spec_from_file_location("downloader", Path(__file__).resolve().parent.parent / "app" / "downloader.py")
dl = importlib.util.module_from_spec(spec)
spec.loader.exec_module(dl)

FAKE = [sys.executable, str(Path(__file__).resolve().parent / "fake_ytdlp.py")]


def run_job(url="https://x.com/watch?v=1", fmt="MP4", quality=1080, wait=True, steps=5, **kw):
    out = tempfile.mkdtemp()
    os.environ["FAKE_STEPS"] = str(steps)
    ev = {"progress": [], "log": [], "done": None, "fail": None, "cancel": False}
    job = dl.DownloadJob(FAKE, url, out, fmt, quality,
                         on_progress=ev["progress"].append,
                         on_log=lambda l, k, p: ev["log"].append((l, k, p)),
                         on_finished=lambda r: ev.__setitem__("done", r),
                         on_failed=lambda c, d: ev.__setitem__("fail", (c, d)),
                         on_cancelled=lambda: ev.__setitem__("cancel", True), **kw)
    job.start()
    if wait:
        end = time.time() + 20
        while not (ev["done"] or ev["fail"]) and time.time() < end:
            time.sleep(0.05)
    return job, ev, Path(out)


class Pure(unittest.TestCase):
    def test_progress_line(self):
        p = dl.parse_progress_line("TAPROG|downloading|500|1000|NA|2048.5|3|2|10")
        self.assertEqual((p["downloaded"], p["total"], p["total_est"], p["speed"], p["index"], p["count"]),
                         (500, 1000, None, 2048.5, 2, 10))
        self.assertIsNone(dl.parse_progress_line("[download] 10% of 5MiB"))

    def test_quality_options(self):
        self.assertEqual(dl.quality_options("MP4"), [0, 144, 240, 360, 480, 720, 1080, 1440, 2160, 4320])
        self.assertEqual(dl.quality_options("MKV", 1080), [0, 144, 240, 360, 480, 720, 1080])
        self.assertEqual(dl.quality_options("MP3"), [320, 256, 192, 128, 96, 64])
        self.assertEqual(dl.quality_options("WAV"), [48000, 44100, 22050])
        self.assertEqual(dl.quality_label("MP4", 2160), "4K")
        self.assertEqual(dl.quality_label("WAV", 44100), "44.1 kHz")
        self.assertIsNone(dl.quality_label("MP4", 0))

    def test_format_args(self):
        self.assertIn("--audio-quality", dl.build_format_args("MP3", 320))
        self.assertIn("320K", dl.build_format_args("MP3", 320))
        self.assertIn("ExtractAudio:-ar 44100", dl.build_format_args("WAV", 44100))
        self.assertIn("avi", dl.build_format_args("AVI", 720))
        self.assertIn("bv*[height<=720][ext=mp4]+ba[ext=m4a]/bv*[height<=720]+ba/b[height<=720]/b",
                      dl.build_format_args("MP4", 720))

    def test_estimate(self):
        info = {"duration": 100, "formats": [
            {"vcodec": "avc1", "acodec": "none", "height": 1080, "filesize": 80_000_000, "ext": "mp4"},
            {"vcodec": "avc1", "acodec": "none", "height": 2160, "filesize": 400_000_000, "ext": "mp4"},
            {"vcodec": "none", "acodec": "mp4a", "abr": 128, "filesize": 2_000_000, "ext": "m4a"}]}
        self.assertEqual(dl.estimate_size(info, "MP4", 1080), 82_000_000)
        self.assertEqual(dl.estimate_size(info, "MP4", 0), 402_000_000)
        self.assertEqual(dl.estimate_size(info, "MP3", 320), 4_000_000)
        self.assertEqual(dl.estimate_size(info, "WAV", 44100), 100 * 44100 * 4)
        self.assertIsNone(dl.estimate_size(info, "MP4", 144))

    def test_errors(self):
        self.assertEqual(dl.map_error("ERROR: [youtube] x: Video unavailable")[0], "unavailable")
        self.assertEqual(dl.map_error("ERROR: Private video. Sign in")[0], "private")
        self.assertEqual(dl.map_error("ERROR: unable to download video data: getaddrinfo failed")[0], "network")
        self.assertEqual(dl.map_error("ERROR: Requested format is not available")[0], "format")
        self.assertEqual(dl.map_error("ERROR: [Errno 13] Permission denied")[0], "disk")
        code, detail = dl.map_error("ERROR: something strange")
        self.assertEqual((code, detail), ("unknown", "something strange"))

    def test_urls(self):
        self.assertTrue(dl.looks_like_url("https://youtu.be/abc"))
        self.assertFalse(dl.looks_like_url("hello world"))
        self.assertTrue(dl.is_playlist_url("https://www.youtube.com/playlist?list=PL123"))
        self.assertFalse(dl.is_playlist_url("https://www.youtube.com/watch?v=1&list=PL123"))


class Engine(unittest.TestCase):
    def test_info(self):
        info = dl.fetch_info(FAKE, "https://x.com/watch?v=1")
        self.assertEqual((info["title"], info["max_height"], info["is_playlist"]), ("Summer Vlog", 2160, False))
        with self.assertRaises(dl.EngineError) as c:
            dl.fetch_info(FAKE, "https://x.com/bad")
        self.assertEqual(c.exception.code, "unavailable")
        with self.assertRaises(dl.EngineError) as c:
            dl.fetch_info("/no/such/exe", "https://x.com/a")
        self.assertEqual(c.exception.code, "no_ytdlp")

    def test_success(self):
        job, ev, out = run_job(est_total=3000)
        self.assertIsNotNone(ev["done"], ev)
        r = ev["done"]
        self.assertEqual((r["name"], r["size"], r["count"]), ("Video 1.mp4", 3000, 1))
        self.assertTrue((out / "Video 1.mp4").exists())
        self.assertEqual([p.name for p in out.iterdir()], ["Video 1.mp4"])      # tmp folder removed
        self.assertEqual(r["description"], "About Video 1\nSecond line")          # description of the video is kept
        pct = [p["percent"] for p in ev["progress"]]
        self.assertEqual(pct, sorted(pct))
        self.assertLessEqual(max(pct), 99.0)
        self.assertTrue(any(k == "processing" for _l, k, _p in ev["log"]))

    def test_one_video_with_numbered_template_in_its_folder(self):
        tpl = dl.tpl_escape(dl.safe_name("My: List")) + "/" + dl.index_text(3, 12) + " - %(title)s.%(ext)s"
        job, ev, out = run_job(url="https://x.com/watch?v=q7", out_template=tpl)
        self.assertIsNotNone(ev["done"], ev)
        self.assertEqual(ev["done"]["name"], "003 - Video q7.mp4")
        self.assertTrue((out / "My_ List" / "003 - Video q7.mp4").exists())

    def test_playlist_info_and_folder_options(self):
        info = dl.fetch_info(FAKE, "https://x.com/playlist?list=PLX")
        self.assertEqual((info["is_playlist"], info["playlist_id"], info["count"]), (True, "PLX", 5))
        self.assertEqual([(e["id"], e["index"]) for e in info["entries"]],       # private video is left out
                         [("v1", 1), ("v2", 2), ("v3", 3), ("v4", 4), ("v5", 5)])
        self.assertEqual(dl.playlist_id("https://www.youtube.com/playlist?list=PL123&x=1"), "PL123")
        self.assertEqual(dl.playlist_id("https://www.youtube.com/watch?v=abc"), "")

    def test_playlist_with_and_without_folder(self):
        url = "https://x.com/playlist?list=PLX"
        job, ev, out = run_job(url=url, playlist_folder=True)
        self.assertEqual(ev["done"]["count"], 5, ev)
        self.assertEqual(sorted(p.name for p in (out / "My List").iterdir()),
                         ["Five.mp4", "Four.mp4", "One.mp4", "Three.mp4", "Two.mp4"])
        self.assertEqual([i for i, _p in ev["done"]["items"]], ["v1", "v2", "v3", "v4", "v5"])   # ids are known
        job, ev, out = run_job(url=url, playlist_folder=False)                  # no folder: files in the save folder
        self.assertEqual(sorted(p.name for p in out.iterdir())[0], "Five.mp4")
        self.assertFalse((out / "My List").exists())

    def test_playlist_selected_items_only(self):
        job, ev, out = run_job(url="https://x.com/playlist?list=PLX", playlist_folder=False, playlist_items=[2, 4])
        r = ev["done"]
        self.assertEqual(sorted(i for i, _p in r["items"]), ["v2", "v4"])
        self.assertEqual(sorted(p.name for p in out.iterdir()), ["Four.mp4", "Two.mp4"])
        self.assertEqual(max(p["items"] for p in ev["progress"]), 2)             # 2 videos, not 5
        self.assertEqual(sorted({p["item"] for p in ev["progress"]}), [1, 2])

    def test_error(self):
        job, ev, out = run_job(url="https://x.com/fail")
        self.assertEqual(ev["fail"][0], "rate")
        self.assertEqual(list(out.iterdir()), [])

    def test_pause_resume(self):
        job, ev, out = run_job(wait=False, steps=20)
        time.sleep(0.6)
        self.assertTrue(job.pause())
        time.sleep(0.3)
        n = len(ev["progress"])
        time.sleep(1.0)
        self.assertEqual(len(ev["progress"]), n, "progress must stop while paused")
        self.assertTrue(job.alive(), "pause must NOT terminate the process")
        self.assertTrue(job.resume())
        end = time.time() + 20
        while not ev["done"] and time.time() < end:
            time.sleep(0.1)
        self.assertIsNotNone(ev["done"])

    def test_cancel_deletes_partials(self):
        job, ev, out = run_job(wait=False, steps=30)
        time.sleep(0.7)
        tmp = job.tmp_dir
        self.assertTrue(tmp.exists() and any(tmp.iterdir()), "partial file should exist while downloading")
        job.cancel()
        self.assertTrue(ev["cancel"])
        self.assertFalse(tmp.exists())
        self.assertEqual(list(out.iterdir()), [], "nothing may be left in the save folder")
        self.assertFalse(job.alive())

    def test_cancel_while_paused(self):
        job, ev, out = run_job(wait=False, steps=30)
        time.sleep(0.5)
        job.pause()
        job.cancel()
        self.assertEqual(list(out.iterdir()), [])
        self.assertFalse(job.alive())


if __name__ == "__main__":
    unittest.main()


class ParseQuality(unittest.TestCase):
    def test_old_settings_values(self):
        from app.downloader import parse_quality as pq
        self.assertEqual([pq(x) for x in (0, 720, "720", "1080p", "4K", "Best", "", None, "192 kbps", True, "x")],
                         [0, 720, 720, 1080, 2160, 0, 0, 0, 192, 0, 0])


class Numbering(unittest.TestCase):
    def test_index_text(self):
        self.assertEqual(dl.index_text(1, 5), "01")
        self.assertEqual(dl.index_text(9, 9), "09")
        self.assertEqual(dl.index_text(1, 10), "001")
        self.assertEqual(dl.index_text(12, 99), "012")
        self.assertEqual(dl.index_text(7, 100), "0007")
        self.assertEqual(dl.index_text(15, 1200), "00015")

    def test_names(self):
        self.assertEqual(dl.safe_name('A/B:C*"D"?'), "A_B_C__D__")
        self.assertEqual(dl.safe_name("  ..  "), "Playlist")
        self.assertEqual(dl.tpl_escape("100% pure"), "100%% pure")
        self.assertEqual(dl.video_url({"id": "x1"}), "https://www.youtube.com/watch?v=x1")
        self.assertEqual(dl.video_url({"id": "x1", "url": "https://v/1"}), "https://v/1")


class EngineOptions(unittest.TestCase):
    def test_settings_to_ytdlp_options(self):
        from app.downloader import build_download_cmd, engine_options
        s = {"embed_metadata": True, "ytdlp_fallback": True}
        a = engine_options(s.get, "MP4", rate_kb=1536)
        self.assertEqual(a[:2], ["--limit-rate", "1536K"])
        self.assertNotIn("-N", a)                                                         # concurrency = the queue
        self.assertIn("--embed-metadata", a); self.assertIn("--embed-thumbnail", a); self.assertIn("--retries", a)
        self.assertNotIn("--limit-rate", engine_options(s.get, "MP4"))                    # 0 = no limit
        self.assertNotIn("--embed-thumbnail", engine_options(s.get, "WEBM"))          # webm cannot carry a cover
        off = {"embed_metadata": False, "ytdlp_fallback": False,
               "audio_convert": False, "audio_extract": False, "mp4_h264": False}
        self.assertEqual(engine_options(off.get, "MP4"), [])                             # nothing selected: no extra options
        self.assertEqual(engine_options(off.get, "MP3"), ["--audio-quality", "0", "-k"])
        cmd = build_download_cmd("yt", "https://u", "o", "t", "MP4", 0, False, None, "l", extra_args=["-N", "5"])
        self.assertEqual(cmd[-3:], ["-N", "5", "https://u"])                              # before the link


class RefinedTotalTests(unittest.TestCase):
    """2.0.2: the expected size follows the real size of the streams while the download runs."""

    def _job(self):
        got = []
        info = {"duration": 100, "formats": [{"format_id": "137", "filesize": 900}, {"format_id": "140", "filesize_approx": 100}]}
        job = dl.DownloadJob("yt-dlp", "https://youtu.be/x", ".", "MP4", 0, info=info, est_total=5000,
                             on_progress=got.append)
        return job, got

    def test_real_stream_size_replaces_estimate(self):
        job, got = self._job()
        job._handle("[info] x: Downloading 1 format(s): 137+140")
        self.assertEqual(job._streams, [900.0, 100.0])
        job._progress({"status": "downloading", "downloaded": 100.0, "total": 1200.0, "total_est": None, "speed": 10.0,
                       "eta": 5, "index": None, "count": None})
        self.assertEqual(got[-1]["total"], 1300.0)                      # 1200 real video + 100 announced audio (not 5000)
        job._progress({"status": "finished", "downloaded": 1200.0, "total": 1200.0, "total_est": None, "speed": 10.0,
                       "eta": 0, "index": None, "count": None})
        job._progress({"status": "downloading", "downloaded": 50.0, "total": 110.0, "total_est": None, "speed": 10.0,
                       "eta": 5, "index": None, "count": None})
        self.assertEqual(got[-1]["total"], 1310.0)                      # video 1200 + audio 110 (real)
        self.assertAlmostEqual(got[-1]["percent"], 1250 / 1310 * 100, places=3)

    def test_without_stream_sizes_the_old_logic_is_used(self):
        job, got = self._job()
        job._progress({"status": "downloading", "downloaded": 100.0, "total": 1200.0, "total_est": None, "speed": 10.0,
                       "eta": 5, "index": None, "count": None})
        self.assertEqual(got[-1]["total"], 5000)


class H264Quality(unittest.TestCase):
    """2.3.1: 2K / 4K / 8K in the list, H.264 + AAC MP4."""

    def fm(self, h, v):
        return {"height": h, "vcodec": v, "acodec": "none", "ext": "mp4" if v.startswith("avc") else "webm"}

    def test_heights_and_labels(self):
        from app import downloader as d
        self.assertEqual(d.quality_options("MP4")[-3:], [1440, 2160, 4320])
        self.assertEqual([d.height_label(h) for h in (1080, 1440, 2160, 4320)], ["1080p", "2K", "4K", "8K"])
        self.assertEqual([d.parse_quality(x) for x in ("2K", "4k", "8K", "1440p")], [1440, 2160, 4320, 1440])

    def test_h264_stream_is_taken_as_it_is(self):
        from app import downloader as d
        info = {"formats": [self.fm(720, "avc1.4d401f"), self.fm(1080, "avc1.640028"), self.fm(1080, "vp09.00")]}
        a = d.h264_args(info, 0)
        self.assertIn("[vcodec^=avc1]", a[1])
        self.assertNotIn("--recode-video", a)

    def test_high_resolution_is_converted(self):
        from app import downloader as d
        info = {"formats": [self.fm(1080, "avc1.640028"), self.fm(2160, "vp09.00"), self.fm(4320, "av01.0")]}
        a = d.h264_args(info, 0)                                  # best = 8K (AV1): converted
        self.assertIn("--recode-video", a)
        self.assertIn("libx264", a[-1])
        self.assertIn("height<=4320", a[1])
        b = d.h264_args(info, 1080)                               # limited to 1080p: H.264 exists, no conversion
        self.assertNotIn("--recode-video", b)
        self.assertIn("height<=1080", b[1])

    def test_unknown_info_prefers_h264_and_setting_switch(self):
        from app import downloader as d
        self.assertIn("vcodec^=avc1", d.h264_args(None, 720)[1])
        on = d.engine_options(lambda k, df=None: df, "MP4", 0, None, 0)
        off = d.engine_options(lambda k, df=None: False if k == "mp4_h264" else df, "MP4", 0, None, 0)
        self.assertIn("-f", on)
        self.assertNotIn("-f", off)
        self.assertNotIn("-f", d.engine_options(lambda k, df=None: df, "MKV", 0, None, 0))
