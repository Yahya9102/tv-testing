#!/usr/bin/env python3
"""Publish a conservative, tested M3U. Never wipe a working list on mass failure."""
from __future__ import annotations
import argparse
import json
import sys
from pathlib import Path
from build import parse_m3u, render_playlist

TRANSIENT = {"BLOCKERAD", "OSÄKER", "SPELLISTA_NÅBAR"}

def select_verified(source_text: str, report: dict, group: str,
                    previous_text: str | None = None) -> tuple[str | None, dict]:
    entries = parse_m3u(source_text, group)
    prior = set()
    if previous_text:
        try:
            prior = {entry.url for entry in parse_m3u(previous_text, group)}
        except ValueError:
            prior = set()
    checks = {r["url"]: r["status"] for r in report.get("results", [])
              if isinstance(r, dict) and isinstance(r.get("url"), str)
              and isinstance(r.get("status"), str)}
    chosen = []
    fresh = retained = 0
    for entry in entries:
        status = checks.get(entry.url)
        if status == "MEDIA_NÅBAR":
            chosen.append(entry)
            fresh += 1
        elif entry.url in prior and status in TRANSIENT:
            chosen.append(entry)
            retained += 1
    if not chosen or (prior and len(chosen) < max(1, len(prior) // 2)):
        return None, {"published": False, "fresh": fresh, "retained": retained,
                      "reason": "No successes or widespread outage"}
    return render_playlist(chosen), {"published": True, "fresh": fresh,
                                     "retained": retained, "total": len(chosen)}

def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--playlist", type=Path, required=True)
    p.add_argument("--report", type=Path, required=True)
    p.add_argument("--output", type=Path, required=True)
    p.add_argument("--group", required=True)
    args = p.parse_args()
    try:
        source = args.playlist.read_text(encoding="utf-8-sig")
        report = json.loads(args.report.read_text(encoding="utf-8"))
        old = args.output.read_text(encoding="utf-8-sig") if args.output.exists() else None
        result, stats = select_verified(source, report, args.group, old)
        print(json.dumps(stats, ensure_ascii=False))
        if result is None:
            print("WARNING: previous verified list preserved", file=sys.stderr)
            return 0
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temp = args.output.with_suffix(".tmp")
        temp.write_bytes(result.replace("\n", "\r\n").encode("utf-8"))
        temp.replace(args.output)
        return 0
    except (OSError, ValueError, KeyError, TypeError) as exc:
        print(f"Verified list not published: {exc}", file=sys.stderr)
        return 1

if __name__ == "__main__":
    raise SystemExit(main())
