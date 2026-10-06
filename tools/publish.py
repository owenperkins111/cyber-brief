#!/usr/bin/env python3
"""Add an episode to the podcast site directory and rebuild feed.xml.

Usage: publish.py SITE_DIR EPISODE.mp3 --date YYYY-MM-DD --title "..." --summary "..." --base-url URL
Keeps the newest KEEP episodes; older MP3s are removed from SITE_DIR.
Episode metadata lives in SITE_DIR/episodes.json.
"""
import argparse, json, os, shutil, subprocess
from datetime import datetime, timezone
from email.utils import format_datetime
from xml.sax.saxutils import escape

KEEP = 14
SHOW_TITLE = "Cyber Brief"
SHOW_DESC = ("A short daily cyber security briefing for defenders: actively exploited "
             "vulnerabilities, patch priorities, breaches and threat actor news. "
             "Generated each morning by Claude from public reporting.")


def duration(path):
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                          "-of", "default=nw=1:nk=1", path], capture_output=True, text=True, check=True)
    return int(float(out.stdout.strip()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("site")
    ap.add_argument("mp3")
    ap.add_argument("--date", required=True)
    ap.add_argument("--title", required=True)
    ap.add_argument("--summary", required=True)
    ap.add_argument("--base-url", required=True)
    a = ap.parse_args()
    base = a.base_url.rstrip("/")

    os.makedirs(os.path.join(a.site, "audio"), exist_ok=True)
    meta_path = os.path.join(a.site, "episodes.json")
    eps = json.load(open(meta_path)) if os.path.exists(meta_path) else []

    fname = f"{a.date}.mp3"
    dest = os.path.join(a.site, "audio", fname)
    shutil.copyfile(a.mp3, dest)
    pub = datetime.now(timezone.utc).replace(microsecond=0)

    eps = [e for e in eps if e["file"] != fname]
    eps.append({"file": fname, "date": a.date, "title": a.title, "summary": a.summary,
                "pub": format_datetime(pub), "bytes": os.path.getsize(dest),
                "secs": duration(dest)})
    eps.sort(key=lambda e: e["date"], reverse=True)
    for old in eps[KEEP:]:
        p = os.path.join(a.site, "audio", old["file"])
        if os.path.exists(p):
            os.remove(p)
    eps = eps[:KEEP]
    json.dump(eps, open(meta_path, "w"), indent=1)

    items = []
    for e in eps:
        m, s = divmod(e["secs"], 60)
        items.append(f"""  <item>
   <title>{escape(e['title'])}</title>
   <description>{escape(e['summary'])}</description>
   <itunes:summary>{escape(e['summary'])}</itunes:summary>
   <enclosure url="{base}/audio/{e['file']}" length="{e['bytes']}" type="audio/mpeg"/>
   <guid isPermaLink="false">cyber-brief-{e['date']}</guid>
   <pubDate>{e['pub']}</pubDate>
   <itunes:duration>{m}:{s:02d}</itunes:duration>
   <itunes:explicit>false</itunes:explicit>
  </item>""")
    feed = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0" xmlns:itunes="http://www.itunes.com/dtds/podcast-1.0.dtd" xmlns:atom="http://www.w3.org/2005/Atom">
 <channel>
  <title>{SHOW_TITLE}</title>
  <link>{base}/</link>
  <atom:link href="{base}/feed.xml" rel="self" type="application/rss+xml"/>
  <language>en-gb</language>
  <description>{escape(SHOW_DESC)}</description>
  <itunes:summary>{escape(SHOW_DESC)}</itunes:summary>
  <itunes:author>Cyber Brief</itunes:author>
  <itunes:image href="{base}/cover.png"/>
  <itunes:category text="Technology"/>
  <itunes:explicit>false</itunes:explicit>
  <itunes:block>Yes</itunes:block>
  <itunes:type>episodic</itunes:type>
{chr(10).join(items)}
 </channel>
</rss>
"""
    open(os.path.join(a.site, "feed.xml"), "w", encoding="utf-8").write(feed)
    open(os.path.join(a.site, ".nojekyll"), "w").close()
    links = "".join(f'<li><a href="audio/{e["file"]}">{escape(e["title"])}</a></li>' for e in eps)
    open(os.path.join(a.site, "index.html"), "w", encoding="utf-8").write(
        f'<!doctype html><meta charset="utf-8"><meta name="viewport" content="width=device-width">'
        f'<title>{SHOW_TITLE}</title><body style="font-family:system-ui;max-width:640px;margin:2rem auto;padding:0 16px">'
        f'<h1>{SHOW_TITLE}</h1><p>Podcast feed: <code>{base}/feed.xml</code></p><ul>{links}</ul>')
    print(f"feed updated: {len(eps)} episodes")


if __name__ == "__main__":
    main()
