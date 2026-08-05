"""
google_boards.py
-----------------
Scrapes Google search results for DevOps/Cloud Engineer job postings hosted
on ATS platforms (Personio, join.com, Lever, Workable) using Google dork
queries, e.g.:

    devops engineer inurl:personio intext:germany
    devops engineer inurl:join.com intext:germany
    devops engineer inurl:lever intext:germany
    devops engineer inurl:workable.com intext:germany

Mirrors the structure/conventions of indeed.py (applied_jobs.json /
invalid_jobs.json tracking, interactive HTML output, exclusion terms).

IMPORTANT CAVEATS (read before relying on this):
1. This scrapes Google's HTML search results directly. Google does not
   officially support this and will rate-limit / CAPTCHA aggressive or
   frequent scraping. Keep SLEEP_BETWEEN_QUERIES generous and don't run
   this in a tight loop.
2. Google's markup changes over time, so the CSS selectors below may need
   updating if results stop parsing (check the debug HTML dump this script
   writes on a suspected parse failure).
3. Google doesn't support an exact "hours old" filter like Indeed does.
   The closest built-in options are day / week / month (`qdr:d/w/m`).
   TBS is set to "qdr:m" (past month) below as the nearest match to your
   720-hour Indeed window — tighten to "qdr:w" if you want to mimic 720h
   (30 days) more loosely or need fewer, fresher results.
4. If you hit CAPTCHAs repeatedly, the reliable long-term fix is to switch
   to the official Google Programmable Search Engine (Custom Search JSON
   API) or a paid SERP API (e.g. SerpApi) instead of raw HTML scraping.

Install deps:
    pip install requests beautifulsoup4 lxml
"""

import os
import re
import json
import time
import random
import webbrowser
from urllib.parse import urlparse, parse_qs, unquote

import requests
from bs4 import BeautifulSoup

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APPLIED_FILE = os.path.join(SCRIPT_DIR, "google_boards_applied.json")
INVALID_FILE = os.path.join(SCRIPT_DIR, "google_boards_invalid.json")
HTML_FILE = os.path.join(SCRIPT_DIR, "google_boards_jobs.html")
DEBUG_HTML_FILE = os.path.join(SCRIPT_DIR, "google_boards_last_response.html")

# ---------------------------------------------------------------------------
# Boards to search. Each becomes its own "inurl:" dork.
# ---------------------------------------------------------------------------
BOARDS = [
    {"label": "Personio", "inurl": "personio"},
    {"label": "join.com", "inurl": "join.com"},
    {"label": "Lever", "inurl": "lever"},
    {"label": "Workable", "inurl": "workable.com"},
]

BASE_TERM = "devops engineer"
INTEXT = "germany"

# Same idea as indeed.py — words you don't want in the title/snippet.
EXCLUDE_TERMS = ["manager", "intern", "senior manager", "data engineer"]

RESULTS_WANTED_PER_BOARD = 30   # Google typically caps ~30-100 per query before blocking
TBS = "qdr:m"                    # qdr:d = past day, qdr:w = past week, qdr:m = past month
SLEEP_BETWEEN_QUERIES = (6, 12)  # random seconds between requests, be polite

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
}


def build_query(inurl_value, base_term, intext, exclude_terms):
    exclusions = ""
    for term in exclude_terms:
        term = term.strip()
        if not term:
            continue
        if " " in term and not (term.startswith('"') and term.endswith('"')):
            term = f'"{term}"'
        exclusions += f" -{term}"
    return f"{base_term} inurl:{inurl_value} intext:{intext}{exclusions}"


def load_json_set(path):
    if os.path.exists(path):
        with open(path, "r") as f:
            return set(json.load(f))
    return set()


def save_json_set(path, data_set):
    with open(path, "w") as f:
        json.dump(list(data_set), f, indent=2)


def clean_google_url(href):
    """Unwrap Google's '/url?q=...' redirect links if present."""
    if href.startswith("/url?"):
        qs = parse_qs(urlparse(href).query)
        if "q" in qs:
            return unquote(qs["q"][0])
    return href


def looks_like_captcha(html_text):
    markers = ["our systems have detected unusual traffic", "recaptcha", "/sorry/index"]
    lowered = html_text.lower()
    return any(m in lowered for m in markers)


