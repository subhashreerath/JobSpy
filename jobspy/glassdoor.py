from jobspy import scrape_jobs
import webbrowser
import os
import json
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APPLIED_FILE = os.path.join(SCRIPT_DIR, "applied_jobs_glassdoor.json")
HTML_FILE = os.path.join(SCRIPT_DIR, "glassdoor_jobs.html")

# ---------------------------------------------------------------------------
# Configure the countries you want to search here.
# "country_indeed" must match jobspy's expected country name (case-insensitive).
# "location" is what gets passed to Glassdoor to narrow the search within that country.
# ---------------------------------------------------------------------------
COUNTRIES = [
    {"label": "UK", "location": "United Kingdom", "country_indeed": "uk"},
    {"label": "Ireland", "location": "Ireland", "country_indeed": "ireland"},
    {"label": "Germany", "location": "Deutschland", "country_indeed": "germany"},
    {"label": "New Zealand", "location": "New Zealand", "country_indeed": "New Zealand"},
]

SEARCH_TERM = "Cloud Engineer, DevOps Engineer"

# Words/phrases you don't want showing up in the title or description.
# Each entry gets turned into a "-term" exclusion (multi-word phrases get quoted automatically).
EXCLUDE_TERMS = ["manager", "intern", "senior manager", "data engineer"]

JOB_TYPE = "fulltime"
HOURS_OLD = 720.0
RESULTS_WANTED_PER_COUNTRY = 100

# Columns we want in the final table, in order.
COLUMNS_TO_SHOW = [
    "site",
    "job_url",
    "job_url_direct",
    "title",
    "company",
    "location",
    "date_posted",
    "job_type",
    "country_label",
]


def build_search_term(base_term, exclude_terms):
    exclusions = ""
    for term in exclude_terms:
        term = term.strip()
        if not term:
            continue
        if " " in term and not (term.startswith('"') and term.endswith('"')):
            term = f'"{term}"'
        exclusions += f" -{term}"
    return f"{base_term}{exclusions}"


def load_applied(applied_file=APPLIED_FILE):
    if os.path.exists(applied_file):
        with open(applied_file, "r") as f:
            return set(json.load(f))
    return set()


def save_applied(applied_set, applied_file=APPLIED_FILE):
    with open(applied_file, "w") as f:
        json.dump(list(applied_set), f, indent=2)


FINAL_SEARCH_TERM = build_search_term(SEARCH_TERM, EXCLUDE_TERMS)
print(f"Using search term: {FINAL_SEARCH_TERM}")


all_jobs = []

for c in COUNTRIES:
    print(f"Scraping Glassdoor for {c['label']}...")
    try:
        jobs = scrape_jobs(
            site_name="glassdoor",
            search_term=FINAL_SEARCH_TERM,
            location=c["location"],
            country_indeed=c["country_indeed"],
            job_type=JOB_TYPE,
            hours_old=HOURS_OLD,
            results_wanted=RESULTS_WANTED_PER_COUNTRY,
        )
        if jobs is None or len(jobs) == 0:
            print(f"  Found 0 jobs in {c['label']}")
            continue
        jobs["country_label"] = c["label"]
        print(f"  Found {len(jobs)} jobs in {c['label']}")
        all_jobs.append(jobs)
    except Exception as e:
        print(f"  Failed to scrape {c['label']}: {e}")

if not all_jobs:
    print(
        "\nNo jobs found for any country. Glassdoor scraping is currently broken "
        "upstream in JobSpy (Glassdoor changed their site and broke the scraper's "
        "CSRF token fetch + location lookup — see github.com/speedyapply/JobSpy "
        "PR #347). Patch your local jobspy/glassdoor/__init__.py or switch this "
        "script to Indeed/LinkedIn until the fix is released to PyPI."
    )
    raise SystemExit(0)

jobs = pd.concat(all_jobs, ignore_index=True)
print(f"\nTotal jobs found across all countries: {len(jobs)}")

# reindex instead of a plain [] lookup so we never crash if a scraper
# returns a dataframe missing one of the expected columns
jobs_filtered = jobs.reindex(columns=COLUMNS_TO_SHOW).copy()

jobs_filtered = jobs_filtered.drop_duplicates(subset=["job_url"]).reset_index(drop=True)

applied = load_applied()
jobs_filtered = jobs_filtered[~jobs_filtered["job_url"].isin(applied)].reset_index(drop=True)
print(f"Showing {len(jobs_filtered)} jobs after excluding {len(applied)} previously applied")

country_counts = jobs_filtered["country_label"].value_counts().to_dict()
country_badges_html = "".join(
    f'<div class="stat-badge">{label}: <strong>{count}</strong></div>'
    for label, count in country_counts.items()
)

filter_buttons_html = '<button class="filter-btn active" data-country="all" onclick="filterCountry(\'all\')">All</button>'
for c in COUNTRIES:
    filter_buttons_html += (
        f'<button class="filter-btn" data-country="{c["label"]}" '
        f'onclick="filterCountry(\'{c["label"]}\')">{c["label"]}</button>'
    )

