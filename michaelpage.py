import requests
from bs4 import BeautifulSoup
import webbrowser
import os
import json
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APPLIED_FILE = os.path.join(SCRIPT_DIR, "applied_jobs_michaelpage.json")
HTML_FILE = os.path.join(SCRIPT_DIR, "michaelpage_jobs.html")
BASE_URL = "https://www.michaelpage.de"

SEARCH_TERMS = [
    "cloud-engineer",
    "devops-engineer",
    "platform-engineer",
    "infrastructure-engineer",
]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept-Language": "de-DE,de;q=0.9,en;q=0.8",
}


def load_applied():
    if os.path.exists(APPLIED_FILE):
        with open(APPLIED_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_applied(applied_set):
    with open(APPLIED_FILE, "w") as f:
        json.dump(list(applied_set), f, indent=2)


def scrape_search(search_term):
    url = f"{BASE_URL}/jobs/{search_term}/deutschland"
    print(f"Scraping: {url}")
    resp = requests.get(url, headers=HEADERS, timeout=30)
    if resp.status_code != 200:
        print(f"  Warning: got status {resp.status_code} for {search_term}")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    jobs = []

    # Find job listing links - they follow pattern /job-detail/*/ref/*
    job_links = soup.find_all("a", href=lambda h: h and "/job-detail/" in h)

    seen_urls = set()
    for link in job_links:
        href = link.get("href", "")
        if not href or href in seen_urls:
            continue
        seen_urls.add(href)

        full_url = BASE_URL + href if href.startswith("/") else href
        title = link.get_text(strip=True)
        if not title or len(title) < 3:
            continue

        # Try to find location and contract type from surrounding elements
        parent = link.find_parent("div") or link.find_parent("li") or link.find_parent("article")
        location = ""
        contract_type = ""

        if parent:
            text_content = parent.get_text(" ", strip=True)
            # Look for common German cities/location patterns
            for loc_elem in parent.find_all(["span", "li", "div"]):
                loc_text = loc_elem.get_text(strip=True)
                if loc_text in ["Festanstellung", "Interim", "Freelance"]:
                    contract_type = loc_text
                elif len(loc_text) < 40 and loc_text != title and any(c.isalpha() for c in loc_text):
                    if not location and loc_text not in ["Speichern", "Jobs ansehen", "Home Office"]:
                        # Heuristic: short text that's not a button label might be location
                        if any(city in loc_text for city in ["Berlin", "München", "Hamburg", "Stuttgart", "Frankfurt", "Köln", "Düsseldorf", "Bonn", "Leipzig", "Dresden", "Hannover", "Nürnberg", "Bremen", "Essen", "Dortmund"]):
                            location = loc_text

        # Extract reference ID from URL
        ref_id = ""
        if "/ref/" in href:
            ref_id = href.split("/ref/")[-1]

        jobs.append({
            "title": title,
            "company": "via Michael Page",
            "location": location,
            "contract_type": contract_type,
            "job_url": full_url,
            "ref_id": ref_id,
            "search_term": search_term.replace("-", " ").title(),
        })

    print(f"  Found {len(jobs)} jobs")
    return jobs


# Scrape all search terms
all_jobs = []
for term in SEARCH_TERMS:
    all_jobs.extend(scrape_search(term))

# Deduplicate by URL
seen = set()
unique_jobs = []
for job in all_jobs:
    if job["job_url"] not in seen:
        seen.add(job["job_url"])
        unique_jobs.append(job)

print(f"\nTotal unique jobs found: {len(unique_jobs)}")

# Exclude applied jobs
applied = load_applied()
filtered_jobs = [j for j in unique_jobs if j["job_url"] not in applied]
print(f"Showing {len(filtered_jobs)} jobs after excluding {len(applied)} previously applied")

# Build HTML
rows_html = ""
for idx, job in enumerate(filtered_jobs):
    rows_html += f"""
    <tr id="row-{idx}" data-url="{job['job_url']}">
        <td class="title-col"><a href="{job['job_url']}" target="_blank">{job['title']}</a></td>
        <td>{job['company']}</td>
        <td>{job['location']}</td>
        <td>{job['contract_type']}</td>
        <td><span class="search-tag">{job['search_term']}</span></td>
        <td><code>{job['ref_id']}</code></td>
        <td><button class="btn-apply" onclick="markApplied({idx}, '{job['job_url']}')">Mark Applied</button></td>
    </tr>"""

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Michael Page Jobs - Cloud/DevOps/Platform Engineer</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #f0f2f5;
            padding: 30px;
            color: #333;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 28px;
            color: #1a1a2e;
            margin-bottom: 8px;
        }}
        .header p {{
            color: #666;
            font-size: 14px;
        }}
        .stats {{
            display: flex;
            justify-content: center;
            gap: 20px;
            margin-bottom: 20px;
            flex-wrap: wrap;
        }}
        .stat-badge {{
            background: #fff;
            border-radius: 8px;
            padding: 10px 20px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
            font-size: 14px;
        }}
        .stat-badge strong {{ color: #0066cc; }}
        .controls {{
            text-align: center;
            margin-bottom: 20px;
        }}
        .btn-save {{
            background: #10b981;
            color: #fff;
            border: none;
            padding: 10px 24px;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .btn-save:hover {{ background: #059669; }}
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #fff;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.08);
        }}
        thead {{
            background: #0066cc;
            color: #fff;
        }}
        th {{
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        td {{
            padding: 12px 16px;
            border-bottom: 1px solid #eee;
            font-size: 14px;
        }}
        tr:hover {{ background: #f8fafc; }}
        tr.applied {{
            background: #d1fae5 !important;
            opacity: 0.6;
        }}
        tr.applied .btn-apply {{
            background: #6b7280;
            cursor: default;
        }}
        tr.applied .btn-apply::after {{ content: " ✓"; }}
        .title-col {{ font-weight: 500; max-width: 300px; }}
        .title-col a {{
            color: #0066cc;
            text-decoration: none;
            font-weight: 500;
        }}
        .title-col a:hover {{ text-decoration: underline; }}
        .search-tag {{
            background: #e0e7ff;
            color: #3730a3;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 500;
        }}
        code {{
            background: #f3f4f6;
            padding: 2px 6px;
            border-radius: 4px;
            font-size: 12px;
            color: #666;
        }}
        .btn-apply {{
            background: #ef4444;
            color: #fff;
            border: none;
            padding: 6px 14px;
            border-radius: 5px;
            font-size: 12px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .btn-apply:hover {{ background: #dc2626; }}
        .empty-state {{
            text-align: center;
            padding: 60px;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Michael Page — Job Listings</h1>
        <p>Cloud Engineer &bull; DevOps Engineer &bull; Platform Engineer &bull; Infrastructure Engineer &bull; Deutschland</p>
    </div>
    <div class="stats">
        <div class="stat-badge">Total found: <strong>{len(unique_jobs)}</strong></div>
        <div class="stat-badge">Showing: <strong>{len(filtered_jobs)}</strong></div>
        <div class="stat-badge">Already applied: <strong>{len(applied)}</strong></div>
        <div class="stat-badge">Search terms: <strong>{len(SEARCH_TERMS)}</strong></div>
    </div>
    <div class="controls">
        <button class="btn-save" onclick="saveApplied()">Save Applied Jobs (update file)</button>
    </div>
    {"<table><thead><tr><th>Title</th><th>Source</th><th>Location</th><th>Contract</th><th>Search</th><th>Ref ID</th><th>Action</th></tr></thead><tbody>" + rows_html + "</tbody></table>" if filtered_jobs else '<div class="empty-state"><h2>No new jobs found</h2><p>All current listings have been marked as applied, or no results were returned.</p></div>'}

    <script>
        let appliedJobs = JSON.parse(localStorage.getItem('michaelpageApplied') || '[]');

        appliedJobs.forEach(url => {{
            document.querySelectorAll('tr[data-url]').forEach(row => {{
                if (row.dataset.url === url) {{
                    row.classList.add('applied');
                    row.querySelector('.btn-apply').textContent = 'Applied';
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
                localStorage.setItem('michaelpageApplied', JSON.stringify(appliedJobs));
            }}
        }}

        function saveApplied() {{
            const blob = new Blob([JSON.stringify(appliedJobs, null, 2)], {{type: 'application/json'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'applied_jobs_michaelpage.json';
            a.click();
            alert('Downloaded applied_jobs_michaelpage.json — place it next to michaelpage.py to exclude these jobs on next run.');
        }}
    </script>
</body>
</html>"""

with open(HTML_FILE, "w") as f:
    f.write(html_content)

print(f"\nJobs saved to {HTML_FILE}")
webbrowser.open('file://' + os.path.realpath(HTML_FILE))
print("Opening in browser...")