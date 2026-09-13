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

## TiviMate setup

After this repo is pushed:

1. Open TiviMate → Settings → Playlists → Add playlist → M3U playlist
2. Paste:

   `https://raw.githubusercontent.com/ryanbehrens2223/rdb-tivimate/main/playlist.m3u`

3. EPG sources are already in the playlist header (Pluto US + Samsung TV Plus US). You can also add them under Settings → EPG if a guide is missing.

### Local test (optional)

```bash
cd /path/to/rdb-tivimate
python3 -m http.server 8080
```

- Playlist: `http://YOUR-MAC-IP:8080/playlist.m3u`

## Refresh the channel list

Public stream URLs change. From this repo:

```bash
python3 scripts/refresh_playlist.py
```

That downloads the current US catalog, drops geo-blocked and panel/restream hosts, puts sports first, and overwrites `playlist.m3u`.

## Files

| File | Purpose |
| --- | --- |
| `playlist.m3u` | Curated US public playlist for TiviMate |
| `epg.xml` | Placeholder only; TiviMate uses the EPG URLs in the M3U header |
| `scripts/refresh_playlist.py` | Regenerates `playlist.m3u` from iptv-org |
