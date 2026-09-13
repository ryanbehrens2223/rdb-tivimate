# rdb-tivimate

US TiviMate playlist hosted on GitHub. Built from the public [iptv-org](https://github.com/iptv-org/iptv) US catalog, then filtered so Firestick users in the US are not pointed at geo-blocked or anonymous pay-TV restreams.

## What you get

`playlist.m3u` is a single US list with **every public iptv-org category** that still has a usable official-style host: news, movies, series, sports, kids, documentary, entertainment, legislative, music, and the rest.

Sports are grouped first. After a refresh this file has about **1,295 channels**, including about **47 sports-tagged** channels such as:

- CBS Sports Golazo / CBS Sports HQ
- beIN SPORTS XTRA
- FIFA+ United States
- Stadium, SportsGrid, Red Bull TV
- Pluto sports (NFL Channel highlights, MLB highlights, Bellator, PBR, Competition)
- ACCDN, NHRA, Overtime, Rally TV, Tennis Channel FAST feeds, TVS sports

## What you do not get

This is **not** a cable sports package.

| Wanted | In this playlist? |
| --- | --- |
| ESPN, ESPNU, Fox Sports 1/2, NFL Network, NBA TV, regional NBC Sports | No. Those are pay-TV. The raw iptv-org US file has lookalikes on random IP servers; those were removed. |
| Live NFL / NBA / MLB / NHL / college games as on cable | No. Free channels here are mostly highlights, studio shows, FAST, and niche sports. |
| Sky Sports, Sony Sports, foreign league feeds | No. Those fail or geo-block from the US. |
| HBO, Showtime, Cinemax, Disney Channel pay feeds | No. Same panel-host filter. |
| YouTube subscriptions | No. Use the YouTube app or SmartTube. |

Live national games without blackouts still need a licensed app you already pay for (YouTube TV, Hulu + Live, Fubo, Sling, league passes, and the subscriptions you already have).

## Mac mini setup

TiviMate cannot read a private GitHub repo. The mini serves `playlist.m3u` on your Wi-Fi. Away from home, only devices you add to your Tailscale network can reach it. Do not port-forward 8080 on the router, and do not turn on Tailscale Funnel.

Your mini’s Tailscale IP is already `100.84.247.124` (`ryans-mac-mini`).

### 1. Put this folder on the mini

On the Mac mini, clone the private repo (or copy this folder over):

```bash
git clone https://github.com/ryanbehrens2223/rdb-tivimate.git
cd rdb-tivimate
```

If the folder is already there, `git pull` so you have the latest scripts.

### 2. Keep the mini awake

System Settings → Energy (or Battery → Options):

- Prevent automatic sleeping when the display is off
- Wake for network access
- Start up automatically after a power failure

Sign in at the desktop after reboot so the login service can run.

### 3. Install the server and daily refresh

```bash
chmod +x scripts/*.sh scripts/*.py
./scripts/install-macos-service.sh
```

That does three things:

- Serves the playlist on port 8080 at login and keeps it running
- Rebuilds `playlist.m3u` every day at 5:00 AM local time
- Runs one refresh immediately

Allow incoming connections for Python if macOS Firewall asks.

Different refresh time (example: 4:30 AM):

```bash
REFRESH_HOUR=4 REFRESH_MINUTE=30 ./scripts/install-macos-service.sh
```

### 4. Same Wi-Fi (Firestick at home)

On the mini, print the URLs:

```bash
python3 scripts/serve.py --urls
```

On the Firestick: TiviMate → Settings → Playlists → Add playlist → M3U, paste the **Same Wi-Fi** URL:

`http://MINI-LAN-IP:8080/playlist.m3u`

EPG sources are already in the playlist header.

### 5. External access for people you choose

This is Tailscale, not the open internet.

1. Keep Tailscale running on the Mac mini.
2. Install Tailscale on each device that should connect (Firestick, a friend’s phone, another TV).
3. Approve that device in the [Tailscale admin console](https://login.tailscale.com/admin/machines). Anyone not on your tailnet cannot load the playlist.
4. On those devices, use:

   `http://100.84.247.124:8080/playlist.m3u`

To remove access later, disable or delete that machine in the Tailscale admin console.

Optional HTTPS name on your tailnet only (run on the mini after the server is up):

```bash
tailscale serve --bg 8080
```

Use the `https://<machine>.<tailnet>.ts.net/playlist.m3u` URL it prints. Do not enable Funnel.

### 6. Check that it is working

On the mini:

```bash
curl -I http://127.0.0.1:8080/playlist.m3u
tail -n 20 ~/Library/Logs/rdb-tivimate.log
tail -n 20 ~/Library/Logs/rdb-tivimate-refresh.log
```

You want HTTP 200. In TiviMate, refresh the playlist after the first add.

### Automated refresh

`com.rdb.tivimate-refresh` runs `scripts/refresh_playlist.py` once a day. That re-downloads the public US catalog, applies the same filters, and overwrites `playlist.m3u`. TiviMate picks it up on its next playlist refresh.

Manual run if you want it now:

```bash
python3 scripts/refresh_playlist.py
```

Logs: `~/Library/Logs/rdb-tivimate-refresh.log`

Remove the server and the daily job:

```bash
./scripts/uninstall-macos-service.sh
```

`git push` from the mini is only a backup of the private repo. TiviMate never uses GitHub.

## Files

| File | Purpose |
| --- | --- |
| `playlist.m3u` | Curated US public playlist for TiviMate |
| `epg.xml` | Placeholder only; TiviMate uses the EPG URLs in the M3U header |
| `scripts/serve.py` | Serves the playlist from this Mac |
| `scripts/install-macos-service.sh` | Starts the server at login and keeps it running |
| `scripts/uninstall-macos-service.sh` | Removes that login service |
| `scripts/refresh_playlist.py` | Regenerates `playlist.m3u` from iptv-org |
