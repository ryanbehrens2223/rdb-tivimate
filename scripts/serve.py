#!/usr/bin/env python3
"""Serve playlist.m3u from this repo so TiviMate can load it from your Mac.

The GitHub repo can stay private. TiviMate talks to this machine over
your LAN or Tailscale, not to raw.githubusercontent.com.
"""

from __future__ import annotations

import argparse
import socket
import subprocess
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PORT = 8080
DEFAULT_BIND = "0.0.0.0"


class PlaylistHandler(SimpleHTTPRequestHandler):
    extensions_map = {
        **SimpleHTTPRequestHandler.extensions_map,
        ".m3u": "application/vnd.apple.mpegurl",
        ".m3u8": "application/vnd.apple.mpegurl",
        ".xml": "application/xml",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:
        super().log_message(format, *args)


def lan_ipv4() -> str | None:
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.connect(("8.8.8.8", 80))
        ip = sock.getsockname()[0]
        sock.close()
        if ip and not ip.startswith("127."):
            return ip
    except OSError:
        pass
    return None


def tailscale_ipv4() -> str | None:
    try:
        result = subprocess.run(
            ["tailscale", "ip", "-4"],
            check=False,
            capture_output=True,
            text=True,
            timeout=5,
        )
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return None
    if result.returncode != 0:
        return None
    ip = result.stdout.strip().splitlines()[0] if result.stdout.strip() else ""
    return ip or None


def playlist_urls(port: int) -> list[tuple[str, str]]:
    urls: list[tuple[str, str]] = []
    lan = lan_ipv4()
    if lan:
        urls.append(("Same Wi-Fi", f"http://{lan}:{port}/playlist.m3u"))
    ts = tailscale_ipv4()
    if ts:
        urls.append(("Tailscale", f"http://{ts}:{port}/playlist.m3u"))
    urls.append(("This Mac only", f"http://127.0.0.1:{port}/playlist.m3u"))
    return urls


def print_urls(port: int) -> None:
    print(f"Serving {ROOT}")
    print("Paste one of these into TiviMate → Playlists → Add playlist → M3U:")
    print()
    for label, url in playlist_urls(port):
        print(f"  {label}: {url}")
    print()
    if not tailscale_ipv4():
        print("Tailscale IP not found. Install Tailscale on this Mac and the Firestick")
        print("if you want the playlist away from home.")
        print()


def main() -> None:
    parser = argparse.ArgumentParser(description="Serve the TiviMate playlist from this Mac.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--bind", default=DEFAULT_BIND)
    parser.add_argument("--urls", action="store_true", help="Print TiviMate URLs and exit")
    args = parser.parse_args()

    if args.urls:
        print_urls(args.port)
        return

    print_urls(args.port)
    server = ThreadingHTTPServer((args.bind, args.port), PlaylistHandler)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
        server.shutdown()


if __name__ == "__main__":
    main()
