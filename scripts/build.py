#!/usr/bin/env python3
"""Build IBO-compatible M3U files from IPTV-org and local curated sources.

No external Python dependencies. Only public HTTP(S) stream URLs are included.
This program does not bypass DRM, subscription checks, or geographic blocks.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlparse
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
META = re.compile(r'\s+group-title="[^"]*"')
HEADERS = ("#EXTVLCOPT:", "#KODIPROP:")


@dataclass(frozen=True)
class Channel:
    info: str
    url: str
    options: tuple[str, ...] = ()

    def render(self) -> str:
        return "\n".join((self.info, *self.options, self.url)) + "\n"


def valid_stream_url(value: str) -> bool:
    parsed = urlparse(value)
    return parsed.scheme in {"http", "https"} and bool(parsed.netloc) and not parsed.username and not parsed.password


def re_group(extinf: str, group_name: str) -> str:
    # Escape metadata attribute values; group names are controlled by config.json.
    group_name = group_name.replace('"', "'").replace('\r', " ").replace('\n', " ")
    attr = f' group-title="{group_name}"'
    if META.search(extinf):
        return META.sub(attr, extinf, count=1)
    # Add the group title before the channel name (first comma outside quotes).
    quoted = False
    for index, char in enumerate(extinf):
        if char == '"':
            quoted = not quoted
        elif char == "," and not quoted:
            return extinf[:index] + attr + extinf[index:]
    return extinf + attr


def parse_m3u(data: str, group_name: str) -> list[Channel]:
    if not data.lstrip("\ufeff \r\n\t").startswith("#EXTM3U"):
        raise ValueError("The source does not start with #EXTM3U")

    channels: list[Channel] = []
    info: str | None = None
    options: list[str] = []
    for raw_line in data.splitlines():
        line = raw_line.strip()
        if line.startswith("#EXTINF:"):
            info = re_group(line, group_name)
            options = []
        elif info is not None and line.startswith(HEADERS):
            options.append(line)
        elif info is not None and line and not line.startswith("#"):
            if valid_stream_url(line):
                channels.append(Channel(info, line, tuple(options)))
            info, options = None, []
    return channels


def unique_channels(channels: list[Channel]) -> list[Channel]:
    seen: set[str] = set()
    result = []
    for channel in channels:
        if channel.url not in seen:
            seen.add(channel.url)
            result.append(channel)
    return result


def render_playlist(channels: list[Channel]) -> str:
    return "#EXTM3U\n" + "".join(channel.render() for channel in channels)


def fetch_playlist(url: str, attempts: int = 3) -> str:
    parsed = urlparse(url)
    if parsed.scheme != "https" or parsed.hostname != "iptv-org.github.io":
        raise ValueError(f"Only trusted IPTV-org HTTPS sources are allowed: {url}")
    last_error: Exception | None = None
    for attempt in range(attempts):
        try:
            request = Request(url, headers={"User-Agent": "familje-iptv-builder/1.0", "Accept": "audio/x-mpegurl, text/plain, */*"})
            with urlopen(request, timeout=30) as response:
                content = response.read(15_000_001)
            if len(content) > 15_000_000:
                raise ValueError("Source exceeds 15 MB")
            return content.decode("utf-8-sig")
        except (HTTPError, URLError, TimeoutError, UnicodeDecodeError) as error:
            last_error = error
            if attempt < attempts - 1:
                time.sleep(2 ** attempt)
    raise RuntimeError(f"Could not retrieve {url}: {last_error}")


def read_local_source(relative_path: str, root: Path = ROOT) -> str:
    """Read a curated local M3U file; disallow arbitrary paths and symlink escapes."""
    permitted = (root / "sources").resolve()
    selected = (root / relative_path).resolve()
    if not selected.is_relative_to(permitted) or selected.suffix != ".m3u":
        raise ValueError(f"Invalid local M3U path: {relative_path}")
    if not selected.is_file() or selected.stat().st_size > 1_000_000:
        raise ValueError(f"Local M3U is missing or too large: {relative_path}")
    return selected.read_text(encoding="utf-8-sig")


def build(config: dict, fetcher=fetch_playlist, root: Path = ROOT) -> tuple[dict[str, str], dict]:
    groups = config["groups"]
    files: dict[str, str] = {}
    all_channels: list[Channel] = []
    stats = {"updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"), "groups": {}, "warnings": [], "source": "IPTV-org and curated public URL candidates; availability not tested"}
    for group in groups:
        group_id, name = group["id"], group["name"]
        if not re.fullmatch(r"[a-z0-9_-]+", group_id):
            raise ValueError(f"Unsafe group id: {group_id}")
        entries = []
        for source in group["sources"]:
            url = source if isinstance(source, str) else source.get("file", source.get("url", "unknown"))
            try:
                if isinstance(source, dict) and "file" in source:
                    raw = read_local_source(source["file"], root=root)
                else:
                    raw = fetcher(url)
                downloaded = parse_m3u(raw, name)
                if isinstance(source, dict) and source.get("channel_ids"):
                    wanted_ids = set(source["channel_ids"])
                    downloaded = [c for c in downloaded if (match := re.search(r'tvg-id="([^"]+)"', c.info)) and match.group(1) in wanted_ids]
                if not downloaded:
                    raise ValueError(f"No usable streams in {url}")
                entries.extend(downloaded)
            except (RuntimeError, ValueError, OSError, HTTPError, URLError, TimeoutError) as error:
                warning = f"{group_id}: skipped {url}: {error}"
                print("WARNING: " + warning, file=sys.stderr)
                stats["warnings"].append(warning)
        if not entries:
            previous = root / "playlists" / f"{group_id}.m3u"
            if previous.is_file():
                try:
                    entries = parse_m3u(previous.read_text(encoding="utf-8-sig"), name)
                except (OSError, ValueError):
                    entries = []
            if not entries:
                raise RuntimeError(f"No working source or previous playlist for {group_id}")
            stats["warnings"].append(f"{group_id}: preserved previous playlist")
        own = unique_channels(entries)
        files[f"{group_id}.m3u"] = render_playlist(own)
        stats["groups"][group_id] = {"label": name, "channels": len(own), "sources": len(group["sources"])}
        all_channels.extend(own)

    combined = unique_channels(all_channels)
    files["all.m3u"] = render_playlist(combined)
    stats["combined_unique_streams"] = len(combined)
    return files, stats


def write_results(files: dict[str, str], stats: dict, destination: Path) -> None:
    destination.mkdir(parents=True, exist_ok=True)
    # Generate all content first: a bad/upstream unavailable feed cannot erase playlists.
    for name, content in files.items():
        if not content.startswith("#EXTM3U\n"):
            raise ValueError(f"Invalid output: {name}")
    for name, content in files.items():
        output = destination / name
        temporary = destination / f".{name}.tmp"
        # UTF-8 + CRLF widely supported by IPTV clients.
        temporary.write_bytes(content.replace("\n", "\r\n").encode("utf-8"))
        temporary.replace(output)
    status = destination / "status.json"
    temporary = destination / ".status.json.tmp"
    temporary.write_text(json.dumps(stats, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(status)


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate country/language M3U playlists for IBO Player")
    parser.add_argument("--config", type=Path, default=ROOT / "config.json")
    parser.add_argument("--output", type=Path, default=ROOT / "playlists")
    args = parser.parse_args()
    try:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        files, stats = build(config)
        write_results(files, stats, args.output)
    except (ValueError, RuntimeError, OSError, KeyError, TypeError, json.JSONDecodeError) as error:
        print(f"Playlist build failed; previous files were kept: {error}", file=sys.stderr)
        return 1
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
