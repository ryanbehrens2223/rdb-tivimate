#!/usr/bin/env python3
"""Fetch and merge EPG XML files from multiple sources into a single epg.xml.

Combines EPG data from:
1. Pluto TV US (iptv-org source)
2. Samsung TV Plus US (iptv-org source)
3. ustvgo EPG (alternative source)

Merges all channels into a single XML file with unified tvg-id mapping.
"""

from __future__ import annotations

import gzip
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime
from pathlib import Path
from urllib.error import URLError

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "epg.xml"

EPG_SOURCES = [
    ("PlutoTV", "https://i.mjh.nz/PlutoTV/us.xml"),
    ("SamsungTVPlus", "https://i.mjh.nz/SamsungTVPlus/us.xml"),
    ("ustvgo", "https://www.kcpcdr.com/ustvgo.xml.gz"),
]

USER_AGENT = "rdb-tivimate-epg/1.0"


def fetch(url: str) -> bytes:
    """Fetch URL content with retries."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            content = resp.read()
            # Handle gzip compression
            if url.endswith(".gz"):
                content = gzip.decompress(content)
            return content
    except URLError as e:
        print(f"[!] Error fetching {url}: {e}")
        return b""


def parse_xmltv(content: bytes) -> ET.Element | None:
    """Parse XMLTV content safely."""
    if not content:
        return None
    try:
        return ET.fromstring(content)
    except ET.ParseError as e:
        print(f"[!] Error parsing XML: {e}")
        return None


def merge_epg_sources() -> ET.Element:
    """Merge multiple EPG sources into a single XML document."""
    # Create root element
    root = ET.Element("tv")
    root.set("generator-info-name", "rdb-tivimate-merged-epg")
    root.set("generated-at", datetime.utcnow().isoformat() + "Z")

    # Track which channel IDs we've seen
    seen_channels: set[str] = set()
    seen_programs: set[tuple[str, str]] = set()  # (channel_id, start_time)

    total_channels = 0
    total_programs = 0
    source_stats: dict[str, dict[str, int]] = {}

    for source_name, url in EPG_SOURCES:
        print(f"[*] Fetching {source_name} EPG from {url}...")
        content = fetch(url)
        epg_root = parse_xmltv(content)

        if epg_root is None:
            print(f"[!] Failed to parse {source_name} EPG")
            source_stats[source_name] = {"channels": 0, "programs": 0}
            continue

        channels_added = 0
        programs_added = 0

        # Extract channels
        for channel in epg_root.findall("channel"):
            channel_id = channel.get("id")
            if not channel_id or channel_id in seen_channels:
                continue

            seen_channels.add(channel_id)
            # Deep copy the channel element
            new_channel = ET.fromstring(ET.tostring(channel))
            new_channel.set("source", source_name)
            root.append(new_channel)
            channels_added += 1
            total_channels += 1

        # Extract programs
        for program in epg_root.findall("programme"):
            channel_id = program.get("channel")
            start_time = program.get("start")

            if not channel_id or not start_time:
                continue

            # Skip if we've seen this exact program before
            prog_key = (channel_id, start_time)
            if prog_key in seen_programs:
                continue

            seen_programs.add(prog_key)
            # Deep copy the program element
            new_program = ET.fromstring(ET.tostring(program))
            new_program.set("source", source_name)
            root.append(new_program)
            programs_added += 1
            total_programs += 1

        source_stats[source_name] = {
            "channels": channels_added,
            "programs": programs_added,
        }
        print(
            f"  ✓ Added {channels_added} channels, {programs_added} programs from {source_name}"
        )

    return root, total_channels, total_programs, source_stats


def main() -> None:
    print("[*] Merging EPG sources...")
    root, total_channels, total_programs, source_stats = merge_epg_sources()

    # Create tree and write to file
    tree = ET.ElementTree(root)
    ET.indent(tree, space="  ")  # Pretty print (Python 3.9+)

    tree.write(OUT, encoding="utf-8", xml_declaration=True)

    print(f"\n[SUCCESS] Wrote {OUT}")
    print(f"  Total channels: {total_channels}")
    print(f"  Total programs: {total_programs}")
    print("\nDetails by source:")
    for source_name, stats in source_stats.items():
        print(
            f"  - {source_name}: {stats['channels']} channels, {stats['programs']} programs"
        )


if __name__ == "__main__":
    main()
