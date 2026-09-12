# -*- coding: utf-8 -*-
"""
Daily YouTube view-count tracker.

Reads every video ID referenced in the discography JSON files (the "yt" and
"yt2" fields), fetches current view counts via the YouTube Data API v3, and
appends today's snapshot to a year-partitioned history file under
data/yt-views/<year>.json. Splitting by year keeps each file small so the
site never has to load more than one year's worth of data at a time.

Requires the YOUTUBE_API_KEY environment variable (a free YouTube Data API v3
key). Safe to re-run multiple times on the same day: it updates today's entry
in place instead of duplicating it.
"""
import json
import os
import re
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
VIEWS_DIR = os.path.join(DATA_DIR, "yt-views")

API_KEY = os.environ.get("YOUTUBE_API_KEY")


def collect_video_ids():
    ids = set()
    for name in ("kinggnu-discography.json", "srvvinci-discography.json"):
        path = os.path.join(DATA_DIR, name)
        with open(path, encoding="utf-8") as f:
            text = f.read()
        for m in re.finditer(r'"yt2?"\s*:\s*"([a-zA-Z0-9_-]{6,15})"', text):
            ids.add(m.group(1))
    return sorted(ids)


def fetch_view_counts(video_ids):
    """Returns {video_id: view_count_int_or_None}."""
    results = {}
    for i in range(0, len(video_ids), 50):
        batch = video_ids[i:i + 50]
        params = urllib.parse.urlencode({
            "part": "statistics",
            "id": ",".join(batch),
            "key": API_KEY,
        })
        url = f"https://www.googleapis.com/youtube/v3/videos?{params}"
        with urllib.request.urlopen(url, timeout=30) as res:
            data = json.load(res)
        found = {}
        for item in data.get("items", []):
            vid = item["id"]
            count = item.get("statistics", {}).get("viewCount")
            found[vid] = int(count) if count is not None else None
        for vid in batch:
            results[vid] = found.get(vid)  # None if private/deleted/not found
    return results


def today_jst():
    # Record against Japan Standard Time, since the audience/fanbase is Japan-based.
    return (datetime.now(timezone.utc) + timedelta(hours=9)).strftime("%Y-%m-%d")


def main():
    if not API_KEY:
        raise SystemExit("FATAL: YOUTUBE_API_KEY environment variable is not set")

    video_ids = collect_video_ids()
    print(f"Tracking {len(video_ids)} video IDs")

    counts = fetch_view_counts(video_ids)
    missing = [vid for vid, c in counts.items() if c is None]
    if missing:
        print(f"WARNING: no stats returned for {len(missing)} video(s): {missing}")

    date = today_jst()
    year = date[:4]
    os.makedirs(VIEWS_DIR, exist_ok=True)
    path = os.path.join(VIEWS_DIR, f"{year}.json")

    if os.path.isfile(path):
        with open(path, encoding="utf-8") as f:
            history = json.load(f)
    else:
        history = {"dates": [], "views": {}}

    if date in history["dates"]:
        idx = history["dates"].index(date)
        print(f"{date} already recorded, updating in place")
    else:
        history["dates"].append(date)
        idx = len(history["dates"]) - 1

    for vid in video_ids:
        arr = history["views"].setdefault(vid, [])
        while len(arr) <= idx:
            arr.append(None)
        arr[idx] = counts.get(vid)

    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, separators=(",", ":"))

    print(f"Wrote {path} ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    main()
