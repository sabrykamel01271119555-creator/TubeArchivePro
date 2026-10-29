"""Info pages (help / about us / contact us / donate) and reviews.txt:  python -m unittest tests.test_infodoc -v"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import infodoc as d                                    # noqa: E402


class Render(unittest.TestCase):
    def test_blocks(self):
        b = d.parse_blocks("# Title\n\nHello **world**\nsecond line\n\n## Part\n- a\n- b\n1. one\n2. two\n> note\n---\nEmail :: x@y.com\nPhone :: 1")
        kinds = [k for k, _ in b]
        self.assertEqual(kinds, ["title", "p", "h2", "ul", "ol", "note", "rule", "rows"])
        self.assertEqual(b[1][1], "Hello **world** second line")
        self.assertEqual(b[3][1], ["a", "b"])
        self.assertEqual(b[7][1], [("Email", "x@y.com"), ("Phone", "1")])

    def test_inline_links_and_escaping(self):
        h = d.inline("see https://a.com/x?y=1, mail me@a.com [site](https://b.org) <b> & **bold**")
        self.assertIn('href="https://a.com/x?y=1"', h)
        self.assertIn('href="mailto:me@a.com"', h)
        self.assertIn('href="https://b.org"', h)
        self.assertIn("&lt;b&gt; &amp; <b>bold</b>", h)
        self.assertNotIn("mailto:kamel@instapay", d.inline("sabry kamel@instapay"))      # not an e-mail address

    def test_rtl_page(self):
        self.assertIn('dir="rtl"', d.render_text("# x", "rtl"))


class LocalFiles(unittest.TestCase):
    def test_every_page_exists_in_both_languages(self):
        for kind in ("help", "about", "contact", "donate"):
            for lang in ("en", "ar"):
                p = d.info_path(kind, lang)
                self.assertIsNotNone(p, (kind, lang))
                self.assertTrue(p.name.endswith(f".{lang}.txt"))
                self.assertGreater(len(d.load_info(kind, lang)), 40)

    def test_content_the_owner_asked_for(self):
        en = {k: d.load_info(k, "en") for k in ("help", "about", "contact", "donate")}
        self.assertIn("sabry.kamel2024@gmail.com", en["contact"])
        self.assertNotIn("00201271119555", en["contact"])                 # the number is not written, only a WhatsApp link
        self.assertIn("wa.me/201271119555", en["contact"])
        self.assertIn("https://www.facebook.com/sabry.kamel.12", en["contact"])
        self.assertIn("sabry kamel@instapay", en["donate"])
        self.assertIn("01063292594", en["donate"])
        self.assertIn("Sabry Kamel", en["about"])
        self.assertIn("2026", en["about"])
        self.assertIn("Let's Have Fun", en["about"])
        self.assertIn("2.3", en["help"])
        html = d.render_text(en["contact"])
        self.assertIn("mailto:sabry.kamel2024@gmail.com", html)

    def test_language_fallback(self):
        tmp = Path(tempfile.mkdtemp())
        (tmp / "help.en.txt").write_text("# English", encoding="utf-8")
        self.assertEqual(d.load_info("help", "fr", tmp), "# English")          # unknown language -> English
        (tmp / "help.fr.txt").write_text("# Francais", encoding="utf-8")
        self.assertEqual(d.load_info("help", "fr", tmp), "# Francais")
        self.assertEqual(d.load_info("donate", "en", tmp), "")                    # missing file -> empty


class Reviews(unittest.TestCase):
    def test_lines_with_bars(self):
        r = d.parse_reviews("Ali | 5 | Great program | 2026-10-01\nSara | 4 | Good\n# comment\nOmar | ★★★ | OK")
        self.assertEqual([(x["name"], x["rating"], x["comment"]) for x in r],
                         [("Ali", 5.0, "Great program"), ("Sara", 4.0, "Good"), ("Omar", 3.0, "OK")])
        self.assertEqual(r[0]["date"], "2026-10-01")

    def test_sheet_export_with_header_and_columns_in_any_order(self):
        r = d.parse_reviews("Name\tRating\tComment\nMona\t5\tLovely\n2026-10-02\tKarim\t4\tVery useful")
        self.assertEqual([x["name"] for x in r], ["Mona", "Karim"])
        self.assertEqual(r[1]["rating"], 4.0)
        self.assertEqual(r[1]["date"], "2026-10-02")

    def test_csv_and_blocks(self):
        r = d.parse_reviews('Huda,5,"Nice, simple and fast"')
        self.assertEqual((r[0]["name"], r[0]["rating"], r[0]["comment"]), ("Huda", 5.0, "Nice, simple and fast"))
        r = d.parse_reviews("Name: Lina\nRating: 4/5\nComment: Works well\n\nName: Sam\nStars: 5\nReview: Best tool")
        self.assertEqual([(x["name"], x["rating"], x["comment"]) for x in r],
                         [("Lina", 4.0, "Works well"), ("Sam", 5.0, "Best tool")])

    def test_html(self):
        r = d.parse_reviews("Ali | 5 | <b>x</b> great\nSara | 3 | fine")
        h = d.render_reviews(r, "Reviews", "{n} reviews", "none")
        self.assertIn("4.0", h)                                    # average
        self.assertIn("2 reviews", h)
        self.assertIn("&lt;b&gt;x&lt;/b&gt; great", h)             # nothing from the file is trusted as HTML
        self.assertIn("none", d.render_reviews([], "Reviews", "{n}", "none"))
        self.assertEqual(d.parse_reviews(""), [])


class DescriptionLinks(unittest.TestCase):
    def test_links_and_escape(self):
        from app.infodoc import description_html
        h = description_html("a <b> x\nSee https://youtu.be/abc?x=1&y=2, www.site.com/a or me@x.com")
        self.assertIn("&lt;b&gt;", h)
        self.assertIn("<br>", h)
        self.assertIn('href="https://youtu.be/abc?x=1&amp;y=2"', h)
        self.assertIn('href="https://www.site.com/a"', h)
        self.assertIn('href="mailto:me@x.com"', h)
        self.assertNotIn("<b>", h)


class AboutMerged(unittest.TestCase):
    def test_about_contains_contact_and_donate_without_frames(self):
        from app import infodoc
        for lang in ("en", "ar"):
            text = infodoc.load_about(lang)
            self.assertIn("sabry.kamel2024@gmail.com", text)
            self.assertIn("01063292594", text)
            self.assertEqual(text.count("sabry.kamel2024@gmail.com"), 1)               # not twice
            html = infodoc.render_text(text, "ltr")
            self.assertNotIn("border:1px solid " + infodoc.C_CARD_EDGE, html.split("01063292594")[0].rsplit("<table", 1)[-1])
        self.assertTrue(infodoc.load_about("en").startswith("# About"))


if __name__ == "__main__":
    unittest.main()
