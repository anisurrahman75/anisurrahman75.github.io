#!/usr/bin/env python3
"""Publish a Markdown draft as a styled blog post.

Usage:
    python3 scripts/publish-post.py drafts/my-post.md

Reads a Markdown file with front-matter, then:
  1. writes blog/<slug>.html in the site's house style,
  2. inserts (or updates) the post card in blog/index.html,
  3. adds the page to sitemap.xml.

Re-running on the same file updates the post and its card in place.
No third-party dependencies — plain Python 3.

Front-matter (--- delimited, key: value):
  title    (required)  post title
  date     (required)  e.g. "Jul 2026" — shown on the card and the post
  tags     (required)  comma-separated, drives the index tag filter
  summary  (required)  1-2 sentences for the index card + meta description
  related  (optional)  URL for the "related" footer link
  minutes  (optional)  read-time estimate; computed from word count if absent
"""
import html
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://anisurrahman75.github.io"

# ---------------------------------------------------------------- front matter

def parse_front_matter(text):
    m = re.match(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", text, re.S)
    if not m:
        sys.exit("error: file must start with a --- front-matter block (see drafts/README.md)")
    meta = {}
    for line in m.group(1).splitlines():
        line = line.split("  #", 1)[0]  # allow trailing comments
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip().lower()] = v.strip()
    for req in ("title", "date", "tags", "summary"):
        if not meta.get(req):
            sys.exit(f"error: front-matter is missing required key: {req}")
    return meta, m.group(2).strip()

# ------------------------------------------------------------ markdown -> html

def inline(s):
    s = html.escape(s, quote=False)
    s = re.sub(r"`([^`]+)`",
               r'<code style="font-family:\'IBM Plex Mono\',monospace;font-size:14.5px;background:#161c26;border:1px solid #232c39;border-radius:5px;padding:1px 6px;color:#9fb0c0;">\1</code>', s)
    s = re.sub(r"\*\*([^*]+)\*\*", r'<strong style="color:#e7edf4;font-weight:600;">\1</strong>', s)
    s = re.sub(r"(?<!\*)\*([^*\n]+)\*(?!\*)", r"<em>\1</em>", s)
    s = re.sub(r"\[([^\]]+)\]\((https?://[^)]+)\)",
               r'<a href="\2" target="_blank" rel="noopener" style="color:var(--accent);border-bottom:1px solid rgba(70,200,192,0.35);">\1</a>', s)
    s = re.sub(r"\[([^\]]+)\]\(([^)]+)\)",
               r'<a href="\2" style="color:var(--accent);border-bottom:1px solid rgba(70,200,192,0.35);">\1</a>', s)
    return s

def code_box(lines):
    body = "<br>\n".join(html.escape(l, quote=False).replace(" ", "&nbsp;") for l in lines)
    return ('<div style="background:#0d1119;border:1px solid #1f2733;border-radius:12px;'
            'padding:18px 20px;margin:0 0 26px;font-family:\'IBM Plex Mono\',monospace;'
            f'font-size:13px;line-height:1.7;color:#9fb0c0;overflow-x:auto;">{body}</div>')

def md_to_html(md):
    out, lines, i = [], md.splitlines(), 0
    while i < len(lines):
        line = lines[i]
        if not line.strip():
            i += 1
            continue
        # fenced code
        if line.strip().startswith("```"):
            j = i + 1
            block = []
            while j < len(lines) and not lines[j].strip().startswith("```"):
                block.append(lines[j]); j += 1
            out.append(code_box(block)); i = j + 1
            continue
        # indented code (4+ spaces)
        if line.startswith("    "):
            block = []
            while i < len(lines) and (lines[i].startswith("    ") or not lines[i].strip()):
                if lines[i].strip() or (block and block[-1].strip()):
                    block.append(lines[i][4:] if lines[i].startswith("    ") else "")
                i += 1
            while block and not block[-1].strip():
                block.pop()
            out.append(code_box(block))
            continue
        # image on its own line -> figure with caption from alt text
        m_img = re.match(r"^!\[([^\]]*)\]\(([^)\s]+)\)\s*$", line.strip())
        if m_img:
            alt, src = m_img.group(1), m_img.group(2)
            out.append(
                '<figure style="margin:32px 0;">'
                f'<img src="{src}" alt="{html.escape(alt, quote=True)}" loading="lazy" '
                'style="width:100%;max-height:520px;object-fit:cover;border-radius:14px;border:1px solid #232c39;display:block;">'
                f'<figcaption style="font-size:13.5px;color:#7e8b9b;margin-top:10px;text-align:center;">{inline(alt)}</figcaption>'
                "</figure>")
            i += 1
            continue
        # heading
        if line.startswith("## "):
            out.append(f'<h2 style="font-size:24px;font-weight:600;letter-spacing:-0.01em;margin:40px 0 14px;color:#e7edf4;">{inline(line[3:].strip())}</h2>')
            i += 1
            continue
        # blockquote
        if line.startswith("> "):
            block = []
            while i < len(lines) and lines[i].startswith("> "):
                block.append(lines[i][2:].strip()); i += 1
            out.append('<blockquote style="margin:32px 0;padding:4px 0 4px 22px;border-left:2px solid var(--accent);font-size:19px;line-height:1.6;color:#dbe4ee;font-weight:500;">'
                       + inline(" ".join(block)) + "</blockquote>")
            continue
        # lists (ordered / unordered)
        m_ol = re.match(r"\s*\d+\.\s+", line)
        m_ul = re.match(r"\s*[-*]\s+", line)
        if m_ol or m_ul:
            tag = "ol" if m_ol else "ul"
            items, cur = [], None
            pat = r"\s*\d+\.\s+" if m_ol else r"\s*[-*]\s+"
            while i < len(lines) and lines[i].strip():
                m = re.match(pat, lines[i])
                if m:
                    if cur is not None:
                        items.append(cur)
                    cur = lines[i][m.end():].strip()
                elif cur is not None:
                    cur += " " + lines[i].strip()
                i += 1
            if cur is not None:
                items.append(cur)
            lis = "\n".join(f'<li style="margin-bottom:8px;">{inline(it)}</li>' for it in items)
            out.append(f'<{tag} style="margin:0 0 22px;padding-left:22px;font-size:16.5px;line-height:1.7;color:#c2cdda;">{lis}</{tag}>')
            continue
        # paragraph (may span lines)
        block = []
        while i < len(lines) and lines[i].strip() and not re.match(r"(## |> |```|    |\s*\d+\.\s|\s*[-*]\s)", lines[i]):
            block.append(lines[i].strip()); i += 1
        out.append(f'<p style="margin:0 0 22px;">{inline(" ".join(block))}</p>')
    return "\n\n      ".join(out)

