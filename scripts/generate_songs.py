# -*- coding: utf-8 -*-
"""
Static page generator for FunGNU song pages.
Reads song/index.html as a template, bakes per-song content, and writes
song/<slug>/index.html for every song found in the discography JSON.
"""
import json
import os
import re

ROOT = r"c:/fanGNU"
TEMPLATE_PATH = os.path.join(ROOT, "scripts", "templates", "song.html")
OUT_BASE = os.path.join(ROOT, "song")

ROOT_TOKEN = "@@ROOT@@"


def load_json(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


def esc_h(s):
    if s is None:
        s = ""
    s = str(s)
    return (
        s.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


LINK_URL_RE = re.compile(r"(\[[^\]]+\]\()(\.\./[^)]+)(\))")


def deepen_relative_links(text):
    """Prepend one extra '../' to internal (non-http) markdown-lite links."""
    if not text:
        return text

    def repl(m):
        return m.group(1) + "../" + m.group(2) + m.group(3)

    return LINK_URL_RE.sub(repl, text)


NORM_STAR_RE = re.compile(r"\s*★.*$")
NORM_PAREN_RE = re.compile(r"[（(][^）)]*[）)]\s*$")


def normalize_title(title):
    t = NORM_STAR_RE.sub("", title or "")
    t = NORM_PAREN_RE.sub("", t)
    return t.strip().lower()


def collect_songs(kg, sv):
    """Yield (slug, song_dict) for every song findable via the old findBySlug logic."""
    seen = set()

    def emit(slug, song):
        if not slug or slug in seen:
            return
        seen.add(slug)
        song["slug"] = slug
        song.setdefault("appleMusic", "")
        yield_list.append((slug, song))

    yield_list = []

    for item in kg.get("items", []):
        if item.get("discs"):
            continue  # video/Blu-ray releases are handled by generate_videos.py, not songs
        slug = item.get("slug")
        if slug:
            album = None
            for a in kg.get("albums", []):
                found = None
                for t in a.get("tracks", []):
                    if t.get("yt") and t.get("yt") == item.get("yt"):
                        found = t
                        break
                if found:
                    album = {"title": a["title"], "num": found["num"]}
                    break
            emit(slug, {
                "isSrvvinci": False, "type": item.get("type"), "title": item.get("title"),
                "liveTitle": item.get("liveTitle", ""), "year": item.get("year"),
                "note": item.get("note"), "extra": item.get("extra"),
                "yt": item.get("yt", ""), "yt2": item.get("yt2", ""),
                "tweets": item.get("tweets", []), "spotify": item.get("spotify", ""),
                "externalVideo": item.get("externalVideo", ""), "hideVideo": bool(item.get("hideVideo")),
                "lyrics": item.get("lyrics", ""), "shorts": item.get("shorts", []),
                "album": album, "isAlbumTrack": False, "albumText": item.get("albumText", ""),
            })
        coupling = item.get("coupling")
        if coupling and coupling.get("slug"):
            c = coupling
            emit(c["slug"], {
                "isSrvvinci": False, "type": item.get("type"), "title": c.get("title"),
                "liveTitle": c.get("liveTitle", ""), "year": item.get("year"),
                "note": c.get("note"), "extra": c.get("extra", ""),
                "yt": c.get("yt", ""), "yt2": c.get("yt2", ""),
                "tweets": c.get("tweets", []), "spotify": c.get("spotify", ""),
                "externalVideo": c.get("externalVideo", ""), "hideVideo": bool(c.get("hideVideo")),
                "lyrics": c.get("lyrics", ""), "shorts": [],
                "album": None, "isAlbumTrack": False, "albumText": "",
            })

    for a in kg.get("albums", []):
        for t in a.get("tracks", []):
            slug = t.get("slug")
            if slug:
                emit(slug, {
                    "isSrvvinci": False, "type": "ALBUM", "title": t.get("title"),
                    "liveTitle": t.get("liveTitle", ""), "year": a.get("year"),
                    "note": t.get("note"), "extra": t.get("extra", ""),
                    "yt": t.get("yt", ""), "yt2": t.get("yt2", ""),
                    "tweets": t.get("tweets", []), "spotify": t.get("spotify", ""),
                    "externalVideo": t.get("externalVideo", ""), "hideVideo": bool(t.get("hideVideo")),
                    "lyrics": t.get("lyrics", ""), "shorts": [],
                    "album": {"title": a["title"], "num": t["num"]}, "isAlbumTrack": True, "albumText": "",
                })

    for group in sv.get("groups", []):
        collections = []
        for d in group.get("demos", []) or []:
            if d.get("tracks"):
                collections.append((d, d.get("type") or "DEMO"))
        for d in group.get("singles", []) or []:
            if d.get("tracks"):
                collections.append((d, d.get("type") or "SINGLE"))
        for a in group.get("albums", []) or []:
            collections.append((a, a.get("type") or "ALBUM"))

        for coll, ctype in collections:
            for t in coll.get("tracks", []):
                slug = t.get("slug")
                if slug:
                    emit(slug, {
                        "isSrvvinci": True, "type": ctype, "title": t.get("title"),
                        "liveTitle": t.get("liveTitle", ""), "year": coll.get("year", ""),
                        "note": t.get("note", ""), "extra": t.get("extra", ""),
                        "yt": t.get("yt", ""), "yt2": t.get("yt2", ""),
                        "tweets": t.get("tweets", []), "spotify": t.get("spotify", ""),
                        "appleMusic": t.get("appleMusic", ""),
                        "externalVideo": t.get("externalVideo", ""), "hideVideo": bool(t.get("hideVideo")),
                        "lyrics": t.get("lyrics", ""), "shorts": [],
                        "album": {"title": coll["title"], "num": t["num"]}, "isAlbumTrack": True, "albumText": "",
                    })

        flat_pools = []
        for d in group.get("demos", []) or []:
            if not d.get("tracks"):
                flat_pools.append((d, d.get("type") or "DEMO"))
        for d in group.get("singles", []) or []:
            if not d.get("tracks"):
                flat_pools.append((d, d.get("type") or "SINGLE"))

        for item, itype in flat_pools:
            slug = item.get("slug")
            if slug:
                emit(slug, {
                    "isSrvvinci": True, "type": itype, "title": item.get("title"),
                    "liveTitle": item.get("liveTitle", ""), "year": item.get("year", ""),
                    "note": item.get("note", ""), "extra": item.get("extra", ""),
                    "yt": item.get("yt", ""), "yt2": item.get("yt2", ""),
                    "tweets": item.get("tweets", []), "spotify": item.get("spotify", ""),
                    "appleMusic": "",
                    "externalVideo": item.get("externalVideo", ""), "hideVideo": bool(item.get("hideVideo")),
                    "lyrics": item.get("lyrics", ""), "album": None, "isAlbumTrack": False,
                })

    return yield_list


def find_live_history(title, live_title, kg_live, sv_live):
    target = live_title or title
    if not target:
        return []
    norm_target = normalize_title(target)
    results = []
    for data, source in ((kg_live, "kinggnu"), (sv_live, "srvvinci")):
        for tour in data.get("tours", []):
            for show in tour.get("shows", []):
                setlist = show.get("setlist") or []
                hit = any(s == target or normalize_title(s) == norm_target for s in setlist)
                if hit:
                    results.append({
                        "date": show.get("date"),
                        "tourName": tour.get("name"),
                        "venue": show.get("venue", ""),
                        "source": source,
                    })
    results.sort(key=lambda r: r["date"], reverse=True)
    return results


def main():
    kg = load_json("kinggnu-discography.json")
    sv = load_json("srvvinci-discography.json")
    kg_live = load_json("kinggnu-live.json")
    sv_live = load_json("srvvinci-live.json")

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    # Fix the one JS line that rebuilds canonical/og:url in the old query-string format.
    template = template.replace(
        "const canonicalUrl = `https://fungnu.com/song/?slug=${encodeURIComponent(slug)}`;",
        "const canonicalUrl = `https://fungnu.com/song/${encodeURIComponent(slug)}/`;",
    )

    # Blanket-fix relative depth for all shared chrome/links (page moves one level deeper).
    template = template.replace("../", "../../")

    old_tail = """  const params = new URLSearchParams(location.search);
  const hashParams = new URLSearchParams(location.hash.slice(1));
  const slug = params.get('slug') || hashParams.get('slug') || '';

  let isSrvvinci = false;

  const lookup = findBySlug(slug);
  lookup
    .then(song => {
      if (!song) { renderNotFound(); return null; }
      isSrvvinci = song.isSrvvinci;
      document.getElementById('discographyLink').href = isSrvvinci ? '../../srvvinci-discography/' : '../../discography/';
      const breadcrumbSection = document.getElementById('breadcrumbSection');
      breadcrumbSection.href = isSrvvinci ? '../../srvvinci-discography/' : '../../discography/';
      breadcrumbSection.textContent = isSrvvinci ? '前身バンド ディスコグラフィー' : 'DISCOGRAPHY';
      renderSong(song);
      fetch('../../data/amazon-products.json')
        .then(res => res.json())
        .then(products => renderAmazonProducts(products[song.title]))
        .catch(() => {});
      const url = new URL(location.href);
      const query = new URLSearchParams();
      query.set('title', song.title);
      const hash = new URLSearchParams();
      if (slug) hash.set('slug', slug);
      url.search = query.toString();
      url.hash = hash.toString();
      history.replaceState(null, '', url);
      return findLiveHistory(song.liveTitle || song.title);
    })
    .then(history => {
      const list = history || [];
      renderLiveStats(list);
      renderLiveYears(list);
      renderLiveHistory(list);
    })
    .catch(err => {
      console.error(err);
      renderNotFound();
    });

  document.getElementById('backLink').addEventListener('click', () => {
    if (document.referrer && document.referrer.includes(location.host)) {
      history.back();
    } else {
      location.href = '../../discography/';
    }
  });"""

    new_tail = """  const slug = SONG_DATA.slug || '';
  let isSrvvinci = SONG_DATA.isSrvvinci;
  document.getElementById('discographyLink').href = isSrvvinci ? '%(ROOT)ssrvvinci-discography/' : '%(ROOT)sdiscography/';
  const breadcrumbSection = document.getElementById('breadcrumbSection');
  breadcrumbSection.href = isSrvvinci ? '%(ROOT)ssrvvinci-discography/' : '%(ROOT)sdiscography/';
  breadcrumbSection.textContent = isSrvvinci ? '前身バンド ディスコグラフィー' : 'DISCOGRAPHY';
  renderSong(SONG_DATA);
  fetch('%(ROOT)sdata/amazon-products.json')
    .then(res => res.json())
    .then(products => {
      const own = products[SONG_DATA.title] || [];
      const albumTitle = SONG_DATA.album && SONG_DATA.album.title;
      const fromAlbum = albumTitle ? (products[albumTitle] || []) : [];
      renderAmazonProducts([...own, ...fromAlbum]);
    })
    .catch(() => {});
  renderLiveStats(LIVE_HISTORY);
  renderLiveYears(LIVE_HISTORY);
  renderLiveHistory(LIVE_HISTORY);

  document.getElementById('backLink').addEventListener('click', () => {
    if (document.referrer && document.referrer.includes(location.host)) {
      history.back();
    } else {
      location.href = '%(ROOT)sdiscography/';
    }
  });""" % {"ROOT": ROOT_TOKEN}

    if old_tail not in template:
        raise SystemExit("FATAL: old_tail block not found in template after path-fix — aborting to avoid silent corruption.")
    template = template.replace(old_tail, new_tail, 1)

    songs = collect_songs(kg, sv)
    print(f"Found {len(songs)} songs")

    generated = 0
    for slug, song in songs:
        page = template

        title = song.get("title") or "（タイトル不明）"
        song_type = song.get("type") or ""
        note = song.get("note") or ""
        is_srvvinci = song.get("isSrvvinci")

        desc = f"King Gnu{'（前身バンド時代）' if is_srvvinci else ''}「{title}」の楽曲詳細ページ。{note.split(',')[0] + '。' if note else ''}MV・タイアップ情報・ライブ披露履歴などをまとめて掲載。"
        canonical_url = f"https://fungnu.com/song/{slug}/"

        page = page.replace(
            "<title>楽曲詳細 — FunGNU</title>",
            f"<title>{esc_h(title)} — 楽曲詳細 — FunGNU</title>",
            1,
        )
        page = page.replace(
            '<meta name="description" content="King Gnu・Srv.Vinci時代の楽曲詳細ページ。MV・タイアップ情報・ライブ披露履歴などをまとめて掲載。">',
            f'<meta name="description" content="{esc_h(desc)}">',
            1,
        )
        page = page.replace(
            '<meta property="og:title" content="楽曲詳細 — FunGNU">',
            f'<meta property="og:title" content="{esc_h(title)} — 楽曲詳細 — FunGNU">',
            1,
        )
        page = page.replace(
            '<meta property="og:description" content="King Gnu・Srv.Vinci時代の楽曲詳細ページ。MV・タイアップ情報・ライブ披露履歴などをまとめて掲載。">',
            f'<meta property="og:description" content="{esc_h(desc)}">',
            1,
        )
        page = page.replace(
            '<meta property="og:url" content="https://fungnu.com/song/">',
            f'<meta property="og:url" content="{canonical_url}">',
            1,
        )
        page = page.replace(
            '<link rel="canonical" href="https://fungnu.com/song/">',
            f'<link rel="canonical" href="{canonical_url}">',
            1,
        )

        if song_type:
            page = page.replace(
                '<span class="disc-type-badge" id="typeBadge"></span>',
                f'<span class="disc-type-badge {esc_h(song_type)}" id="typeBadge">{esc_h(song_type)}</span>',
                1,
            )
        else:
            page = page.replace(
                '<span class="disc-type-badge" id="typeBadge"></span>',
                '<span class="disc-type-badge" id="typeBadge" style="display:none;"></span>',
                1,
            )

        page = page.replace(
            '<h1 class="page-header-title" id="songTitle">読み込み中…</h1>',
            f'<h1 class="page-header-title" id="songTitle">{esc_h(title)}</h1>',
            1,
        )
        page = page.replace(
            '<span id="breadcrumbCurrent">読み込み中…</span>',
            f'<span id="breadcrumbCurrent">{esc_h(title)}</span>',
            1,
        )

        # Deepen internal relative links inside this song's own extra text
        # (it will be displayed one directory level deeper than before).
        song_for_data = dict(song)
        song_for_data["extra"] = deepen_relative_links(song.get("extra") or "")

        live_history = find_live_history(title, song.get("liveTitle"), kg_live, sv_live)

        data_json = json.dumps(song_for_data, ensure_ascii=False).replace("</", "<\\/")
        history_json = json.dumps(live_history, ensure_ascii=False).replace("</", "<\\/")
        data_script = (
            "  <script>\n"
            f"    const SONG_DATA = {data_json};\n"
            f"    const LIVE_HISTORY = {history_json};\n"
            "  </script>\n"
        )

        anchor = "  <script>\n  function escH(s) {"
        if anchor not in page:
            raise SystemExit(f"FATAL: script anchor not found for slug={slug}")
        page = page.replace(anchor, data_script + anchor, 1)

        page = page.replace(ROOT_TOKEN, "../../")

        out_dir = os.path.join(OUT_BASE, slug)
        os.makedirs(out_dir, exist_ok=True)
        with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
            f.write(page)
        generated += 1

    print(f"Generated {generated} pages under {OUT_BASE}\\<slug>\\index.html")


if __name__ == "__main__":
    main()
