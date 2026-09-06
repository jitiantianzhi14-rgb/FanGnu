# -*- coding: utf-8 -*-
"""
Static page generator for FunGNU video/release pages.
Reads scripts/templates/video.html as a template, bakes per-release content, and
writes video/<encoded-title>/index.html for every kinggnu-discography.json item
that has a "discs" field (Blu-ray/DVD releases).
"""
import json
import os
import re
import urllib.parse

ROOT = r"c:/fanGNU"
TEMPLATE_PATH = os.path.join(ROOT, "scripts", "templates", "video.html")
OUT_BASE = os.path.join(ROOT, "video")

ROOT_TOKEN = "@@ROOT@@"

JS_SAFE = "!'()*"


def js_encode_uri_component(s):
    return urllib.parse.quote(str(s), safe=JS_SAFE, encoding="utf-8")


def load_json(name):
    with open(os.path.join(ROOT, "data", name), encoding="utf-8") as f:
        return json.load(f)


LINK_URL_RE = re.compile(r"(\[[^\]]+\]\()(\.\./[^)]+)(\))")


def deepen_relative_links(text):
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
    products_data = load_json("amazon-products.json")

    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        template = f.read()

    old_canon = """    const canonicalUrl = `https://fungnu.com/video/?title=${encodeURIComponent(release.title)}`;"""
    new_canon = """    const canonicalUrl = `https://fungnu.com/video/${encodeURIComponent(RELEASE_DATA.urlSlug)}/`;"""
    if old_canon not in template:
        raise SystemExit("FATAL: old_canon block not found")
    template = template.replace(old_canon, new_canon, 1)

    # Blanket-fix relative depth for all shared chrome/links (page moves one level deeper).
    template = template.replace("../", "../../")

    old_tail = """  const params = new URLSearchParams(location.search);
  const title = params.get('title') || '';

  fetch('../../data/kinggnu-discography.json')
    .then(res => res.json())
    .then(data => {
      const release = (data.items || []).find(i => i.title === title && i.discs);
      if (!release) { renderNotFound(); return; }
      renderRelease(release);

      fetch('../../data/amazon-products.json')
        .then(res => res.json())
        .then(products => renderAmazonProducts(products[release.title]))
        .catch(() => {});
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

    new_tail = """  renderRelease(RELEASE_DATA.release);
  renderAmazonProducts(AMAZON_PRODUCTS);

  document.getElementById('backLink').addEventListener('click', () => {
    if (document.referrer && document.referrer.includes(location.host)) {
      history.back();
    } else {
      location.href = '%(ROOT)sdiscography/';
    }
  });""" % {"ROOT": ROOT_TOKEN}

    if old_tail not in template:
        raise SystemExit("FATAL: old_tail block not found in template after path-fix")
    template = template.replace(old_tail, new_tail, 1)

    releases = [item for item in kg.get("items", []) if item.get("discs")]

    generated = 0
    for release in releases:
        title = release.get("title")
        dir_name = release.get("slug")
        if not dir_name:
            raise SystemExit(f"FATAL: release '{title}' has no explicit slug field")
        canonical_url = f"https://fungnu.com/video/{dir_name}/"

        page = template

        page_title = f"{title} — FunGNU"
        release_type = release.get("type") or ""
        desc = f"King Gnuの{release_type + ' ' if release_type else ''}「{title}」の詳細ページ。収録曲などをまとめて掲載。"
        page = page.replace(
            "<title>リリース詳細 — FunGNU</title>",
            f"<title>{esc_h(page_title)}</title>",
            1,
        )
        page = page.replace(
            '<meta name="description" content="King Gnuの映像作品・パッケージ商品の詳細ページ。収録曲などをまとめて掲載。">',
            f'<meta name="description" content="{esc_h(desc)}">',
            1,
        )
        page = page.replace(
            '<meta property="og:title" content="リリース詳細 — FunGNU">',
            f'<meta property="og:title" content="{esc_h(page_title)}">',
            1,
        )
        page = page.replace(
            '<meta property="og:description" content="King Gnuの映像作品・パッケージ商品の詳細ページ。収録曲などをまとめて掲載。">',
            f'<meta property="og:description" content="{esc_h(desc)}">',
            1,
        )
        page = page.replace(
            '<meta property="og:url" content="https://fungnu.com/video/">',
            f'<meta property="og:url" content="{canonical_url}">',
            1,
        )
        page = page.replace(
            '<link rel="canonical" href="https://fungnu.com/video/">',
            f'<link rel="canonical" href="{canonical_url}">',
            1,
        )
        page = page.replace(
            '<h1 class="page-header-title" id="releaseTitle">読み込み中…</h1>',
            f'<h1 class="page-header-title" id="releaseTitle">{esc_h(title)}</h1>',
            1,
        )
        page = page.replace(
            '<span id="breadcrumbCurrent">読み込み中…</span>',
            f'<span id="breadcrumbCurrent">{esc_h(title)}</span>',
            1,
        )
        release_type = release.get("type")
        if release_type:
            page = page.replace(
                '<span class="disc-type-badge" id="typeBadge"></span>',
                f'<span class="disc-type-badge {esc_h(release_type)}" id="typeBadge">{esc_h(release_type)}</span>',
                1,
            )
        else:
            page = page.replace(
                '<span class="disc-type-badge" id="typeBadge"></span>',
                '<span class="disc-type-badge" id="typeBadge" style="display:none;"></span>',
                1,
            )

        products = products_data.get(title, [])
        release_for_data = dict(release)
        release_for_data["extra"] = deepen_relative_links(release.get("extra") or "")
        data_obj = {"urlSlug": dir_name, "release": release_for_data}
        data_json = json.dumps(data_obj, ensure_ascii=False).replace("</", "<\\/")
        products_json = json.dumps(products, ensure_ascii=False).replace("</", "<\\/")
        data_script = (
            "  <script>\n"
            f"    const RELEASE_DATA = {data_json};\n"
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
