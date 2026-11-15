import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from publish_verified import select_verified

SRC = """#EXTM3U
#EXTINF:-1,Alpha
https://example.com/a.m3u8
#EXTINF:-1,Bravo
https://example.com/b.m3u8
"""
OLD = """#EXTM3U
#EXTINF:-1,Bravo
https://example.com/b.m3u8
"""

class TestVerified(unittest.TestCase):
    def test_publish_confirmed_only(self):
        result, info = select_verified(SRC, {"results": [
            {"url": "https://example.com/a.m3u8", "status": "MEDIA_NÅBAR"},
            {"url": "https://example.com/b.m3u8", "status": "SAKNAS"}]}, "Kurdistan")
        self.assertTrue(info["published"])
        self.assertIn("Alpha", result)
        self.assertNotIn("Bravo", result)

    def test_keep_previous_during_transient_outage(self):
        result, info = select_verified(SRC, {"results": [
            {"url": "https://example.com/a.m3u8", "status": "MEDIA_NÅBAR"},
            {"url": "https://example.com/b.m3u8", "status": "BLOCKERAD"}]}, "Kurdistan", OLD)
        self.assertIn("Bravo", result)
        self.assertEqual(info["retained"], 1)

    def test_avoid_wiping_old_playlist_when_all_bad(self):
        result, info = select_verified(SRC, {"results": [
            {"url": "https://example.com/b.m3u8", "status": "SAKNAS"}]}, "Kurdistan", OLD)
        self.assertIsNone(result)
        self.assertFalse(info["published"])

    def test_no_publish_when_nothing_confirmed(self):
        result, _ = select_verified(SRC, {"results": []}, "Kurdistan")
        self.assertIsNone(result)
if __name__ == "__main__":
    unittest.main()