def google_search(query, num_results, tbs):
    """Fetch one page of Google results and parse title/url/snippet."""
    params = {
        "q": query,
        "num": num_results,
        "hl": "en",
        "gl": "de",
        "tbs": tbs,
    }
    # Bypass the EU/GDPR cookie-consent interstitial, which otherwise
    # returns HTTP 200 with a consent page instead of real results.
    cookies = {"CONSENT": "YES+1"}

    resp = requests.get(
        "https://www.google.com/search",
        params=params,
        headers=HEADERS,
        cookies=cookies,
        timeout=15,
    )
    print(f"  HTTP {resp.status_code}, response length {len(resp.text)} chars")

    # Always dump the last response so a 0-result run can be diagnosed —
    # open google_boards_last_response.html in a browser to see what
    # Google actually sent back (consent wall, captcha, real results, etc).
    with open(DEBUG_HTML_FILE, "w") as f:
        f.write(resp.text)

    if looks_like_captcha(resp.text):
        print(
            "  !! Google returned a CAPTCHA/unusual-traffic page. "
            f"Saved response to {DEBUG_HTML_FILE} for inspection. "
            "Stopping further requests for this run — try again later with "
            "longer delays, or switch to an official Search API."
        )
        return None  # signal caller to stop

    if "consent.google.com" in resp.url or "consent" in resp.text.lower()[:2000]:
        print(
            "  !! Response looks like a cookie-consent page, not results. "
            f"Check {DEBUG_HTML_FILE}."
        )

    soup = BeautifulSoup(resp.text, "lxml")
    results = []

    # Primary selector (classic Google organic result block)
    blocks = soup.select("div.g") or soup.select("div.MjjYud")

    for block in blocks:
        a_tag = block.find("a", href=True)
        h3_tag = block.find("h3")
        if not a_tag or not h3_tag:
            continue
        url = clean_google_url(a_tag["href"])
        if not url.startswith("http"):
            continue
        title = h3_tag.get_text(strip=True)
        snippet_tag = block.select_one("div.VwiC3b") or block.select_one("span.aCOpRe")
        snippet = snippet_tag.get_text(" ", strip=True) if snippet_tag else ""
        results.append({"url": url, "title": title, "snippet": snippet})

    # Fallback: grab any h3-in-a pattern if the block selectors above found nothing
    if not results:
        for a_tag in soup.find_all("a", href=True):
            h3_tag = a_tag.find("h3")
            if h3_tag:
                url = clean_google_url(a_tag["href"])
                if url.startswith("http"):
                    results.append({"url": url, "title": h3_tag.get_text(strip=True), "snippet": ""})

    return results


def extract_company(url, board_label):
    """Best-effort company name extraction from known ATS URL patterns."""
    try:
        parsed = urlparse(url)
        host = parsed.netloc.lower()
        path_parts = [p for p in parsed.path.split("/") if p]

        if board_label == "Personio":
            # e.g. https://COMPANY.jobs.personio.de/job/12345
            if ".personio." in host:
                return host.split(".")[0].replace("-", " ").title()
        elif board_label == "join.com":
            # e.g. https://join.com/companies/COMPANY/jobs/12345-title
            if "companies" in path_parts:
                idx = path_parts.index("companies")
                if idx + 1 < len(path_parts):
                    return path_parts[idx + 1].replace("-", " ").title()
        elif board_label == "Lever":
            # e.g. https://jobs.lever.co/COMPANY/job-id
            if "lever.co" in host and path_parts:
                return path_parts[0].replace("-", " ").title()
        elif board_label == "Workable":
            # e.g. https://apply.workable.com/COMPANY/j/JOBID/
            if "workable.com" in host and path_parts:
                return path_parts[0].replace("-", " ").title()
    except Exception:
        pass
    return "Unknown"


# ---------------------------------------------------------------------------
# Run searches
# ---------------------------------------------------------------------------
applied = load_json_set(APPLIED_FILE)
invalid = load_json_set(INVALID_FILE)

all_results = []

for board in BOARDS:
    query = build_query(board["inurl"], BASE_TERM, INTEXT, EXCLUDE_TERMS)
    print(f"Searching Google for {board['label']}: {query}")

    results = google_search(query, RESULTS_WANTED_PER_BOARD, TBS)
    if results is None:
        break  # captcha hit, stop entirely for this run
    print(f"  Found {len(results)} raw results")

    for r in results:
        r["board"] = board["label"]
        r["company"] = extract_company(r["url"], board["label"])
        all_results.append(r)

    time.sleep(random.uniform(*SLEEP_BETWEEN_QUERIES))

if not all_results:
    print("No results found (or stopped early). Exiting.")
    raise SystemExit(0)

