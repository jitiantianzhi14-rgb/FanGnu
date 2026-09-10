# -*- coding: utf-8 -*-
"""
Static page generator for FunGNU live-show pages.
Reads live-show/index.html as a template, bakes per-show content, and writes
live-show/<date>/index.html (King Gnu) or live-show/<date>-srvvinci/index.html
(Srv.Vinci) for every show in the live JSON files.
"""
import json
import os

ROOT = r"c:/fanGNU"
TEMPLATE_PATH = os.path.join(ROOT, "scripts", "templates", "live-show.html")
OUT_BASE = os.path.join(ROOT, "live-show")

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


def main():
    kg_live = load_json("kinggnu-live.json")
    sv_live = load_json("srvvinci-live.json")

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    # Fix the JS line that rebuilds canonical/og:url in the old query-string format.
    old_canon = """    const canonicalUrl = isSrvvinci
      ? `https://fungnu.com/live-show/?date=${encodeURIComponent(show.date)}&src=srvvinci`
      : `https://fungnu.com/live-show/?date=${encodeURIComponent(show.date)}`;"""
    new_canon = """    const canonicalUrl = `https://fungnu.com/live-show/${encodeURIComponent(SHOW_DATA.urlSlug)}/`;"""
    if old_canon not in template:
        raise SystemExit("FATAL: old_canon block not found")
    template = template.replace(old_canon, new_canon, 1)

    # Blanket-fix relative depth for all shared chrome/links (page moves one level deeper).
    template = template.replace("../", "../../")

    old_tail = """  const params = new URLSearchParams(location.search);
  const date = params.get('date') || '';
  const isSrvvinci = params.get('src') === 'srvvinci';
  const backHref = isSrvvinci ? '../../srvvinci-live/' : '../../live/';
  document.getElementById('archiveLink').href = backHref;
  const breadcrumbSection = document.getElementById('breadcrumbSection');
  breadcrumbSection.href = backHref;
  breadcrumbSection.textContent = isSrvvinci ? '前身バンド ライブ' : 'LIVE';

  Promise.all([findShow(date, isSrvvinci), loadSongIndex(isSrvvinci), loadAlbumMap()])
    .then(([result, songIndex, songAlbum]) => {
      if (result) renderShow(result.tour, result.show, songIndex, songAlbum);
      else renderNotFound();
    })
    .catch(err => {
      console.error(err);
      renderNotFound();
    });

  document.getElementById('backLink').addEventListener('click', () => {
    if (document.referrer && document.referrer.includes(location.host)) {
      history.back();
    } else {
      location.href = backHref;
    }
  });"""

    new_tail = """  const isSrvvinci = SHOW_DATA.isSrvvinci;
  const backHref = isSrvvinci ? '%(ROOT)ssrvvinci-live/' : '%(ROOT)slive/';
  document.getElementById('archiveLink').href = backHref;
  const breadcrumbSection = document.getElementById('breadcrumbSection');
  breadcrumbSection.href = backHref;
  breadcrumbSection.textContent = isSrvvinci ? '前身バンド ライブ' : 'LIVE';

  Promise.all([loadSongIndex(isSrvvinci), loadAlbumMap()])
    .then(([songIndex, songAlbum]) => {
      renderShow(SHOW_DATA.tour, SHOW_DATA.show, songIndex, songAlbum);
    })
    .catch(err => {
      console.error(err);
      renderNotFound();
    });

  document.getElementById('backLink').addEventListener('click', () => {
    if (document.referrer && document.referrer.includes(location.host)) {
      history.back();
    } else {
      location.href = backHref;
    }
  });""" % {"ROOT": ROOT_TOKEN}

    if old_tail not in template:
        raise SystemExit("FATAL: old_tail block not found in template after path-fix")
    template = template.replace(old_tail, new_tail, 1)

    # Also fix loadSongIndex/loadAlbumMap fetch paths: they already got blanket-fixed to
    # '../../data/...'  -- that's correct since this page is now one level deeper.

    generated = 0
    seen_dirs = {}
    duplicates = []
    for source_file, is_srvvinci in ((kg_live, False), (sv_live, True)):
        for tour in source_file.get("tours", []):
            tour_min = {"name": tour.get("name")}
            for show in tour.get("shows", []):
                date = show.get("date")
                if not date:
                    continue
                base_dir_name = f"{date}-srvvinci" if is_srvvinci else date
                if base_dir_name in seen_dirs:
                    seen_dirs[base_dir_name] += 1
                    dir_name = f"{base_dir_name}-{seen_dirs[base_dir_name]}"
                    duplicates.append((base_dir_name, dir_name, show.get("venue")))
                else:
                    seen_dirs[base_dir_name] = 1
                    dir_name = base_dir_name

                page = template

                venue = show.get("venue") or "会場未定"
                tour_name = tour.get("name") or ""
                page_title = f"{venue} — 公演詳細 — FunGNU!!!"
                desc = f"{date} {tour_name}（{venue}）の公演詳細。セットリストなどをまとめて掲載。"
                canonical_url = f"https://fungnu.com/live-show/{dir_name}/"

                if not (show.get("note") or "").strip():
                    noindex_anchor = '  <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
                    if noindex_anchor not in page:
                        raise SystemExit(f"FATAL: noindex anchor not found for {dir_name}")
                    page = page.replace(
                        noindex_anchor,
                        noindex_anchor + '  <meta name="robots" content="noindex">\n',
                        1,
                    )

                page = page.replace(
                    "<title>公演詳細 — FunGNU!!!</title>",
                    f"<title>{esc_h(page_title)}</title>",
                    1,
                )
                page = page.replace(
                    '<meta name="description" content="King Gnu・Srv.Vinci時代のライブ公演詳細ページ。会場・セットリストなどをまとめて掲載。">',
                    f'<meta name="description" content="{esc_h(desc)}">',
                    1,
                )
                page = page.replace(
                    '<meta property="og:title" content="公演詳細 — FunGNU!!!">',
                    f'<meta property="og:title" content="{esc_h(page_title)}">',
                    1,
                )
                page = page.replace(
                    '<meta property="og:description" content="King Gnu・Srv.Vinci時代のライブ公演詳細ページ。会場・セットリストなどをまとめて掲載。">',
                    f'<meta property="og:description" content="{esc_h(desc)}">',
                    1,
                )
                page = page.replace(
                    '<meta property="og:url" content="https://fungnu.com/live-show/">',
                    f'<meta property="og:url" content="{canonical_url}">',
                    1,
                )
                page = page.replace(
                    '<link rel="canonical" href="https://fungnu.com/live-show/">',
                    f'<link rel="canonical" href="{canonical_url}">',
                    1,
                )

                page = page.replace(
                    '<h1 class="page-header-title" id="venueName">読み込み中…</h1>',
                    f'<h1 class="page-header-title" id="venueName">{esc_h(venue)}</h1>',
                    1,
                )
                page = page.replace(
                    '<span id="breadcrumbCurrent">読み込み中…</span>',
                    f'<span id="breadcrumbCurrent">{esc_h(venue)}</span>',
                    1,
                )
                page = page.replace(
                    '<div class="page-header-tour" id="tourName"></div>',
                    f'<div class="page-header-tour" id="tourName">{esc_h(tour_name)}</div>',
                    1,
                )
                page = page.replace(
                    '<div class="page-header-date" id="showDate"></div>',
                    f'<div class="page-header-date" id="showDate">{esc_h(date)}</div>',
                    1,
                )
                page = page.replace(
                    '<div class="detail-address" id="address"></div>',
                    f'<div class="detail-address" id="address">{esc_h(show.get("location") or "")}</div>',
                    1,
                )
                status = show.get("status")
                if status:
                    badge_class = "live-badge sold" if status == "SOLD OUT" else "live-badge"
                    page = page.replace(
                        '<span class="live-badge" id="statusBadge" style="display:none;"></span>',
                        f'<span class="{badge_class}" id="statusBadge">{esc_h(status)}</span>',
                        1,
                    )
                note = show.get("note")
                if note:
                    page = page.replace(
                        '<div class="detail-note" id="noteText" style="display:none;"></div>',
                        f'<div class="detail-note" id="noteText">※{esc_h(note)}</div>',
                        1,
                    )

                data_obj = {"isSrvvinci": is_srvvinci, "urlSlug": dir_name, "tour": tour_min, "show": show}
                data_json = json.dumps(data_obj, ensure_ascii=False).replace("</", "<\\/")
                data_script = (
                    "  <script>\n"
                    f"    const SHOW_DATA = {data_json};\n"
                    "  </script>\n"
                )

                anchor = "  <script>\n  function escH(s) {"
                if anchor not in page:
                    raise SystemExit(f"FATAL: script anchor not found for {dir_name}")
                page = page.replace(anchor, data_script + anchor, 1)

                page = page.replace(ROOT_TOKEN, "../../")

                out_dir = os.path.join(OUT_BASE, dir_name)
                os.makedirs(out_dir, exist_ok=True)
                with open(os.path.join(out_dir, "index.html"), "w", encoding="utf-8") as f:
                    f.write(page)
                generated += 1

    print(f"Generated {generated} pages under {OUT_BASE}\\<date>\\index.html")
    if duplicates:
        print("WARNING: duplicate show dates found (disambiguated with a numeric suffix):")
        for base, disambiguated, venue in duplicates:
            print(f"  {base} -> {disambiguated} (venue: {venue})")


if __name__ == "__main__":
    main()
