"""2.3.0: encryption of the online text files."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app import secure                                              # noqa: E402


class Secure(unittest.TestCase):
    def test_round_trip(self):
        for data in (b"", b"1 gif https://x/y.gif\n2 gif https://x/z.gif", "عربي ✓".encode("utf-8"), bytes(range(256)) * 50):
            blob = secure.encrypt(data)
            self.assertTrue(secure.is_encrypted(blob))
            self.assertNotIn(b"https", blob)
            self.assertEqual(secure.decrypt(blob), data)
            self.assertEqual(secure.decrypt_if_needed(blob), data)

    def test_plain_and_damaged(self):
        self.assertEqual(secure.decrypt_if_needed(b"1.0.0 = 25"), b"1.0.0 = 25")      # plain files still work
        blob = bytearray(secure.encrypt(b"secret list"))
        blob[25] ^= 1
        self.assertIsNone(secure.decrypt_if_needed(bytes(blob)))
        with self.assertRaises(ValueError):
            secure.decrypt(b"TAE1short")

    def test_different_nonce_each_time(self):
        self.assertNotEqual(secure.encrypt(b"same"), secure.encrypt(b"same"))

    def test_read_text_file_decrypts(self):
        import http.server, threading
        from app import ads
        blob = secure.encrypt("1 https://a/b.gif https://c\n".encode())

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a): pass
            def do_GET(self):
                self.send_response(200); self.send_header("Content-Length", str(len(blob))); self.end_headers(); self.wfile.write(blob)
        srv = http.server.ThreadingHTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=srv.serve_forever, daemon=True).start()
        try:
            url = f"http://127.0.0.1:{srv.server_address[1]}/list.txt"
            text = ads.read_text_file("x", "list.txt", [{"name": "list.txt", "text": "list.txt", "url": url}])
            self.assertEqual(text, "1 https://a/b.gif https://c\n")
        finally:
            srv.shutdown(); srv.server_close()


if __name__ == "__main__":
    unittest.main()