# Dedup by URL
seen = set()
deduped = []
for r in all_results:
    if r["url"] in seen:
        continue
    seen.add(r["url"])
    deduped.append(r)

print(f"\nTotal unique results across all boards: {len(deduped)}")

# Exclude already applied / marked invalid
filtered = [r for r in deduped if r["url"] not in applied and r["url"] not in invalid]
print(f"Showing {len(filtered)} after excluding {len(applied)} applied and {len(invalid)} invalid")

# Per-board counts for the stats bar
board_counts = {}
for r in filtered:
    board_counts[r["board"]] = board_counts.get(r["board"], 0) + 1

board_badges_html = "".join(
    f'<div class="stat-badge">{label}: <strong>{count}</strong></div>'
    for label, count in board_counts.items()
)

filter_buttons_html = '<button class="filter-btn active" data-board="all" onclick="filterBoard(\'all\')">All</button>'
for board in BOARDS:
    filter_buttons_html += (
        f'<button class="filter-btn" data-board="{board["label"]}" '
        f'onclick="filterBoard(\'{board["label"]}\')">{board["label"]}</button>'
    )

rows_html = ""
for idx, r in enumerate(filtered):
    url = r["url"]
    title = r["title"] or ""
    snippet = r["snippet"] or ""
    company = r["company"] or "Unknown"
    board = r["board"]

    rows_html += f"""
    <tr id="row-{idx}" data-url="{url}" data-board="{board}">
        <td><span class="board-tag">{board}</span></td>
        <td>{company}</td>
        <td class="title-col"><a href="{url}" target="_blank">{title}</a></td>
        <td class="snippet-col">{snippet}</td>
        <td>
            <button class="btn-apply" onclick="markApplied({idx}, '{url}')">Mark Applied</button>
            <button class="btn-invalid" onclick="markInvalid({idx}, '{url}')">Not Relevant</button>
        </td>
    </tr>"""

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Google Job Board Search - DevOps Engineer (Germany)</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            padding: 30px;
            color: #333;
        }}
        .header {{ text-align: center; margin-bottom: 30px; }}
        .header h1 {{ font-size: 28px; color: #1a1a2e; margin-bottom: 8px; }}
        .header p {{ color: #666; font-size: 14px; }}
        .stats {{
            display: flex; justify-content: center; gap: 20px;
            margin-bottom: 20px; flex-wrap: wrap;
        }}
        .stat-badge {{
            background: #fff; border-radius: 8px; padding: 10px 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08); font-size: 14px;
        }}
        .stat-badge strong {{ color: #2563eb; }}
        .controls {{
            text-align: center; margin-bottom: 20px; display: flex;
            justify-content: center; align-items: center; gap: 12px; flex-wrap: wrap;
        }}
        .filter-group {{
            display: flex; gap: 6px; background: #fff; padding: 6px;
            border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        }}
        .filter-btn {{
            border: none; background: transparent; padding: 8px 16px;
            border-radius: 6px; font-size: 13px; font-weight: 600;
            cursor: pointer; color: #555; transition: all 0.15s;
        }}
        .filter-btn:hover {{ background: #f0f2f5; }}
        .filter-btn.active {{ background: #1a1a2e; color: #fff; }}
        .btn-save {{
            background: #10b981; color: #fff; border: none; padding: 10px 24px;
            border-radius: 6px; font-size: 14px; cursor: pointer; transition: background 0.2s;
        }}
        .btn-save:hover {{ background: #059669; }}
        table {{
            width: 100%; border-collapse: collapse; background: #fff;
            border-radius: 12px; overflow: hidden; box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        thead {{ background: #1a1a2e; color: #fff; }}
        th {{
            padding: 14px 16px; text-align: left; font-weight: 600;
            font-size: 13px; text-transform: uppercase; letter-spacing: 0.5px;
        }}
        td {{ padding: 12px 16px; border-bottom: 1px solid #eee; font-size: 14px; }}
        tr:hover {{ background: #f8fafc; }}
        tr.applied {{ background: #d1fae5 !important; opacity: 0.6; }}
        tr.applied .btn-apply {{ background: #6b7280; cursor: default; }}
        tr.applied .btn-apply::after {{ content: " ✓"; }}
        tr.invalid {{ background: #fee2e2 !important; opacity: 0.5; }}
        tr.hidden-row {{ display: none; }}
        .board-tag {{
            background: #eef2ff; color: #4338ca; padding: 3px 10px;
            border-radius: 12px; font-size: 12px; font-weight: 600; white-space: nowrap;
        }}
        .title-col {{ font-weight: 500; max-width: 260px; }}
        .snippet-col {{ color: #666; font-size: 13px; max-width: 320px; }}
        a {{ color: #2563eb; text-decoration: none; font-weight: 500; }}
        a:hover {{ text-decoration: underline; }}
        .btn-apply, .btn-invalid {{
            border: none; padding: 6px 12px; border-radius: 5px; font-size: 12px;
            cursor: pointer; transition: background 0.2s; margin: 2px;
        }}
        .btn-apply {{ background: #ef4444; color: #fff; }}
        .btn-apply:hover {{ background: #dc2626; }}
        .btn-invalid {{ background: #9ca3af; color: #fff; }}
        .btn-invalid:hover {{ background: #6b7280; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Job Board Search — DevOps Engineer (Germany)</h1>
        <p>Google dork search &bull; Personio, join.com, Lever, Workable &bull; Past month</p>
    </div>
    <div class="stats">
        <div class="stat-badge">Total found: <strong>{len(deduped)}</strong></div>
        <div class="stat-badge">Showing: <strong>{len(filtered)}</strong></div>
        <div class="stat-badge">Already applied: <strong>{len(applied)}</strong></div>
        <div class="stat-badge">Marked invalid: <strong>{len(invalid)}</strong></div>
        {board_badges_html}
    </div>
    <div class="controls">
        <div class="filter-group">
            {filter_buttons_html}
        </div>
        <button class="btn-save" onclick="saveApplied()">Save Applied (download)</button>
        <button class="btn-save" onclick="saveInvalid()" style="background:#9ca3af;">Save Invalid (download)</button>
    </div>
    <table>
        <thead>
            <tr>
                <th>Board</th>
                <th>Company</th>
                <th>Title</th>
                <th>Snippet</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>

    <script>
        let appliedJobs = JSON.parse(localStorage.getItem('googleBoardsApplied') || '[]');
        let invalidJobs = JSON.parse(localStorage.getItem('googleBoardsInvalid') || '[]');

        appliedJobs.forEach(url => {{
            document.querySelectorAll('tr[data-url]').forEach(row => {{
                if (row.dataset.url === url) {{
                    row.classList.add('applied');
                    row.querySelector('.btn-apply').textContent = 'Applied';
                }}
            }});
        }});
        invalidJobs.forEach(url => {{
            document.querySelectorAll('tr[data-url]').forEach(row => {{
                if (row.dataset.url === url) {{
                    row.classList.add('invalid');
                }}
            }});
        }});

        function markApplied(idx, url) {{
            const row = document.getElementById('row-' + idx);
            if (row.classList.contains('applied')) return;
            row.classList.add('applied');
            row.querySelector('.btn-apply').textContent = 'Applied';
            if (!appliedJobs.includes(url)) {{
                appliedJobs.push(url);
                localStorage.setItem('googleBoardsApplied', JSON.stringify(appliedJobs));
            }}
        }}

        function markInvalid(idx, url) {{
            const row = document.getElementById('row-' + idx);
            row.classList.add('invalid');
            if (!invalidJobs.includes(url)) {{
                invalidJobs.push(url);
                localStorage.setItem('googleBoardsInvalid', JSON.stringify(invalidJobs));
            }}
        }}

        function saveApplied() {{
            const blob = new Blob([JSON.stringify(appliedJobs, null, 2)], {{type: 'application/json'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'google_boards_applied.json';
            a.click();
            alert('Downloaded google_boards_applied.json — place it next to google_boards.py to exclude these jobs next run.');
        }}

        function saveInvalid() {{
            const blob = new Blob([JSON.stringify(invalidJobs, null, 2)], {{type: 'application/json'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'google_boards_invalid.json';
            a.click();
            alert('Downloaded google_boards_invalid.json — place it next to google_boards.py to exclude these jobs next run.');
        }}

        function filterBoard(board) {{
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.dataset.board === board);
            }});
            document.querySelectorAll('tr[data-board]').forEach(row => {{
                if (board === 'all' || row.dataset.board === board) {{
                    row.classList.remove('hidden-row');
                }} else {{
                    row.classList.add('hidden-row');
                }}
            }});
        }}
    </script>
</body>
</html>"""

with open(HTML_FILE, "w") as f:
    f.write(html_content)

print(f"Jobs saved to {HTML_FILE}")
webbrowser.open("file://" + os.path.realpath(HTML_FILE))
print("Opening in browser...")