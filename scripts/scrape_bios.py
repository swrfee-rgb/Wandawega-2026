#!/usr/bin/env python3
"""
Scrape every Studio Gang staffer's bio from studiogang.com.

Writes a single file `bios.json` next to itself, mapping display
name -> { role, bio }. The bio is the visible text from each
person's /people/<slug>/ page, stripped of HTML and capped at
1500 characters so the result stays paste-friendly.

Run locally — the Wandawega sandbox can't reach studiogang.com.

    python3 scrape_bios.py

That's it. No `>` redirection needed. Look for bios.json in the
same folder when it finishes (~1 minute for ~127 people).

Requires Python 3.7+, standard library only.
"""

import html as html_lib
import json
import os
import re
import sys
import time
import urllib.request

LISTING_URL = "https://studiogang.com/people/"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15"
)
MAX_BIO_CHARS = 1500
OUT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "bios.json")


def fetch(url, retries=3):
    last = None
    for attempt in range(retries):
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "text/html"})
        try:
            with urllib.request.urlopen(req, timeout=30) as r:
                return r.read().decode("utf-8", errors="replace")
        except Exception as e:
            last = e
            time.sleep(1.5 * (attempt + 1))
    raise last


def parse_listing(html):
    """Return [(display_name, individual_url, role)]."""
    module_re = re.compile(
        r'<div class="module m[12]">(.*?)(?=<div class="module m[12]">|</section>)',
        re.S,
    )
    href_re = re.compile(
        r'<a[^>]*href="(https://studiogang\.com/people/[^"]+)"[^>]*class="cyan"', re.S
    )
    name_re = re.compile(r'<a[^>]*class="cyan"[^>]*>([^<]+)</a>', re.S)
    role_re = re.compile(
        r'<a[^>]*class="cyan"[^>]*>[^<]+</a><br>\s*([^<]+?)\s*</div>', re.S
    )
    out = []
    for m in module_re.finditer(html):
        block = m.group(1)
        h = href_re.search(block)
        n = name_re.search(block)
        if not (h and n):
            continue
        name = re.sub(r"\s+", " ", html_lib.unescape(n.group(1))).strip()
        url = h.group(1).strip()
        role_m = role_re.search(block)
        role = (
            re.sub(r"\s+", " ", html_lib.unescape(role_m.group(1))).strip()
            if role_m
            else ""
        )
        out.append((name, url, role))
    return out


def extract_bio(html):
    """Best-effort: pull visible bio text from a person's page."""
    # Strip script and style first
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.S | re.I)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S | re.I)

    # Most bio prose on studiogang.com lives inside <div class="txt"> or
    # <div class="txt sm"> blocks. Grab all of them when present.
    blocks = re.findall(r'<div class="txt[^"]*">(.*?)</div>', text, re.S)
    if blocks:
        text = "\n\n".join(blocks)
    else:
        # Fallback: try <article> or the main content area
        art = re.search(r"<article[^>]*>(.*?)</article>", text, re.S | re.I)
        if art:
            text = art.group(1)

    # Strip remaining tags
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</p>", "\n\n", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)
    # Collapse whitespace but keep paragraph breaks
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n[ \t]+", "\n", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    if len(text) > MAX_BIO_CHARS:
        text = text[:MAX_BIO_CHARS].rsplit(" ", 1)[0] + "…"
    return text


def main():
    print(f"# fetching listing: {LISTING_URL}", file=sys.stderr)
    listing_html = fetch(LISTING_URL)
    people = parse_listing(listing_html)
    print(f"# {len(people)} people found", file=sys.stderr)

    out = {}
    for i, (name, url, role) in enumerate(people, 1):
        try:
            page_html = fetch(url)
            bio = extract_bio(page_html)
            out[name] = {"role": role, "bio": bio, "url": url}
            shown = bio[:60].replace("\n", " ")
            print(f"# [{i}/{len(people)}] {name:35} -> {shown}…", file=sys.stderr)
        except Exception as e:
            out[name] = {"role": role, "bio": "", "url": url, "error": str(e)}
            print(f"# [{i}/{len(people)}] {name:35} -> FETCH FAILED: {e}", file=sys.stderr)
        time.sleep(0.4)  # be polite

    with open(OUT_FILE, "w", encoding="utf-8") as f:
        json.dump(out, f, ensure_ascii=False, indent=2, sort_keys=True)

    print(f"\nWrote {OUT_FILE}", file=sys.stderr)
    print(f"({len(out)} people, ~{os.path.getsize(OUT_FILE) // 1024} KB)", file=sys.stderr)


if __name__ == "__main__":
    main()
