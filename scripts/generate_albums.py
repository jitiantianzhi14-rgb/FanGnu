# -*- coding: utf-8 -*-
"""
Static page generator for FunGNU album pages.
Reads scripts/templates/album.html as a template, bakes per-album content, and
writes album/<encoded-title>/index.html (King Gnu) or
album/<encoded-title>-srvvinci/index.html (Srv.Vinci) for every album.
"""
import json
import os
import re
import urllib.parse

ROOT = r"c:/fanGNU"
TEMPLATE_PATH = os.path.join(ROOT, "scripts", "templates", "album.html")
OUT_BASE = os.path.join(ROOT, "album")

ROOT_TOKEN = "@@ROOT@@"

JS_SAFE = "!'()*"


def js_encode_uri_component(s):
    return urllib.parse.quote(str(s), safe=JS_SAFE, encoding="utf-8")


def load_json(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


LINK_URL_RE = re.compile(r"(\[[^\]]+\]\()(\.\./[^)]+)(\))")


def deepen_relative_links(text):
    """Prepend one extra '../' to internal (non-http) markdown-lite links."""
    if not text:
        return text

    def repl(m):
        return m.group(1) + "../" + m.group(2) + m.group(3)

    return LINK_URL_RE.sub(repl, text)


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
    kg = load_json("kinggnu-discography.json")
    sv = load_json("srvvinci-discography.json")
    products_data = load_json("amazon-products.json")

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    old_canon = """    const canonicalUrl = isSrvvinci
      ? `https://fungnu.com/album/?src=srvvinci&album=${encodeURIComponent(album.title)}`
      : `https://fungnu.com/album/?album=${encodeURIComponent(album.title)}`;"""
    new_canon = """    const canonicalUrl = `https://fungnu.com/album/${encodeURIComponent(ALBUM_DATA.urlSlug)}/`;"""
    if old_canon not in template:
        raise SystemExit("FATAL: old_canon block not found")
    template = template.replace(old_canon, new_canon, 1)

    # Blanket-fix relative depth for all shared chrome/links (page moves one level deeper).
    template = template.replace("../", "../../")

    old_tail = """  const params = new URLSearchParams(location.search);
  const albumTitle = params.get('album') || '';
  const isSrvvinci = params.get('src') === 'srvvinci';

  const breadcrumbSection = document.getElementById('breadcrumbSection');
  breadcrumbSection.href = isSrvvinci ? '../../srvvinci-discography/' : '../../discography/';
  breadcrumbSection.textContent = isSrvvinci ? '前身バンド ディスコグラフィー' : 'DISCOGRAPHY';

  const dataUrl = isSrvvinci ? '../../data/srvvinci-discography.json' : '../../data/kinggnu-discography.json';

  fetch(dataUrl)
    .then(res => res.json())
    .then(data => {
      let album;
      if (isSrvvinci) {
        for (const group of (data.groups || [])) {
          album = [...(group.demos || []), ...(group.albums || [])].find(a => a.title === albumTitle);
          if (album) break;
        }
      } else {
        album = (data.albums || []).find(a => a.title === albumTitle);
      }
      if (!album) { renderNotFound(isSrvvinci); return; }
      renderAlbum(album, isSrvvinci);

      fetch('../../data/amazon-products.json')
        .then(res => res.json())
        .then(products => renderAmazonProducts(products[album.title]))
        .catch(() => {});
    })
    .catch(err => {
      console.error(err);
      renderNotFound(isSrvvinci);
    });

  document.getElementById('backLink').addEventListener('click', () => {
    if (document.referrer && document.referrer.includes(location.host)) {
      history.back();
    } else {
      location.href = isSrvvinci ? '../../srvvinci-discography/' : '../../discography/';
    }
  });"""

    new_tail = """  const isSrvvinci = ALBUM_DATA.isSrvvinci;

  const breadcrumbSection = document.getElementById('breadcrumbSection');
  breadcrumbSection.href = isSrvvinci ? '%(ROOT)ssrvvinci-discography/' : '%(ROOT)sdiscography/';
  breadcrumbSection.textContent = isSrvvinci ? '前身バンド ディスコグラフィー' : 'DISCOGRAPHY';

  renderAlbum(ALBUM_DATA.album, isSrvvinci);
  renderAmazonProducts(AMAZON_PRODUCTS);

  document.getElementById('backLink').addEventListener('click', () => {
    if (document.referrer && document.referrer.includes(location.host)) {
      history.back();
    } else {
      location.href = isSrvvinci ? '%(ROOT)ssrvvinci-discography/' : '%(ROOT)sdiscography/';
    }
  });""" % {"ROOT": ROOT_TOKEN}

    if old_tail not in template:
        raise SystemExit("FATAL: old_tail block not found in template after path-fix")
    template = template.replace(old_tail, new_tail, 1)

    albums = []  # list of (title, album_dict, is_srvvinci)
    for a in kg.get("albums", []):
        albums.append((a.get("title"), a, False))
    for group in sv.get("groups", []):
        for a in list(group.get("demos", []) or []) + list(group.get("albums", []) or []):
            if not a.get("tracks"):
                continue
            albums.append((a.get("title"), a, True))

    generated = 0
    for title, album, is_srvvinci in albums:
        dir_name = album.get("slug")
        if not dir_name:
            raise SystemExit(f"FATAL: album '{title}' has no explicit slug field")
        canonical_url = f"https://fungnu.com/album/{dir_name}/"

        page = template

        page_title = f"{title} — アルバム概要 — FunGNU!!!"
        note = album.get("note") or ""
        artist_label = "Srv.Vinci（前身バンド時代）" if is_srvvinci else "King Gnu"
        desc = f"{artist_label}のアルバム「{title}」概要ページ。{note + '。' if note else ''}発売日・収録曲などをまとめて掲載。"
        page = page.replace(
            "<title>アルバム概要 — FunGNU!!!</title>",
            f"<title>{esc_h(page_title)}</title>",
            1,
        )
        page = page.replace(
            '<meta name="description" content="King Gnuのアルバム概要ページ。発売日・収録曲などをまとめて掲載。">',
            f'<meta name="description" content="{esc_h(desc)}">',
            1,
        )
        page = page.replace(
            '<meta property="og:title" content="アルバム概要 — FunGNU!!!">',
            f'<meta property="og:title" content="{esc_h(page_title)}">',
            1,
        )
        page = page.replace(
            '<meta property="og:description" content="King Gnuのアルバム概要ページ。発売日・収録曲などをまとめて掲載。">',
            f'<meta property="og:description" content="{esc_h(desc)}">',
            1,
        )
        page = page.replace(
            '<meta property="og:url" content="https://fungnu.com/album/">',
            f'<meta property="og:url" content="{canonical_url}">',
            1,
        )
        page = page.replace(
            '<link rel="canonical" href="https://fungnu.com/album/">',
            f'<link rel="canonical" href="{canonical_url}">',
            1,
        )
        page = page.replace(
            '<h1 class="page-header-title" id="albumTitle">読み込み中…</h1>',
            f'<h1 class="page-header-title" id="albumTitle">{esc_h(title)}</h1>',
            1,
        )
        page = page.replace(
            '<span id="breadcrumbCurrent">読み込み中…</span>',
            f'<span id="breadcrumbCurrent">{esc_h(title)}</span>',
            1,
        )

        products = products_data.get(title, [])
        album_for_data = dict(album)
        album_for_data["extra"] = deepen_relative_links(album.get("extra") or "")
        data_obj = {"isSrvvinci": is_srvvinci, "urlSlug": dir_name, "album": album_for_data}
        data_json = json.dumps(data_obj, ensure_ascii=False).replace("</", "<\\/")
        products_json = json.dumps(products, ensure_ascii=False).replace("</", "<\\/")
        data_script = (
            "  <script>\n"
            f"    const ALBUM_DATA = {data_json};\n"
            f"    const AMAZON_PRODUCTS = {products_json};\n"
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

    print(f"Generated {generated} pages under {OUT_BASE}\\<title>\\index.html")


if __name__ == "__main__":
    main()
