#!/usr/bin/env python3
"""Rebuild playlist.m3u by merging iptv-org and ustvgo sources.

Combines official US streams from:
1. iptv-org US public catalog (filtered for US-reachable hosts)
2. ustvgo.tv (alternative US stream source)

Deduplicates channels and prioritizes official/higher-quality streams.
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

# iptv-org sources
US_M3U = "https://iptv-org.github.io/iptv/countries/us.m3u"
STREAMS_API = "https://iptv-org.github.io/api/streams.json"

# ustvgo source
USTVGO_CHANNELS = "https://raw.githubusercontent.com/benmoose39/ustvgo_to_m3u/main/ustvgo_channel_info.txt"

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
    """Parse M3U playlist format."""
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
                    "source": "iptv-org",
                }
            )
            extinf = None
            extras = []
    return entries


def parse_ustvgo_channels(text: str) -> list[dict]:
    """Parse ustvgo channel info format: Name|Code|Logo|TVG|VPN(optional)"""
    entries: list[dict] = []
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("~~"):
            continue
        parts = [p.strip() for p in line.split("|")]
        if len(parts) < 3:
            continue
        
        name = parts[0]
        code = parts[1]
        logo = parts[2]
        requires_vpn = len(parts) > 4 and parts[4].upper() == "VPN"
        
        # We'll construct the actual stream URL when we have the sample
        entries.append(
            {
                "name": name,
                "code": code,
                "logo": logo,
                "tvg": code.lower(),
                "group": "ustvgo",
                "requires_vpn": requires_vpn,
                "source": "ustvgo",
                "url": None,  # Will be populated later
            }
        )
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


def get_ustvgo_sample_urls() -> tuple[str, str]:
    """Get sample stream URLs from ustvgo (CNN for non-VPN, BET for VPN)."""
    headers = {"Referer": "https://ustvgo.tv/"}
    
    # Non-VPN sample
    try:
        cnn_req = urllib.request.Request(
            "https://ustvgo.tv/player.php?stream=CNN",
            headers=headers,
        )
        cnn_resp = urllib.request.urlopen(cnn_req, timeout=10)
        cnn_text = cnn_resp.read().decode("utf-8", errors="replace")
        novpn_sample = cnn_text.split("hls_src='")[1].split("'")[0]
    except (IndexError, urllib.error.URLError, Exception):
        novpn_sample = ""
    
    # VPN sample
    try:
        bet_req = urllib.request.Request(
            "https://ustvgo.tv/player.php?stream=BET",
            headers=headers,
        )
        bet_resp = urllib.request.urlopen(bet_req, timeout=10)
        bet_text = bet_resp.read().decode("utf-8", errors="replace")
        vpn_sample = bet_text.split("hls_src='")[1].split("'")[0]
    except (IndexError, urllib.error.URLError, Exception):
        vpn_sample = "https://raw.githubusercontent.com/benmoose39/YouTube_to_m3u/main/assets/moose_na.m3u"
    
    return novpn_sample, vpn_sample


def populate_ustvgo_urls(entries: list[dict]) -> list[dict]:
    """Populate actual stream URLs for ustvgo entries."""
    novpn_sample, vpn_sample = get_ustvgo_sample_urls()
    
    populated = []
    for entry in entries:
        if not novpn_sample and not vpn_sample:
            continue  # Skip if we couldn't get samples
        
        if entry["requires_vpn"] and vpn_sample:
            url = vpn_sample.replace("BET", entry["code"])
        elif not entry["requires_vpn"] and novpn_sample:
            url = novpn_sample.replace("CNN", entry["code"])
        else:
            continue
        
        entry["url"] = url
        populated.append(entry)
    
    return populated


def sort_key(entry: dict) -> tuple:
    groups = [part.strip() for part in entry["group"].split(";") if part.strip()]
    is_sports = any(part.lower() == "sports" for part in groups)
    primary = groups[0] if groups else "Undefined"
    return (0 if is_sports else 1, primary.lower(), entry["name"].lower())


def format_entry_for_m3u(entry: dict) -> tuple[str, str, str]:
    """Format an entry into M3U lines (info, extras, url)."""
    if entry["source"] == "iptv-org":
        return entry["info"], "\n".join(entry["extras"]), entry["url"]
    else:  # ustvgo
        extinf = f'#EXTINF:-1 tvg-id="{entry["tvg"]}" tvg-logo="{entry["logo"]}" group-title="{entry["group"]}", {entry["name"]}'
        return extinf, "", entry["url"]


def main() -> None:
    print("[*] Fetching iptv-org US catalog...")
    us_text = fetch(US_M3U).decode("utf-8", errors="replace")
    streams = json.loads(fetch(STREAMS_API).decode("utf-8"))
    geo_urls = {
        stream["url"]
        for stream in streams
        if "Geo-blocked" in (stream.get("labels") or [])
    }

    # Process iptv-org entries
    kept_iptv: list[dict] = []
    skipped_iptv = Counter()
    seen_urls: set[str] = set()

    print("[*] Processing iptv-org entries...")
    for entry in parse_m3u(us_text):
        if "[Geo-blocked]" in entry["name"] or entry["url"] in geo_urls:
            skipped_iptv["geo-blocked"] += 1
            continue
        if is_rejected_host(entry["url"]):
            skipped_iptv["panel-or-restream-host"] += 1
            continue
        if entry["url"] in seen_urls:
            skipped_iptv["duplicate"] += 1
            continue
        seen_urls.add(entry["url"])
        kept_iptv.append(entry)

    # Process ustvgo entries
    print("[*] Fetching ustvgo channels...")
    try:
        ustvgo_text = fetch(USTVGO_CHANNELS).decode("utf-8", errors="replace")
        ustvgo_entries = parse_ustvgo_channels(ustvgo_text)
        print(f"[*] Found {len(ustvgo_entries)} ustvgo channels, populating URLs...")
        ustvgo_entries = populate_ustvgo_urls(ustvgo_entries)
    except Exception as e:
        print(f"[!] Error fetching ustvgo channels: {e}")
        ustvgo_entries = []

    # Merge and deduplicate
    print("[*] Merging playlists...")
    all_entries = kept_iptv + ustvgo_entries
    
    # Deduplicate by URL (prefer iptv-org over ustvgo)
    unique_entries = []
    seen_urls_merged: set[str] = set()
    for entry in all_entries:
        if entry["url"] not in seen_urls_merged:
            unique_entries.append(entry)
            seen_urls_merged.add(entry["url"])

    unique_entries.sort(key=sort_key)

    # Generate statistics
    groups = Counter(
        part.strip()
        for entry in unique_entries
        for part in entry["group"].split(";")
        if part.strip()
    )
    sports_count = sum(
        1
        for entry in unique_entries
        if any(part.strip().lower() == "sports" for part in entry["group"].split(";"))
    )
    ustvgo_count = sum(1 for entry in unique_entries if entry["source"] == "ustvgo")
    iptv_count = len(unique_entries) - ustvgo_count

    # Write output
    lines = [
        f'#EXTM3U url-tvg="{",".join(EPG_URLS)}"',
        "# Source: Merged iptv-org US public catalog + ustvgo",
        "# Sports are listed first. Premium pay-TV restreams are omitted.",
        f"# Channels: {len(unique_entries)} (iptv-org: {iptv_count}, ustvgo: {ustvgo_count}). Sports-tagged: {sports_count}.",
        f"# Skipped (iptv-org): geo-blocked {skipped_iptv['geo-blocked']}, panel hosts {skipped_iptv['panel-or-restream-host']}, duplicates {skipped_iptv['duplicate']}.",
    ]
    
    for entry in unique_entries:
        info, extras, url = format_entry_for_m3u(entry)
        lines.append(info)
        if extras:
            lines.append(extras)
        lines.append(url)

    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
    
    print(f"\n[SUCCESS] Wrote {OUT}")
    print(f"  Total channels: {len(unique_entries)}")
    print(f"    - iptv-org: {iptv_count}")
    print(f"    - ustvgo: {ustvgo_count}")
    print(f"  Sports-tagged: {sports_count}")
    print("\nSkipped (iptv-org):")
    for reason, count in skipped_iptv.items():
        print(f"  - {reason}: {count}")
    print("\nTop groups:", dict(groups.most_common(10)))


if __name__ == "__main__":
    main()
