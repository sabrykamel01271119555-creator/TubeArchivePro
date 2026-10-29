"""Download queue with the fake yt-dlp (no Qt, no internet):  python -m unittest tests.test_queue -v"""
import json
import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.dlqueue import DownloadQueue                       # noqa: E402

FAKE = [sys.executable, str(Path(__file__).resolve().parent / "fake_ytdlp.py")]


def wait(cond, timeout=30):
    end = time.time() + timeout
    while not cond() and time.time() < end:
        time.sleep(0.03)
    return cond()


class Rig:
    def __init__(self, steps=4, **settings):
        os.environ["FAKE_STEPS"] = str(steps)
        self.out = Path(tempfile.mkdtemp())
        self.argfile = self.out / "args.log"
        os.environ["FAKE_ARGLOG"] = str(self.argfile)
        self.settings = {"max_concurrent": 3, "speed_limit_mb": 0, "embed_metadata": False, "ytdlp_fallback": False}
        self.settings.update(settings)
        self.events, self.max_active = [], 0
        self.q = DownloadQueue(FAKE, None, lambda k, d=None: self.settings.get(k, d), self.on_event)

    def on_event(self, kind, obj):
        self.events.append((kind, obj))
        if kind == "task":
            self.max_active = max(self.max_active, self.q.counts()[0])

    def args(self):
        if not self.argfile.exists():
            return []
        return [json.loads(l) for l in self.argfile.read_text().splitlines() if l.strip()]

    def idle(self):
        return not self.q.busy()


def entries(n, first=1):
    return [{"id": f"v{i}", "index": i, "title": f"T{i}", "url": f"https://www.youtube.com/watch?v=v{i}"}
            for i in range(first, first + n)]


