import unittest
from urllib.error import HTTPError
from scripts.check_streams import read_channels, verify, markdown

class CheckStreamTests(unittest.TestCase):
    def test_parse(self):
        got = read_channels('#EXTM3U\n#EXTINF:-1,Channel One\nhttps://example.com/live.m3u8\n')
        self.assertEqual(got, [('Channel One', 'https://example.com/live.m3u8')])

    def test_master_variant_and_segment(self):
        hits = []
        def fetcher(url, timeout, *, limit=384*1024):
            hits.append(url)
            if url.endswith('index.m3u8'):
                return 200, b'#EXTM3U\n#EXT-X-STREAM-INF:BANDWIDTH=1000\nchannel.m3u8\n', url
            if url.endswith('channel.m3u8'):
                return 200, b'#EXTM3U\n#EXT-X-TARGETDURATION:6\n#EXTINF:6,\nmedia/part.ts\n', url
            if url.endswith('media/part.ts'):
                return 206, b'\x47\x40\x00', url
            raise AssertionError(url)
        result = verify('https://example.com/index.m3u8', fetcher)
        self.assertEqual(result[0], 'MEDIA_NÅBAR')
        self.assertEqual(len(hits), 3)

    def test_forbidden(self):
        def fetcher(url, timeout, *, limit=384*1024):
            raise HTTPError(url, 403, 'Forbidden', {}, None)
        self.assertEqual(verify('https://example.com/blocked.m3u8', fetcher)[0], 'BLOCKERAD')

    def test_not_manifest(self):
        def fetcher(url, timeout, *, limit=384*1024):
            return 200, b'<html>error</html>', url
        self.assertEqual(verify('https://example.com/index.m3u8', fetcher)[0], 'FEL')

    def test_manifest_reachable_without_segment(self):
        def fetcher(url, timeout, *, limit=384*1024):
            if url.endswith('.m3u8'):
                return 200, b'#EXTM3U\n#EXTINF:6.0,\nsegment.ts\n', url
            raise TimeoutError()
        self.assertEqual(verify('https://example.com/index.m3u8', fetcher)[0], 'SPELLISTA_NÅBAR')

    def test_report(self):
        result = markdown([{'name':'Example','status':'MEDIA_NÅBAR','reason':'OK'}], '2026-01-01T00:00:00Z')
        self.assertIn('| Example | MEDIA_NÅBAR | OK |', result)

if __name__ == '__main__':
    unittest.main()
