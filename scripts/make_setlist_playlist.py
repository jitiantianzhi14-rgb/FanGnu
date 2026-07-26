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
  py scripts/make_setlist_playlist.py 2026.02.21
  py scripts/make_setlist_playlist.py 2016.09.02 --srvvinci
  py scripts/make_setlist_playlist.py 2026.02.21 --public
  py scripts/make_setlist_playlist.py --all
  py scripts/make_setlist_playlist.py --all --srvvinci
  py scripts/make_setlist_playlist.py --refresh --dates 2024.01.13,2024.01.14

--all を付けると、そのファイル（kinggnu-live.json または --srvvinci指定で
srvvinci-live.json）の全公演のうち、セットリストがあって
まだ spotifyPlaylist が登録されていない公演をまとめて処理します。

--refresh を付けると、新規作成の代わりに既存の spotifyPlaylist の中身を
最新のセットリストで置き換えます（セットリスト修正後の同期用）。
--dates でカンマ区切りの複数公演日をまとめて指定できます（省略時は
date引数の1件のみ）。

作成したプレイリストのURLは、その場でライブJSONファイルに
"spotifyPlaylist" として書き込みます（元のファイルの整形はできるだけ
崩さないよう、行単位のテキスト差し替えで追記します）。
"""

import argparse
import json
import re
import sys
import time
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


def spotify_ref(value):
    """discography.jsonの"spotify"欄からSpotifyの参照を取り出す。
    トラック直リンクなら("track", id)、シングルなどアルバム単位のリンクなら
    ("album", id)を返す。曲IDだけが入っている場合はトラック扱いにする。
    """
    if not value:
        return None
    m = re.search(r"open\.spotify\.com/(?:intl-[a-z]{2}/)?(track|album)/([a-zA-Z0-9]+)", value)
    if m:
        return (m.group(1), m.group(2))
    if re.fullmatch(r"[a-zA-Z0-9]+", value):
        return ("track", value)
    return None


def build_song_index(kg_disco, sv_disco):
    index = {}

    def add(title, ref):
        key = normalize_title(title or "")
        if key and ref and key not in index:
            index[key] = ref

    for item in kg_disco.get("items", []):
        add(item.get("title"), spotify_ref(item.get("spotify")))
        coupling = item.get("coupling")
        if coupling:
            add(coupling.get("title"), spotify_ref(coupling.get("spotify")))
    for album in kg_disco.get("albums", []):
        for t in album.get("tracks", []):
            add(t.get("title"), spotify_ref(t.get("spotify")))

    for group in sv_disco.get("groups", []):
        flat_items = [d for d in group.get("demos", []) if not d.get("tracks")] + \
                     [d for d in group.get("singles", []) if not d.get("tracks")]
        for d in flat_items:
            add(d.get("title"), spotify_ref(d.get("spotify")))

        collections = [d for d in group.get("demos", []) if d.get("tracks")] + \
                      [d for d in group.get("singles", []) if d.get("tracks")] + \
                      group.get("albums", [])
        for coll in collections:
            for t in coll.get("tracks", []):
                add(t.get("title"), spotify_ref(t.get("spotify")))

    return index


def resolve_track_id(sp, ref, album_cache):
    """("track", id) はそのまま、("album", id) はアルバムの1曲目のトラックIDに解決する。"""
    kind, ref_id = ref
    if kind == "track":
        return ref_id
    if ref_id in album_cache:
        return album_cache[ref_id]
    tracks = sp.album_tracks(ref_id, limit=1).get("items") or []
    track_id = tracks[0]["id"] if tracks else None
    album_cache[ref_id] = track_id
    return track_id


def load_json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def insert_spotify_playlist_field(raw_text, date, venue, url):
    """live.jsonの生テキストに対し、該当公演の "status": "..." の直後に
    "spotifyPlaylist" フィールドを差し込む。整形を壊さないための力技。
    見つからなければ (raw_text, False) を返す。
    """
    anchor = f'"date": "{date}", "venue": "{venue}"'
    idx = raw_text.find(anchor)
    if idx == -1:
        return raw_text, False
    status_match = re.search(r'"status":\s*"[^"]*"', raw_text[idx:idx + 2000])
    if not status_match:
        return raw_text, False
    insert_pos = idx + status_match.end()
    escaped_url = url.replace('"', '\\"')
    insertion = f', "spotifyPlaylist": "{escaped_url}"'
    return raw_text[:insert_pos] + insertion + raw_text[insert_pos:], True


def resolve_setlist_tracks(sp, setlist, song_index, album_cache):
    refs = []
    missing = []
    for song in setlist:
        ref = song_index.get(normalize_title(song))
        if ref:
            refs.append(ref)
        else:
            missing.append(song)

    track_ids = []
    for ref in refs:
        track_id = resolve_track_id(sp, ref, album_cache)
        if track_id:
            track_ids.append(track_id)
        else:
            missing.append("(album resolve failed)")

    return track_ids, missing


def create_playlist(sp, tour_name, date, venue, setlist, song_index, album_cache, public):
    track_ids, missing = resolve_setlist_tracks(sp, setlist, song_index, album_cache)

    if not track_ids:
        return None, len(setlist), 0, missing

    playlist_name = f"{tour_name} {date} {venue}".strip()
    playlist = sp._post(
        "me/playlists",
        payload={
            "name": playlist_name,
            "public": public,
            "description": f"FanGNU setlist playlist - {date} {venue}",
        },
    )
    uris = [f"spotify:track:{tid}" for tid in track_ids]
    for i in range(0, len(uris), 100):
        sp.playlist_add_items(playlist["id"], uris[i:i + 100])

    return playlist["external_urls"]["spotify"], len(setlist), len(track_ids), missing


def main():
    parser = argparse.ArgumentParser(description="公演のセットリストからSpotifyプレイリストを作成します。")
    parser.add_argument("date", nargs="?", help="公演日（例: 2026.02.21）。--all指定時は不要")
    parser.add_argument("--srvvinci", action="store_true", help="srvvinci-live.json から探す（指定なしはkinggnu-live.json）")
    parser.add_argument("--public", action="store_true", help="プレイリストを公開設定にする（デフォルトは非公開）")
    parser.add_argument("--all", action="store_true", help="spotifyPlaylist未登録の全公演をまとめて処理する")
    parser.add_argument("--refresh", action="store_true", help="既存のプレイリストを新規作成せず、最新のセットリストで曲を置き換える")
    parser.add_argument("--dates", help="カンマ区切りの複数公演日（--refreshと併用。例: 2024.01.13,2024.01.14）")
    args = parser.parse_args()

    if not args.all and not args.date and not args.dates:
        parser.error("date を指定するか、--all か --dates を付けてください。")

    live_path = DATA_DIR / ("srvvinci-live.json" if args.srvvinci else "kinggnu-live.json")
    kg_disco = load_json(DATA_DIR / "kinggnu-discography.json")
    sv_disco = load_json(DATA_DIR / "srvvinci-discography.json")
    live_data = load_json(live_path)
    song_index = build_song_index(kg_disco, sv_disco)

    auth_manager = SpotifyOAuth(scope=SCOPE)
    sp = spotipy.Spotify(auth_manager=auth_manager)
    sp.current_user()  # 初回ログインを済ませておく
    album_cache = {}

    if args.refresh:
        dates = [d.strip() for d in args.dates.split(",")] if args.dates else [args.date]
        refreshed = 0
        failed = 0
        for d in dates:
            tour, show = None, None
            for t in live_data.get("tours", []):
                for s in t.get("shows", []):
                    if s.get("date") == d:
                        tour, show = t, s
                        break
                if show:
                    break

            if not show:
                print(f"[{d}] 公演が見つかりません")
                failed += 1
                continue

            playlist_url = show.get("spotifyPlaylist")
            m = re.search(r"playlist/([a-zA-Z0-9]+)", playlist_url or "")
            if not m:
                print(f"[{d}] spotifyPlaylistが未登録、またはURLが不正です")
                failed += 1
                continue
            playlist_id = m.group(1)

            setlist = show.get("setlist") or []
            track_ids, missing = resolve_setlist_tracks(sp, setlist, song_index, album_cache)
            if not track_ids:
                print(f"[{d}] 曲が見つかりませんでした")
                failed += 1
                continue

            uris = [f"spotify:track:{tid}" for tid in track_ids]
            sp.playlist_replace_items(playlist_id, uris[:100])
            for i in range(100, len(uris), 100):
                sp.playlist_add_items(playlist_id, uris[i:i + 100])

            print(f"[{d}] {show.get('venue', '')}: {len(track_ids)}/{len(setlist)}曲で更新しました -> {playlist_url}")
            if missing:
                print(f"  見つからなかった曲: {', '.join(missing)}")
            refreshed += 1
            time.sleep(0.3)

        print()
        print(f"更新: {refreshed}件 / 失敗: {failed}件")
        return

    if args.all:
        raw_text = live_path.read_text(encoding="utf-8")
        created = 0
        skipped_existing = 0
        skipped_no_setlist = 0
        failed = 0

        for tour in live_data.get("tours", []):
            for show in tour.get("shows", []):
                date = show.get("date")
                venue = show.get("venue", "")
                if show.get("spotifyPlaylist"):
                    skipped_existing += 1
                    continue
                setlist = show.get("setlist") or []
                if not setlist:
                    skipped_no_setlist += 1
                    continue

                print(f"[{date}] {venue}（{tour.get('name', '')}）...", end=" ")
                try:
                    url, total, matched, missing = create_playlist(
                        sp, tour.get("name", ""), date, venue, setlist, song_index, album_cache, args.public
                    )
                except Exception as e:
                    print(f"エラー: {e}")
                    failed += 1
                    continue

                if not url:
                    print(f"曲が見つからずスキップ ({matched}/{total})")
                    continue

                print(f"{matched}/{total}曲 -> {url}")
                raw_text, ok = insert_spotify_playlist_field(raw_text, date, venue, url)
                if ok:
                    live_path.write_text(raw_text, encoding="utf-8")
                    created += 1
                else:
                    print(f"  [警告] JSONへの書き込み位置が見つかりませんでした（{date} {venue}）。手動で追加してください。")

                time.sleep(0.3)

        print()
        print(f"作成: {created}件 / 既存スキップ: {skipped_existing}件 / セトリなしスキップ: {skipped_no_setlist}件 / 失敗: {failed}件")
        return

    tour, show = None, None
    for t in live_data.get("tours", []):
        for s in t.get("shows", []):
            if s.get("date") == args.date:
                tour, show = t, s
                break
        if show:
            break

    if not show:
        print(f"{live_path.name} に日付 {args.date} の公演が見つかりませんでした。")
        sys.exit(1)

    setlist = show.get("setlist") or []
    if not setlist:
        print("この公演にはセットリスト情報がありません。")
        sys.exit(1)

    url, total, matched, missing = create_playlist(
        sp, tour.get("name", ""), args.date, show.get("venue", ""), setlist, song_index, album_cache, args.public
    )

    print(f"公演: {args.date} {show.get('venue', '')}（{tour.get('name', '')}）")
    print(f"セットリスト {total}曲中 {matched}曲がSpotifyで見つかりました。")
    if missing:
        print("見つからなかった曲:")
        for m in missing:
            print(f"  - {m}")

    if not url:
        print("Spotifyで見つかった曲が1曲もないため、プレイリストは作成しません。")
        sys.exit(1)

    print()
    print("プレイリストを作成しました:")
    print(url)

    raw_text = live_path.read_text(encoding="utf-8")
    raw_text, ok = insert_spotify_playlist_field(raw_text, args.date, show.get("venue", ""), url)
    if ok:
        live_path.write_text(raw_text, encoding="utf-8")
        print(f"{live_path.name} に spotifyPlaylist を登録しました。")
    else:
        print(f"[警告] {live_path.name} への自動書き込みに失敗しました。手動で追加してください。")


if __name__ == "__main__":
    main()
