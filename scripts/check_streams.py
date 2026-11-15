#!/usr/bin/env python3
"""Check HLS playlist availability and fetch a tiny portion of a media segment.

A successful check confirms network reachability, not playable audio/video in IBO.
Does not bypass DRM, passwords, subscriptions, or geographical restrictions.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlsplit
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
USER_AGENT = "Mozilla/5.0 (compatible; family-iptv-healthcheck/1.0)"
LIMIT = 384 * 1024


def read_channels(text: str, group: str | None = None) -> list[tuple[str, str]]:
    if not text.lstrip("\ufeff \r\n\t").startswith("#EXTM3U"):
        raise ValueError("Inte en giltig M3U-spellista")
    result = []
    title = None
    for raw in text.splitlines():
        line = raw.strip()
        if line.startswith("#EXTINF:"):
            matched = re.search(r'group-title="([^"]*)"', line)
            category = matched.group(1) if matched else None
            title = (line.rsplit(",", 1)[-1].strip() or "Okänd kanal") if group is None or category == group else None
        elif title and line and not line.startswith("#"):
            parts = urlsplit(line)
            if parts.scheme in ("http", "https") and parts.hostname and not (parts.username or parts.password):
                result.append((title, line))
            title = None
    return result


def fetch(url: str, timeout: float, *, limit: int = LIMIT) -> tuple[int, bytes, str]:
    req = Request(url, headers={"User-Agent": USER_AGENT, "Accept": "*/*"})
    with urlopen(req, timeout=timeout) as response:
        status = response.status
        # Read bounded bytes; no video segments are saved to disk.
        data = response.read(limit)
        return status, data, response.geturl()


def status_for_error(error: Exception) -> tuple[str, str]:
    if isinstance(error, HTTPError):
        if error.code in (401, 403):
            return "BLOCKERAD", f"HTTP {error.code} (behörighet eller region)"
        if error.code in (404, 410):
            return "SAKNAS", f"HTTP {error.code}"
        if error.code == 429:
            return "OSÄKER", "HTTP 429 (tillfällig begränsning)"
        return "FEL", f"HTTP {error.code}"
    if isinstance(error, (TimeoutError, URLError, OSError)):
        return "OSÄKER", "Timeout, DNS eller nätverksfel"
    return "OSÄKER", "Oförutsett svar"


def segment_uri(lines: list[str]) -> str | None:
    # For media playlists, the first non-comment URI is typically a segment.
    for line in lines:
        line = line.strip()
        if line and not line.startswith("#"):
            return line
    return None


def verify(url: str, fetcher=fetch, timeout: float = 8.0) -> tuple[str, str]:
    current = url
    for depth in range(4):
        try:
            code, body, final_url = fetcher(current, timeout)
        except Exception as exc:
            return status_for_error(exc)
        if code < 200 or code >= 300:
            return "FEL", f"HTTP {code}"
        try:
            playlist = body.decode("utf-8-sig", errors="replace")
        except Exception:
            return "FEL", "Ogiltig M3U8"
        if not playlist.lstrip().startswith("#EXTM3U"):
            return "FEL", "Servern returnerade inte M3U8"
        lines = playlist.splitlines()
        # A master playlist contains variants or #EXT-X-STREAM-INF; follow first variant.
        if any(l.startswith("#EXT-X-STREAM-INF:") for l in lines):
            for i, line in enumerate(lines):
                if line.startswith("#EXT-X-STREAM-INF:"):
                    nxt = next((s.strip() for s in lines[i + 1:] if s.strip() and not s.startswith("#")), None)
                    if nxt:
                        current = urljoin(final_url, nxt)
                        break
            else:
                return "SPELLISTA_NÅBAR", "Master-lista utan variantadress"
            continue
        if any(l.startswith("#EXTINF:") for l in lines):
            segment = segment_uri(lines)
            if segment is None:
                return "SPELLISTA_NÅBAR", "M3U8 finns men inga segment hittades"
            segment_url = urljoin(final_url, segment)
            try:
                scode, data, _ = fetcher(segment_url, timeout, limit=1024)
            except Exception as exc:
                label, detail = status_for_error(exc)
                return "SPELLISTA_NÅBAR", f"Manifest OK; segment: {detail}"
            if scode in (200, 206) and data:
                return "MEDIA_NÅBAR", "Manifest + del av mediasegment kan hämtas"
            return "SPELLISTA_NÅBAR", f"Manifest OK; segment HTTP {scode}"
        return "SPELLISTA_NÅBAR", "M3U8 svarar men inga vanliga segment hittades"
    return "SPELLISTA_NÅBAR", "M3U8 med för många undernivåer"


def check_one(item: tuple[str, str], timeout: float) -> dict:
    name, url = item
    status, reason = verify(url, timeout=timeout)
    return {"name": name, "url": url, "status": status, "reason": reason}


def markdown(rows: list[dict], checked_at: str) -> str:
    groups = ["MEDIA_NÅBAR", "SPELLISTA_NÅBAR", "BLOCKERAD", "SAKNAS", "OSÄKER", "FEL"]
    counts = {key: sum(r["status"] == key for r in rows) for key in groups}
    out = [
        "# Kontroll av IPTV-kanaler",
        "",
        f"Körd (UTC): **{checked_at}**",
        "",
        f"**{len(rows)} adresser** – " + " · ".join(f"{k}: {v}" for k, v in counts.items() if v),
        "",
        "**MEDIA_NÅBAR** betyder att ett M3U8-manifest och en del av ett mediasegment gick att hämta, "
        "inte att kanalen garanterat kan spelas i IBO Player. **SPELLISTA_NÅBAR** är en svagare kontroll. "
        "BLOCKERAD kan vara geografisk. Status kan ändras när som helst.",
        "",
        "| Kanal | Status | Kommentar |",
        "|---|---|---|",
    ]
    for r in rows:
        name = r["name"].replace("|", "\\|")
        reason = r["reason"].replace("|", "\\|")
        out.append(f"| {name} | {r['status']} | {reason} |")
    out += ["", "Den här kontrollen körs på GitHubs nätverk, inte på TV:ns nätverk i Sverige.", ""]
    return "\n".join(out)


def main() -> int:
    parser = argparse.ArgumentParser(description="Check M3U HLS URLs; no live playback guarantee")
    parser.add_argument("--playlist", type=Path, default=ROOT / "playlists/kurdistan.m3u")
    parser.add_argument("--report", type=Path, default=ROOT / "reports/kurdistan-health.md")
    parser.add_argument("--json", type=Path, default=ROOT / "reports/kurdistan-health.json")
    parser.add_argument("--timeout", type=float, default=8.0)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--group", default=None, help="Endast denna M3U group-title")
    args = parser.parse_args()
    try:
        channels = read_channels(args.playlist.read_text(encoding="utf-8-sig"), group=args.group)
        if not channels:
            raise ValueError("Inga kanaler hittades")
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(args.workers, 16))) as pool:
            rows = list(pool.map(lambda c: check_one(c, args.timeout), channels))
        checked_at = datetime.now(timezone.utc).isoformat(timespec="seconds")
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(markdown(rows, checked_at), encoding="utf-8")
        args.json.write_text(json.dumps({"checked_at_utc": checked_at, "results": rows}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        counts = {k: sum(row["status"] == k for row in rows) for k in set(r["status"] for r in rows)}
        print(f"Checked {len(rows)} URLs: {counts}")
        return 0
    except (OSError, ValueError) as exc:
        print(f"Health check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