class QueueTests(unittest.TestCase):
    def test_new_video_has_priority_over_paused_ones(self):
        """2.2.3: paused videos hold no place: after 'pause all' a video that is added starts at once; 'resume' of a paused video
        waits while every place is taken and happens by itself when a place is free."""
        r = Rig(steps=40, max_concurrent=2)
        a = r.q.add_video("https://x.com/watch?v=a", r.out, "MP4", 0, title="A")
        b = r.q.add_video("https://x.com/watch?v=b", r.out, "MP4", 0, title="B")
        self.assertTrue(wait(lambda: a.state == "downloading" and b.state == "downloading"))
        self.assertEqual(r.q.pause_all(), 2)
        self.assertEqual(r.q.counts_by_state(), {"downloading": 0, "paused": 2, "waiting": 0})
        c = r.q.add_video("https://x.com/watch?v=c", r.out, "MP4", 0, title="C")
        d = r.q.add_video("https://x.com/watch?v=d", r.out, "MP4", 0, title="D")
        self.assertTrue(wait(lambda: c.state in ("downloading", "processing") and d.state in ("downloading", "processing")))
        self.assertEqual((a.state, b.state), ("paused", "paused"))
        self.assertTrue(r.q.resume_task(a))                                  # no free place: stays paused, wanted
        self.assertEqual(a.state, "paused")
        self.assertTrue(a._resume_wanted)
        e = r.q.add_video("https://x.com/watch?v=e", r.out, "MP4", 0, title="E")   # waits: no place
        self.assertEqual(e.state, "queued")
        r.q.cancel_task(c)                                                   # a place is free now -> a resumes by itself
        self.assertTrue(wait(lambda: a.state in ("downloading", "processing")))
        self.assertFalse(a._resume_wanted)
        self.assertEqual(e.state, "queued")                                  # the waiting video did not take the place
        r.q.cancel_all()
        self.assertTrue(wait(r.idle))

    def test_discard_removes_from_the_list(self):
        """2.2.5: Cancel in the Downloads list = stop + remove: single videos, a playlist, and 'cancel all'."""
        r = Rig(steps=40, max_concurrent=2)
        a = r.q.add_video("https://x.com/watch?v=a", r.out, "MP4", 0, title="A")
        b = r.q.add_video("https://x.com/watch?v=b", r.out, "MP4", 0, title="B")
        g = r.q.add_playlist("PL", entries(3), r.out, "MP4", 0)
        self.assertTrue(wait(lambda: a.state == "downloading"))
        r.q.discard_task(b)                                                   # b may still wait or already run
        self.assertTrue(wait(lambda: b.finished))
        self.assertEqual(r.q.purge_discarded(), 1)
        self.assertNotIn(b, r.q.tasks)
        self.assertIn(a, r.q.tasks)                                           # a is untouched
        r.q.discard_group(g)
        self.assertTrue(wait(lambda: g.state == "done"))
        self.assertEqual(r.q.purge_discarded(), 1)
        self.assertEqual(r.q.groups, [])
        self.assertEqual([t.id for t in r.q.tasks], [a.id])
        r.q.discard_all()
        self.assertTrue(wait(lambda: a.finished))
        self.assertEqual(r.q.purge_discarded(), 1)
        self.assertEqual((r.q.tasks, r.q.groups), ([], []))
        self.assertTrue(wait(r.idle))

    def test_counters_count_files_not_playlists(self):
        """2.2.2: the counters (New Download, side menu) = files: a playlist of 6 videos + 1 single video = 7, never 2."""
        r = Rig(steps=4, max_concurrent=2)
        r.q.add_playlist("PL", entries(6), r.out, "MP4", 0)
        r.q.add_video("https://x.com/watch?v=single", r.out, "MP4", 0, title="S")
        running, waiting = r.q.counts()
        self.assertEqual(running + waiting, 7)
        self.assertEqual((running, waiting), (2, 5))
        self.assertTrue(wait(r.idle))
        self.assertEqual(r.q.counts(), (0, 0))

    def test_default_is_three_and_limit_is_respected(self):
        r = Rig(steps=4, max_concurrent=2)
        for i in range(5):
            r.q.add_video(f"https://x.com/watch?v=s{i}", r.out, "MP4", 0, title=f"S{i}")
        running, waiting = r.q.counts()
        self.assertEqual((running, waiting), (2, 3))                       # only 2 processes, 3 wait
        self.assertTrue(wait(r.idle))
        self.assertEqual(r.max_active, 2)
        self.assertEqual(sorted(t.state for t in r.q.tasks), ["done"] * 5)
        self.assertEqual(r.q.finished_bytes, 5 * 3000)
        self.assertEqual(r.q.max_concurrent(), 2)
        self.assertEqual(DownloadQueue(FAKE, None, lambda k, d=None: d).max_concurrent(), 3)   # factory default

    def test_a_waiting_video_starts_when_a_place_is_free(self):
        r = Rig(steps=3, max_concurrent=1)
        a = r.q.add_video("https://x.com/watch?v=a1", r.out, "MP4", 0)
        b = r.q.add_video("https://x.com/watch?v=b1", r.out, "MP4", 0)
        self.assertEqual((a.state, b.state), ("downloading", "queued"))
        self.assertTrue(wait(lambda: a.state == "done"))
        self.assertTrue(wait(lambda: b.state in ("downloading", "processing", "done")))
        self.assertTrue(wait(r.idle))

    def test_playlist_numbering_folder_and_group_result(self):
        r = Rig(steps=3)
        g = r.q.add_playlist("My: List", entries(5), r.out, "MP4", 0, count=12, url="https://x.com/playlist?list=P")
        self.assertTrue(wait(lambda: g.state == "done"))
        names = sorted(p.name for p in (r.out / "My_ List").iterdir())
        self.assertEqual(names, [f"00{i} - Video v{i}.mp4" for i in range(1, 6)])         # 12 videos -> 001 ...
        self.assertEqual((g.result["count"], g.result["failed"], g.result["skipped"]), (5, 0, 0))
        self.assertEqual([v for v, _p in g.result["items"]].sort(), None)
        self.assertEqual(g.result["descriptions"]["v2"], "About Video v2\nSecond line")
        self.assertEqual(len([e for e in r.events if e[0] == "group_done"]), 1)

    def test_small_playlist_uses_two_digits_and_no_folder_for_sync(self):
        r = Rig(steps=2)
        g = r.q.add_playlist("L", entries(2, first=7), r.out, "MP4", 0, subfolder=False, count=30)
        self.assertTrue(wait(lambda: g.state == "done"))
        self.assertEqual(sorted(p.name for p in r.out.iterdir() if p.suffix == ".mp4"),
                         ["007 - Video v7.mp4", "008 - Video v8.mp4"])                      # position 7 of 30

    def test_one_playlist_runs_several_videos_together(self):
        r = Rig(steps=5, max_concurrent=3, playlist_concurrent=3)      # the user raised the playlist setting
        g = r.q.add_playlist("PL", entries(6), r.out, "MP4", 0)
        self.assertEqual(r.q.counts(), (3, 3))
        self.assertTrue(wait(lambda: g.state == "done"))
        self.assertEqual(r.max_active, 3)

    def test_playlist_default_is_one_video_at_a_time(self):
        r = Rig(steps=3, max_concurrent=3)                              # no playlist_concurrent -> default 1
        g = r.q.add_playlist("PL", entries(4), r.out, "MP4", 0)
        self.assertEqual(r.q.counts(), (1, 3))
        self.assertTrue(wait(lambda: g.state == "done"))
        self.assertEqual(r.max_active, 1)
        r = Rig(steps=3, max_concurrent=2, playlist_concurrent=5)       # never above max_concurrent
        self.assertEqual(r.q.playlist_limit(), 2)
        r.q.cancel_all(wait=True)
        r = Rig(steps=6, max_concurrent=3)                              # a second playlist uses the free places
        a = r.q.add_playlist("A", entries(2), r.out, "MP4", 0)
        b = r.q.add_playlist("B", entries(2, first=1), r.out, "MP4", 0)
        self.assertEqual(r.q.counts()[0], 2)                            # one video of each playlist
        r.q.cancel_all(wait=True)

    def test_one_by_one_and_skip(self):
        r = Rig(steps=6, max_concurrent=3)
        g = r.q.add_playlist("PL", entries(4), r.out, "MP4", 0)
        r2 = Rig(steps=6, max_concurrent=3, playlist_concurrent=3)
        g = r2.q.add_playlist("PL", entries(4), r2.out, "MP4", 0)
        t1, t2, t3, t4 = g.tasks
        self.assertEqual(r2.q.counts(), (3, 1))
        r2.q.skip(t4)                                                           # waiting video is dropped at once
        self.assertEqual(t4.state, "skipped")
        r2.q.skip(t2)                                                           # a running video is stopped
        self.assertTrue(wait(lambda: t2.state == "skipped"))
        self.assertTrue(wait(lambda: g.state == "done"))
        self.assertEqual((t1.state, t3.state), ("done", "done"))
        self.assertEqual((g.result["count"], g.result["skipped"]), (2, 2))
        self.assertFalse(any(p.name.startswith(".tubearchive_tmp") for p in r2.out.iterdir()))   # partial files removed

    def test_sequential_group_runs_one_at_a_time(self):
        from app.dlqueue import Group, Task
        r = Rig(steps=3, max_concurrent=3)
        g = Group(99, "Seq", count=3, folder=r.out)
        g.sequential = True
        for n, e in enumerate(entries(3), 1):
            t = Task(n, e["url"], e["title"], "MP4", 0, r.out, group=g, index=e["index"], vid=e["id"])
            g.tasks.append(t)
            r.q.tasks.append(t)
        r.q.groups.append(g)
        r.q.pump()
        self.assertEqual(r.q.counts(), (1, 2))
        self.assertTrue(wait(lambda: g.state == "done"))
        self.assertEqual(r.max_active, 1)

    def test_bandwidth_is_divided_between_the_places(self):
        r = Rig(steps=3, max_concurrent=3, speed_limit_mb=6)
        for i in range(6):
            r.q.add_video(f"https://x.com/watch?v=b{i}", r.out, "MP4", 0)
        self.assertTrue(wait(r.idle))
        rates = [a[a.index("--limit-rate") + 1] for a in r.args()]
        self.assertEqual(rates, ["2048K"] * 6)                                  # 6 MB/s / 3 places, however they start
        r = Rig(steps=3, max_concurrent=1, speed_limit_mb=6)
        r.q.add_video("https://x.com/watch?v=one", r.out, "MP4", 0)
        self.assertTrue(wait(r.idle))
        self.assertEqual([a[a.index("--limit-rate") + 1] for a in r.args()], ["6144K"])   # one place: everything
        r = Rig(steps=3, speed_limit_mb=0)
        r.q.add_video("https://x.com/watch?v=none", r.out, "MP4", 0)
        self.assertTrue(wait(r.idle))
        self.assertNotIn("--limit-rate", r.args()[0])                           # 0 = no control of bandwidth

    def test_failed_video_does_not_stop_the_others(self):
        r = Rig(steps=3)
        bad = r.q.add_video("https://x.com/fail", r.out, "MP4", 0)
        ok = r.q.add_video("https://x.com/watch?v=fine", r.out, "MP4", 0)
        self.assertTrue(wait(r.idle))
        self.assertEqual((bad.state, bad.error[0], ok.state), ("failed", "rate", "done"))

    def test_cancel_all_deletes_partial_files(self):
        r = Rig(steps=40, max_concurrent=2)
        for i in range(4):
            r.q.add_video(f"https://x.com/watch?v=c{i}", r.out, "MP4", 0)
        time.sleep(0.6)
        r.q.cancel_all(wait=True)
        self.assertTrue(wait(r.idle, 10))
        self.assertEqual({t.state for t in r.q.tasks}, {"cancelled"})
        self.assertEqual(list(r.out.glob(".tubearchive_tmp*")), [])
        self.assertEqual(list(r.out.glob("*.mp4")), [])

    def test_pause_resume_and_numbers(self):
        r = Rig(steps=8, max_concurrent=2)
        a = r.q.add_video("https://x.com/watch?v=p1", r.out, "MP4", 0, est_total=3000)
        time.sleep(0.5)
        self.assertTrue(r.q.pause_task(a))
        self.assertEqual(a.state, "paused")
        self.assertEqual(r.q.counts(), (1, 0))                                  # a paused video keeps its place
        self.assertTrue(r.q.resume_task(a))
        self.assertTrue(wait(r.idle))
        self.assertEqual(a.state, "done")
        self.assertEqual(r.q.downloaded_bytes(), 3000)
        self.assertEqual(r.q.clear_finished(), 1)
        self.assertEqual(r.q.tasks, [])

    def test_settings_change_applies_to_the_next_start(self):
        r = Rig(steps=3, max_concurrent=1)
        for i in range(3):
            r.q.add_video(f"https://x.com/watch?v=m{i}", r.out, "MP4", 0)
        self.assertEqual(r.q.counts(), (1, 2))
        r.settings["max_concurrent"] = 3                                         # the user raised the number
        r.q.pump()
        self.assertEqual(r.q.counts()[0], 3)
        self.assertTrue(wait(r.idle))


if __name__ == "__main__":
    unittest.main()