# ------------------------------------------------------------------- template

def post_page(meta, body_html, slug):
    tags = [t.strip() for t in meta["tags"].split(",") if t.strip()]
    words = len(re.sub(r"[^\w\s]", "", body_html).split())
    minutes = meta.get("minutes") or max(2, round(words / 200))
    related = ""
    if meta.get("related"):
        label = re.sub(r"^https?://(www\.)?", "", meta["related"]).rstrip("/")
        related = (f'\n      <a href="{meta["related"]}" target="_blank" rel="noopener" '
                   'style="font-family:\'IBM Plex Mono\',monospace;font-size:13px;color:#93a0b1;" '
                   f'style-hover="color:#e7edf4;">related: {html.escape(label)} ↗</a>')
    title_esc = html.escape(meta["title"], quote=True)
    summary_esc = html.escape(meta["summary"], quote=True)
    return f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title_esc} — Anisur Rahman</title>
<meta name="description" content="{summary_esc}">
<meta name="author" content="Anisur Rahman">
<link rel="canonical" href="{SITE}/blog/{slug}.html">
<link rel="icon" href="data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'%3E%3Crect width='100' height='100' rx='20' fill='%230a0c10'/%3E%3Crect x='30' y='30' width='40' height='40' rx='8' fill='%2346c8c0'/%3E%3C/svg%3E">
<script src="../assets/js/support.js"></script>
<script src="../assets/js/toc.js" defer></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500;600&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
*{{box-sizing:border-box;}}
html{{scroll-behavior:smooth;}}
body{{margin:0;overflow-x:hidden;background:#0a0c10;color:#e7edf4;font-family:'IBM Plex Sans',system-ui,sans-serif;-webkit-font-smoothing:antialiased;}}
a{{text-decoration:none;color:inherit;}}
p{{text-wrap:pretty;}}
::selection{{background:rgba(70,200,192,0.32);color:#fff;}}
</style>
</helmet>
<div style="--accent:#46c8c0;background:#0a0c10;min-height:100vh;width:100%;">

  <header style="position:sticky;top:0;z-index:50;background:rgba(10,12,16,0.82);backdrop-filter:blur(14px);-webkit-backdrop-filter:blur(14px);border-bottom:1px solid #19202b;">
    <div style="max-width:760px;margin:0 auto;padding:0 32px;height:64px;display:flex;align-items:center;justify-content:space-between;gap:24px;">
      <a href="../index.html" style="display:flex;align-items:center;gap:10px;font-weight:600;font-size:15px;letter-spacing:-0.01em;">
        <span style="width:9px;height:9px;border-radius:2px;background:var(--accent);box-shadow:0 0 10px var(--accent);"></span>
        Anisur Rahman
      </a>
    </div>
  </header>

  <article style="max-width:720px;margin:0 auto;padding:36px 32px 96px;">
    <nav aria-label="Breadcrumb" style="display:flex;align-items:center;gap:8px;font-family:'IBM Plex Mono',monospace;font-size:13px;margin-bottom:28px;">
      <a href="../index.html" style="color:#93a0b1;" style-hover="color:#e7edf4;">Home</a>
      <span style="color:#3a4655;">›</span>
      <a href="index.html" style="color:#93a0b1;" style-hover="color:#e7edf4;">Blog</a>
      <span style="color:#3a4655;">›</span>
      <span style="color:#e7edf4;">{title_esc}</span>
    </nav>
    <div style="font-family:'IBM Plex Mono',monospace;font-size:11.5px;color:#7e8b9b;margin-bottom:16px;letter-spacing:0.04em;">{html.escape(" · ".join(tags))} <span style="color:#3a4655;">·</span> {minutes} min read</div>
    <h1 style="font-size:40px;line-height:1.1;font-weight:700;letter-spacing:-0.025em;margin:0 0 18px;">{title_esc}</h1>
    <div style="display:flex;align-items:center;gap:10px;padding-bottom:28px;border-bottom:1px solid #19202b;margin-bottom:36px;">
      <span style="font-size:14px;color:#9aa7b6;">By Anisur Rahman</span>
      <span style="color:#3a4655;">·</span>
      <span style="font-family:'IBM Plex Mono',monospace;font-size:12.5px;color:#7e8b9b;">{html.escape(meta["date"])}</span>
    </div>

    <div style="font-size:17px;line-height:1.72;color:#c2cdda;">
      {body_html}
    </div>

    <div style="margin-top:48px;padding-top:28px;border-top:1px solid #19202b;display:flex;justify-content:space-between;align-items:center;gap:16px;flex-wrap:wrap;">
      <a href="index.html" style="font-family:'IBM Plex Mono',monospace;font-size:13px;color:var(--accent);" style-hover="text-decoration:underline;">← all posts</a>{related}
    </div>
  </article>

</div>
</x-dc>
</body>
</html>
"""

def index_card(meta, slug):
    title_esc = html.escape(meta["title"], quote=False)
    return f"""<!-- post:{slug} -->
      <a data-post data-tags="{html.escape(meta['tags'], quote=True)}" href="{slug}.html" style="display:block;padding:28px 0;border-top:1px solid #19202b;" style-hover="opacity:0.85;">
        <h2 style="font-size:24px;font-weight:600;letter-spacing:-0.01em;margin:0 0 6px;color:#e7edf4;">{title_esc}</h2>
        <div data-cat style="font-family:'IBM Plex Mono',monospace;font-size:12.5px;color:var(--accent);margin-bottom:12px;">{html.escape(meta['date'])}</div>
        <p data-desc style="font-size:15px;line-height:1.55;color:#9aa7b6;margin:0;max-width:620px;">{html.escape(meta['summary'])}</p>
        <div data-tagrow style="display:flex;gap:7px;flex-wrap:wrap;margin-top:14px;"></div>
      </a>
      <!-- /post:{slug} -->"""

# ----------------------------------------------------------------------- main

def main():
    if len(sys.argv) != 2:
        sys.exit(__doc__.strip().splitlines()[2].strip())
    src = sys.argv[1]
    if not os.path.exists(src):
        sys.exit(f"error: {src} not found")
    slug = re.sub(r"[^a-z0-9-]", "", os.path.splitext(os.path.basename(src))[0].lower().replace(" ", "-"))
    if not slug:
        sys.exit("error: could not derive a slug from the filename")

    meta, md = parse_front_matter(open(src).read())
    body = md_to_html(md)

    # 1. post page
    post_path = os.path.join(ROOT, "blog", f"{slug}.html")
    with open(post_path, "w") as f:
        f.write(post_page(meta, body, slug))
    print(f"wrote  blog/{slug}.html")

    # 2. index card (insert new, or replace between markers on re-publish)
    idx_path = os.path.join(ROOT, "blog", "index.html")
    idx = open(idx_path).read()
    card = index_card(meta, slug)
    marker = re.compile(rf"<!-- post:{slug} -->.*?<!-- /post:{slug} -->", re.S)
    if marker.search(idx):
        idx = marker.sub(card, idx)
        print("update blog/index.html (card replaced)")
    else:
        anchor = '<div id="posts" style="display:flex;flex-direction:column;">'
        if anchor not in idx:
            sys.exit("error: could not find the posts container in blog/index.html")
        idx = idx.replace(anchor, anchor + "\n\n      " + card, 1)
        print("update blog/index.html (card added)")
    with open(idx_path, "w") as f:
        f.write(idx)

    # 3. sitemap
    sm_path = os.path.join(ROOT, "sitemap.xml")
    sm = open(sm_path).read()
    loc = f"{SITE}/blog/{slug}.html"
    if loc not in sm:
        sm = sm.replace("</urlset>", f"  <url><loc>{loc}</loc></url>\n</urlset>")
        with open(sm_path, "w") as f:
            f.write(sm)
        print("update sitemap.xml")

    print(f"\npublished: {SITE}/blog/{slug}.html")
    print("next: review locally, then  git add -A && git commit -m 'New post' && git push")

if __name__ == "__main__":
    main()
