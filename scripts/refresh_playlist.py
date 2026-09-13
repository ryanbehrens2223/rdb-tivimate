#!/usr/bin/env python3
"""Rebuild playlist.m3u from the public US iptv-org catalog.

Keeps official free/FAST-style US streams across public categories.
Drops geo-blocked feeds and streams served from anonymous IPTV panels
(IP:port hosts and known restream hostnames). Those are how premium
pay-TV sports and movie channels show up in the raw country list.
"""

from __future__ import annotations

import json
import re
import urllib.request
from collections import Counter
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "playlist.m3u"

US_M3U = "https://iptv-org.github.io/iptv/countries/us.m3u"
STREAMS_API = "https://iptv-org.github.io/api/streams.json"

EPG_URLS = [
    "https://i.mjh.nz/PlutoTV/us.xml",
    "https://i.mjh.nz/SamsungTVPlus/us.xml",
]

BAD_HOST_NEEDLES = (
    "damitv",
    "ayitistream",
    "aynascope",
    "aynaott",
)

USER_AGENT = "rdb-tivimate-refresh/1.0"


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def parse_m3u(text: str) -> list[dict]:
    entries: list[dict] = []
    extinf: str | None = None
    extras: list[str] = []
    for raw in text.splitlines():
        line = raw.strip()
        if not line:
            continue
        if line.startswith("#EXTINF"):
            extinf = line
            extras = []
        elif line.startswith("#") and extinf:
            extras.append(line)
        elif extinf and not line.startswith("#"):
            tvg = re.search(r'tvg-id="([^"]*)"', extinf)
            group = re.search(r'group-title="([^"]*)"', extinf)
            name = extinf.split(",", 1)[-1] if "," in extinf else extinf
            entries.append(
                {
                    "info": extinf,
                    "extras": extras,
                    "url": line,
                    "tvg": tvg.group(1) if tvg else "",
                    "group": group.group(1) if group else "Undefined",
                    "name": name,
                }
            )
            extinf = None
            extras = []
    return entries


def is_ip_host(host: str) -> bool:
    hostname = host.split(":")[0]
    parts = hostname.split(".")
    return len(parts) == 4 and all(part.isdigit() for part in parts)


def is_rejected_host(url: str) -> bool:
    host = urlparse(url).netloc.lower()
    if not host:
        return True
    if is_ip_host(host):
        return True
    return any(needle in host for needle in BAD_HOST_NEEDLES)


def sort_key(entry: dict) -> tuple:
    groups = [part.strip() for part in entry["group"].split(";") if part.strip()]
    is_sports = any(part.lower() == "sports" for part in groups)
    primary = groups[0] if groups else "Undefined"
    return (0 if is_sports else 1, primary.lower(), entry["name"].lower())


def main() -> None:
    us_text = fetch(US_M3U).decode("utf-8", errors="replace")
    streams = json.loads(fetch(STREAMS_API).decode("utf-8"))
    geo_urls = {
        stream["url"]
        for stream in streams
        if "Geo-blocked" in (stream.get("labels") or [])
    }

    kept: list[dict] = []
    skipped = Counter()
    seen_urls: set[str] = set()

    for entry in parse_m3u(us_text):
        if "[Geo-blocked]" in entry["name"] or entry["url"] in geo_urls:
            skipped["geo-blocked"] += 1
            continue
        if is_rejected_host(entry["url"]):
            skipped["panel-or-restream-host"] += 1
            continue
        if entry["url"] in seen_urls:
            skipped["duplicate"] += 1
            continue
        seen_urls.add(entry["url"])
        kept.append(entry)

    kept.sort(key=sort_key)
    groups = Counter(
        part.strip()
        for entry in kept
        for part in entry["group"].split(";")
        if part.strip()
    )
    sports_count = sum(
        1
        for entry in kept
        if any(part.strip().lower() == "sports" for part in entry["group"].split(";"))
    )

    lines = [
        f'#EXTM3U url-tvg="{",".join(EPG_URLS)}"',
        "# Source: iptv-org US public catalog, filtered for US-reachable official hosts.",
        "# Sports are listed first. Premium pay-TV restreams are omitted.",
        f"# Channels: {len(kept)}. Sports-tagged: {sports_count}.",
        f"# Skipped geo-blocked: {skipped['geo-blocked']}. Skipped panel hosts: {skipped['panel-or-restream-host']}.",
    ]
    for entry in kept:
        lines.append(entry["info"])
        lines.extend(entry["extras"])
        lines.append(entry["url"])

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"Wrote {OUT} ({len(kept)} channels, {sports_count} sports-tagged)")
    print("Skipped:", dict(skipped))
    print("Groups:", dict(groups.most_common()))


if __name__ == "__main__":
    main()
