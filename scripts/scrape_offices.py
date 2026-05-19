#!/usr/bin/env python3
"""
Scrape Studio Gang's people page + each person's individual page to
infer office (Chicago / San Francisco / New York / Paris).

Run locally where studiogang.com is reachable — this sandbox host
isn't allowlisted and gets HTTP 403, so the scrape has to happen on
your machine.

Output: prints a JSON dict mapping normalized name -> office. Paste
the relevant entries into the PEOPLE_OFFICES const in index.html
(or pipe to a file and process from there).

Usage:
    python3 scripts/scrape_offices.py > offices.json

Requires: a recent Python 3 with the standard library only.
"""
import html as html_lib
import json
import re
import sys
import time
import unicodedata
import urllib.request

LISTING_URL = "https://studiogang.com/people/"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.0 Safari/605.1.15"
)
OFFICES = ("Chicago", "San Francisco", "New York", "Paris")
# Office aliases the bio prose sometimes uses.
OFFICE_PATTERNS = (
    ("Chicago",       re.compile(r"\bChicago\b", re.I)),
    ("San Francisco", re.compile(r"\b(San\s*Francisco|SF\b|Bay\s*Area)\b", re.I)),
    ("New York",      re.compile(r"\b(New\s*York(\s+City)?|NYC|N\.Y\.|Manhattan|Brooklyn)\b", re.I)),
    ("Paris",         re.compile(r"\bParis\b", re.I)),
)

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

def normalize(name):
    s = unicodedata.normalize("NFD", name)
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.lower()
    s = re.sub(r"[\"‘’“”']", "", s)
    s = re.sub(r"[^a-z\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def parse_listing(html):
    """Return list of (display_name, role, individual_url)."""
    module_re = re.compile(
        r'<div class="module m[12]">(.*?)(?=<div class="module m[12]">|</section>)',
        re.S,
    )
    href_re = re.compile(r'<a[^>]*href="(https://studiogang\.com/people/[^"]+)"[^>]*class="cyan"', re.S)
    name_re = re.compile(r'<a[^>]*class="cyan"[^>]*>([^<]+)</a>', re.S)
    role_re = re.compile(r'<a[^>]*class="cyan"[^>]*>[^<]+</a><br>\s*([^<]+?)\s*</div>', re.S)
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
        role = re.sub(r"\s+", " ", html_lib.unescape(role_m.group(1))).strip() if role_m else ""
        out.append((name, role, url))
    return out

def office_from_role(role):
    """Quick win — role title sometimes names an office."""
    for office, pat in OFFICE_PATTERNS:
        if pat.search(role or ""):
            return office
    return None

def office_from_bio(html, role=""):
    """Extract visible text and tally office mentions; return the most
    frequent one. Bias toward Paris/SF/NY (small offices) when tied
    with Chicago (since the studio's HQ is Chicago and 'Chicago' is
    over-mentioned in boilerplate copy)."""
    # Drop scripts/styles/nav for cleaner mentions
    text = re.sub(r"<script.*?</script>", " ", html, flags=re.S)
    text = re.sub(r"<style.*?</style>", " ", text, flags=re.S)
    # Roughly isolate the article body: the people pages put the bio
    # inside <div class="txt"> blocks. Grab them if present.
    body_blocks = re.findall(r'<div class="txt[^"]*">(.*?)</div>', text, re.S)
    if body_blocks:
        text = " ".join(body_blocks)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", text)
    text = html_lib.unescape(text)

    counts = {}
    for office, pat in OFFICE_PATTERNS:
        counts[office] = len(pat.findall(text))

    role_office = office_from_role(role)
    if role_office:
        return role_office

    # Drop offices with zero hits.
    nonzero = {o: c for o, c in counts.items() if c > 0}
    if not nonzero:
        return None

    # Prefer smaller-office hits if any beat 0, else Chicago.
    best = max(nonzero.items(), key=lambda kv: (kv[1], kv[0] != "Chicago"))
    return best[0]

def main():
    print(f"# fetching listing: {LISTING_URL}", file=sys.stderr)
    listing_html = fetch(LISTING_URL)
    people = parse_listing(listing_html)
    print(f"# {len(people)} people found", file=sys.stderr)

    result = {}
    for i, (name, role, url) in enumerate(people, 1):
        key = normalize(name)
        # Cheap path first — sometimes role title gives it away.
        office = office_from_role(role)
        if office is None:
            try:
                bio_html = fetch(url)
                office = office_from_bio(bio_html, role=role)
            except Exception as e:
                print(f"# [{i}/{len(people)}] {name}: fetch failed ({e})", file=sys.stderr)
                continue
            time.sleep(0.4)  # be polite
        if office:
            result[key] = office
            print(f"# [{i}/{len(people)}] {name:35} -> {office}", file=sys.stderr)
        else:
            print(f"# [{i}/{len(people)}] {name:35} -> (no office found)", file=sys.stderr)

    json.dump(result, sys.stdout, ensure_ascii=False, indent=2, sort_keys=True)
    sys.stdout.write("\n")

if __name__ == "__main__":
    main()
