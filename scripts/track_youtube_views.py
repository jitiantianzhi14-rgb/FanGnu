# -*- coding: utf-8 -*-
"""
Daily YouTube view-count tracker.

Reads the hand-maintained list of video IDs in data/yt-tracked-videos.json
(add/remove entries there to control exactly what gets tracked), fetches
current view counts via the YouTube Data API v3, and appends today's
snapshot to a year-partitioned history file under data/yt-views/<year>.json.
Splitting by year keeps each file small so the site never has to load more
than one year's worth of data at a time.

Requires the YOUTUBE_API_KEY environment variable (a free YouTube Data API v3
key). Safe to re-run multiple times on the same day: it updates today's entry
in place instead of duplicating it.
"""
import json
import os
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
VIEWS_DIR = os.path.join(DATA_DIR, "yt-views")
TRACKED_LIST_PATH = os.path.join(DATA_DIR, "yt-tracked-videos.json")

API_KEY = os.environ.get("YOUTUBE_API_KEY")


def collect_video_ids():
    with open(TRACKED_LIST_PATH, encoding="utf-8") as f:
        entries = json.load(f)
    return [e["id"] for e in entries]


def build_title_map():
    """id -> human-readable label, for annotating the history file."""
    with open(TRACKED_LIST_PATH, encoding="utf-8") as f:
        return {e["id"]: e["label"] for e in json.load(f)}


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


def format_history(history, titles=None):
    """Serialize with one video per line, label right next to its counts, so
    a human can tell what a line is about without cross-referencing anything.

    Each video's value is {"label": "...", "counts": [...]} instead of a bare
    array. The counts array itself stays compact (no per-number
    indentation) to keep file size in check.
    """
    titles = titles or {}
    dates_json = json.dumps(history["dates"], ensure_ascii=False, separators=(",", ":"))

    view_lines = []
    for vid, arr in history["views"].items():
        vid_json = json.dumps(vid, ensure_ascii=False)
        label_json = json.dumps(titles.get(vid, vid), ensure_ascii=False)
        arr_json = json.dumps(arr, ensure_ascii=False, separators=(",", ":"))
        view_lines.append(f'    {vid_json}:{{"label":{label_json},"counts":{arr_json}}}')
    views_body = ",\n".join(view_lines)
    return (
        "{\n"
        f'  "dates":{dates_json},\n'
        '  "views":{\n'
        f"{views_body}\n"
        "  }\n"
        "}\n"
    )


def main():
    if not API_KEY:
        raise SystemExit("FATAL: YOUTUBE_API_KEY environment variable is not set")

    video_ids = collect_video_ids()
    print(f"Tracking {len(video_ids)} video IDs from {TRACKED_LIST_PATH}")

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
        # Normalize back to plain {id: [counts]} for in-memory use, regardless
        # of whether the file on disk has the old bare-array shape or the
        # current {"label", "counts"} shape.
        history["views"] = {
            vid: (val["counts"] if isinstance(val, dict) else val)
            for vid, val in history["views"].items()
        }
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

    # Drop history for any video no longer in the tracked list, so the file
    # only ever holds data for what's currently being tracked.
    dropped = set(history["views"]) - set(video_ids)
    if dropped:
        print(f"Dropping {len(dropped)} untracked video(s) from history: {sorted(dropped)}")
        for vid in dropped:
            del history["views"][vid]

    titles = build_title_map()
    with open(path, "w", encoding="utf-8") as f:
        f.write(format_history(history, titles))

    print(f"Wrote {path} ({os.path.getsize(path)} bytes)")


if __name__ == "__main__":
    main()
