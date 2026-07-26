#!/usr/bin/env python3
"""
FanGNU: 公演のセットリスト順にSpotifyプレイリストを自動作成するスクリプト。
サイト本体には含まれない、個人用の裏方ツール。

セットアップ（初回のみ）:
  1. pip install spotipy
  2. https://developer.spotify.com/dashboard でアプリを作成
     - Redirect URI に http://127.0.0.1:8888/callback を登録
     - Client ID / Client Secret を控える
  3. 環境変数を設定
     Windows PowerShellの場合:
       $env:SPOTIPY_CLIENT_ID = "xxxx"
       $env:SPOTIPY_CLIENT_SECRET = "xxxx"
       $env:SPOTIPY_REDIRECT_URI = "http://127.0.0.1:8888/callback"

使い方:
  python scripts/make_setlist_playlist.py 2026.02.21
  python scripts/make_setlist_playlist.py 2016.09.02 --srvvinci
  python scripts/make_setlist_playlist.py 2026.02.21 --public

初回実行時にブラウザでSpotifyのログイン・認可画面が開きます。
実行結果としてプレイリストのURLが表示されるので、それを教えてもらえれば
live-show.htmlに埋め込むための "spotifyPlaylist" フィールドを追加します。
"""

import argparse
import json
import re
import sys
from pathlib import Path

try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    print("spotipy がインストールされていません。`pip install spotipy` を実行してください。")
    sys.exit(1)

DATA_DIR = Path(__file__).resolve().parent.parent / "contents" / "data"
SCOPE = "playlist-modify-public playlist-modify-private"


def normalize_title(title):
    title = re.sub(r"\s*★.*$", "", title)
    title = re.sub(r"[（(][^）)]*[）)]\s*$", "", title)
    return title.strip()


def spotify_track_id(value):
    if not value:
        return None
    m = re.search(r"open\.spotify\.com/(?:intl-[a-z]{2}/)?track/([a-zA-Z0-9]+)", value)
    if m:
        return m.group(1)
    if re.fullmatch(r"[a-zA-Z0-9]+", value):
        return value
    return None


def build_song_index(kg_disco, sv_disco):
    index = {}

    def add(title, track_id):
        key = normalize_title(title or "")
        if key and track_id and key not in index:
            index[key] = track_id

    for item in kg_disco.get("items", []):
        add(item.get("title"), spotify_track_id(item.get("spotify")))
        coupling = item.get("coupling")
        if coupling:
            add(coupling.get("title"), spotify_track_id(coupling.get("spotify")))
    for album in kg_disco.get("albums", []):
        for t in album.get("tracks", []):
            add(t.get("title"), spotify_track_id(t.get("spotify")))

    for group in sv_disco.get("groups", []):
        flat_items = [d for d in group.get("demos", []) if not d.get("tracks")] + \
                     [d for d in group.get("singles", []) if not d.get("tracks")]
        for d in flat_items:
            add(d.get("title"), spotify_track_id(d.get("spotify")))

        collections = [d for d in group.get("demos", []) if d.get("tracks")] + \
                      [d for d in group.get("singles", []) if d.get("tracks")] + \
                      group.get("albums", [])
        for coll in collections:
            for t in coll.get("tracks", []):
                add(t.get("title"), spotify_track_id(t.get("spotify")))

    return index


def find_show(date, live_data):
    for tour in live_data.get("tours", []):
        for show in tour.get("shows", []):
            if show.get("date") == date:
                return tour, show
    return None, None


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def main():
    parser = argparse.ArgumentParser(description="公演のセットリストからSpotifyプレイリストを作成します。")
    parser.add_argument("date", help="公演日（例: 2026.02.21）")
    parser.add_argument("--srvvinci", action="store_true", help="srvvinci-live.json から探す（指定なしはkinggnu-live.json）")
    parser.add_argument("--public", action="store_true", help="プレイリストを公開設定にする（デフォルトは非公開）")
    args = parser.parse_args()

    live_path = DATA_DIR / ("srvvinci-live.json" if args.srvvinci else "kinggnu-live.json")
    kg_disco = load_json(DATA_DIR / "kinggnu-discography.json")
    sv_disco = load_json(DATA_DIR / "srvvinci-discography.json")
    live_data = load_json(live_path)

    tour, show = find_show(args.date, live_data)
    if not show:
        print(f"{live_path.name} に日付 {args.date} の公演が見つかりませんでした。")
        sys.exit(1)

    setlist = show.get("setlist") or []
    if not setlist:
        print("この公演にはセットリスト情報がありません。")
        sys.exit(1)

    song_index = build_song_index(kg_disco, sv_disco)

    track_ids = []
    missing = []
    for song in setlist:
        track_id = song_index.get(normalize_title(song))
        if track_id:
            track_ids.append(track_id)
        else:
            missing.append(song)

    print(f"公演: {args.date} {show.get('venue', '')}（{tour.get('name', '')}）")
    print(f"セットリスト {len(setlist)}曲中 {len(track_ids)}曲がSpotifyで見つかりました。")
    if missing:
        print("見つからなかった曲:")
        for m in missing:
            print(f"  - {m}")

    if not track_ids:
        print("Spotifyで見つかった曲が1曲もないため、プレイリストは作成しません。")
        sys.exit(1)

    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=SCOPE))
    me = sp.current_user()

    playlist_name = f"{tour.get('name', '')} {args.date} {show.get('venue', '')}".strip()
    playlist = sp.user_playlist_create(
        me["id"],
        playlist_name,
        public=args.public,
        description=f"FanGNU setlist playlist - {args.date} {show.get('venue', '')}",
    )

    uris = [f"spotify:track:{tid}" for tid in track_ids]
    for i in range(0, len(uris), 100):
        sp.playlist_add_items(playlist["id"], uris[i:i + 100])

    print()
    print("プレイリストを作成しました:")
    print(playlist["external_urls"]["spotify"])


if __name__ == "__main__":
    main()
