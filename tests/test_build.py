import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from build import (Channel, build, parse_m3u, re_group, render_playlist,
                   unique_channels, valid_stream_url, write_results, read_local_source)

SAMPLE = '''#EXTM3U x-tvg-url="https://example.org/guide.xml"
#EXTINF:-1 tvg-id="a" tvg-logo="https://example.com/logo.png" group-title="News",Alpha
https://example.com/a.m3u8
#EXTINF:-1 tvg-id="b",Bravo
#EXTVLCOPT:http-referrer=https://example.com/
https://example.org/b.m3u8
#EXTINF:-1 tvg-id="bad",Invalid
file:///etc/passwd
'''


class BuilderTests(unittest.TestCase):
    def test_parses_entries_and_preserves_stream_options(self):
        entries = parse_m3u(SAMPLE, "Kurdistan")
        self.assertEqual(2, len(entries))
        self.assertIn('group-title="Kurdistan"', entries[0].info)
        self.assertIn('group-title="Kurdistan"', entries[1].info)
        self.assertEqual(("#EXTVLCOPT:http-referrer=https://example.com/",), entries[1].options)

    def test_does_not_accept_credentials_or_local_uris(self):
        self.assertFalse(valid_stream_url("file:///etc/passwd"))
        self.assertFalse(valid_stream_url("https://user:pass@example.com/a"))
        self.assertTrue(valid_stream_url("http://example.com/live.m3u8"))

    def test_deduplicates_by_url_without_changing_order(self):
        channel = Channel('#EXTINF:-1,Alpha', 'https://example.com/a.m3u8')
        unique = unique_channels([channel, channel, Channel('#EXTINF:-1,Bravo', 'https://example.com/b.m3u8')])
        self.assertEqual(2, len(unique))
        self.assertEqual('https://example.com/a.m3u8', unique[0].url)

    def test_builds_one_combined_playlist_with_categories(self):
        config = {"groups": [
            {"id": "kurdistan", "name": "Kurdistan", "sources": ["url1"]},
            {"id": "iraq", "name": "Irak", "sources": ["url2"]}
        ]}
        files, stats = build(config, fetcher=lambda url: SAMPLE)
        self.assertEqual({"all.m3u"}, set(files))
        self.assertIn('group-title="Kurdistan"', files["all.m3u"])
        self.assertIn('group-title="Irak"', files["all.m3u"])
        self.assertEqual(2, stats["combined_unique_streams"])
        self.assertEqual(2, stats["groups"]["iraq"]["channels"])

    def test_can_select_one_channel_from_a_second_source(self):
        config = {"groups": [{"id": "kurdistan", "name": "Kurdistan", "sources": [
            "first", {"url": "second", "channel_ids": ["b"]}
        ]}]}
        files, stats = build(config, fetcher=lambda _: SAMPLE)
        self.assertEqual(2, stats["combined_unique_streams"])
        self.assertIn("Bravo", files["all.m3u"])

    def test_build_local_curated_source_and_keep_remote_entries(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sources").mkdir()
            (root / "sources/kurdish-extra.m3u").write_text(SAMPLE, encoding="utf-8")
            cfg = {"groups": [{"id": "kurdistan", "name": "Kurdistan", "sources": [
                "https://iptv-org.github.io/iptv/languages/kur.m3u",
                {"file": "sources/kurdish-extra.m3u"}
            ]}]}
            files, stats = build(cfg, fetcher=lambda _: SAMPLE, root=root)
            self.assertEqual(2, stats["groups"]["kurdistan"]["channels"])
            self.assertIn("Alpha", files["all.m3u"])


    def test_fallback_from_single_existing_combined_playlist(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "playlists").mkdir()
            (root / "playlists/all.m3u").write_text(
                '#EXTM3U\n#EXTINF:-1 group-title="Kurdistan",Legacy\n'
                'https://example.com/legacy.m3u8\n', encoding="utf-8"
            )
            cfg = {"groups": [
                {"id": "kurdistan", "name": "Kurdiska", "sources": ["broken"]}
            ]}
            files, stats = build(cfg, fetcher=lambda _: "bad", root=root)
            self.assertEqual({"all.m3u"}, set(files))
            self.assertIn("Legacy", files["all.m3u"])
            self.assertIn('group-title="Kurdiska"', files["all.m3u"])
            self.assertEqual(1, stats["combined_unique_streams"])

    def test_blocks_unsafe_local_source_path(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / "sources").mkdir()
            (root / "other.m3u").write_text(SAMPLE, encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Invalid local M3U"):
                read_local_source("other.m3u", root=root)
            with self.assertRaisesRegex(ValueError, "Invalid local M3U"):
                read_local_source("sources/../../other.m3u", root=root)

    def test_rejects_bad_source_before_writing(self):
        config = {"groups": [{"id": "bad", "name": "Bad", "sources": ["url"]}]}
        with self.assertRaisesRegex(RuntimeError, "No working source or previous playlist"):
            build(config, fetcher=lambda _: "Bad response")

    def test_output_is_crlf_m3u_and_status_exists(self):
        with tempfile.TemporaryDirectory() as folder:
            write_results({"all.m3u": render_playlist([Channel('#EXTINF:-1,Test', 'https://example.com/1')])}, {"count": 1}, Path(folder))
            self.assertTrue((Path(folder) / 'all.m3u').read_bytes().startswith(b'#EXTM3U\r\n'))
            self.assertTrue((Path(folder) / 'status.json').is_file())


if __name__ == "__main__":
    unittest.main()