rows_html = ""
for idx, row in jobs_filtered.iterrows():
    job_url = row["job_url"] if pd.notna(row["job_url"]) else ""
    job_url_direct = row["job_url_direct"] if pd.notna(row["job_url_direct"]) else ""
    title = row["title"] if pd.notna(row["title"]) else ""
    company = row["company"] if pd.notna(row["company"]) else ""
    location = row["location"] if pd.notna(row["location"]) else ""
    date_posted = str(row["date_posted"]) if pd.notna(row["date_posted"]) else ""
    job_type = row["job_type"] if pd.notna(row["job_type"]) else ""
    country_label = row["country_label"] if pd.notna(row["country_label"]) else ""
    site = row["site"] if pd.notna(row["site"]) else ""

    url_link = f'<a href="{job_url}" target="_blank">View</a>' if job_url else ""
    direct_link = f'<a href="{job_url_direct}" target="_blank">Direct</a>' if job_url_direct else ""

    rows_html += f"""
    <tr id="row-{idx}" data-url="{job_url}" data-country="{country_label}">
        <td><span class="country-tag">{country_label}</span></td>
        <td>{site}</td>
        <td>{url_link}</td>
        <td>{direct_link}</td>
        <td class="title-col">{title}</td>
        <td>{company}</td>
        <td>{location}</td>
        <td>{date_posted}</td>
        <td>{job_type}</td>
        <td><button class="btn-apply" onclick="markApplied({idx}, '{job_url}')">Mark Applied</button></td>
    </tr>"""

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Glassdoor Jobs - Cloud/DevOps Engineer</title>
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
        .stat-badge strong {{ color: #2563eb; }}
        .controls {{
            text-align: center;
            margin-bottom: 20px;
            display: flex;
            justify-content: center;
            align-items: center;
            gap: 12px;
            flex-wrap: wrap;
        }}
        .filter-group {{
            display: flex;
            gap: 6px;
            background: #fff;
            padding: 6px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.08);
        }}
        .filter-btn {{
            border: none;
            background: transparent;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 13px;
            font-weight: 600;
            cursor: pointer;
            color: #555;
            transition: all 0.15s;
        }}
        .filter-btn:hover {{ background: #f0f2f5; }}
        .filter-btn.active {{
            background: #1a1a2e;
            color: #fff;
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
            background: #1a1a2e;
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
        tr.hidden-row {{ display: none; }}
        .country-tag {{
            background: #eef2ff;
            color: #4338ca;
            padding: 3px 10px;
            border-radius: 12px;
            font-size: 12px;
            font-weight: 600;
            white-space: nowrap;
        }}
        .title-col {{ font-weight: 500; max-width: 250px; }}
        a {{
            color: #2563eb;
            text-decoration: none;
            font-weight: 500;
        }}
        a:hover {{ text-decoration: underline; }}
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
    </style>
</head>
<body>
    <div class="header">
        <h1>Job Listings — Cloud & DevOps Engineer</h1>
        <p>Glassdoor &bull; UK, Ireland, Germany &amp; New Zealand &bull; Fulltime &bull; Last 30 days</p>
    </div>
    <div class="stats">
        <div class="stat-badge">Total found: <strong>{len(jobs)}</strong></div>
        <div class="stat-badge">Showing: <strong>{len(jobs_filtered)}</strong></div>
        <div class="stat-badge">Already applied: <strong>{len(applied)}</strong></div>
        {country_badges_html}
    </div>
    <div class="controls">
        <div class="filter-group">
            {filter_buttons_html}
        </div>
        <button class="btn-save" onclick="saveApplied()">Save Applied Jobs (update file)</button>
    </div>
    <table>
        <thead>
            <tr>
                <th>Country</th>
                <th>Site</th>
                <th>Link</th>
                <th>Direct Link</th>
                <th>Title</th>
                <th>Company</th>
                <th>Location</th>
                <th>Date Posted</th>
                <th>Type</th>
                <th>Action</th>
            </tr>
        </thead>
        <tbody>
            {rows_html}
        </tbody>
    </table>

    <script>
        let appliedJobs = JSON.parse(localStorage.getItem('glassdoorApplied') || '[]');

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
                localStorage.setItem('glassdoorApplied', JSON.stringify(appliedJobs));
            }}
        }}

        function saveApplied() {{
            const blob = new Blob([JSON.stringify(appliedJobs, null, 2)], {{type: 'application/json'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'applied_jobs_glassdoor.json';
            a.click();
            alert('Downloaded applied_jobs_glassdoor.json — place it next to glassdoor.py to exclude these jobs on next run.');
        }}

        function filterCountry(country) {{
            document.querySelectorAll('.filter-btn').forEach(btn => {{
                btn.classList.toggle('active', btn.dataset.country === country);
            }});
            document.querySelectorAll('tr[data-country]').forEach(row => {{
                if (country === 'all' || row.dataset.country === country) {{
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
webbrowser.open('file://' + os.path.realpath(HTML_FILE))
print("Opening in browser...")