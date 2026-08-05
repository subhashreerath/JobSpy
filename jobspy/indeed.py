from jobspy import scrape_jobs
import webbrowser
import os
import json
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APPLIED_FILE = os.path.join(SCRIPT_DIR, "applied_jobs.json")
INVALID_FILE = os.path.join(SCRIPT_DIR, "invalid_jobs.json")
HTML_FILE = os.path.join(SCRIPT_DIR, "indeed_jobs.html")

# ---------------------------------------------------------------------------
# Configure the countries you want to search here.
# "country_indeed" must match jobspy's expected country name (case-insensitive).
# "location" is what gets passed to Indeed to narrow the search within that country
# (city, region, or just the country name again for a nationwide search).
# ---------------------------------------------------------------------------
COUNTRIES = [
    {"label": "UK", "location": "United Kingdom", "country_indeed": "uk"},
    {"label": "Ireland", "location": "Ireland", "country_indeed": "ireland"},
    {"label": "Germany", "location": "Deutschland", "country_indeed": "germany"},
    {"label": "New Zealand", "location": "New Zealand", "country_indeed": "new zealand"},
    {"label": "Canada", "location": "Canada", "country_indeed": "canada"},
    {"label": "Netherlands", "location": "Netherlands", "country_indeed": "netherlands"},
]

SEARCH_TERM = "Cloud Engineer, DevOps Engineer"

# Words/phrases you don't want showing up in the title or description.
# Each entry gets turned into a "-term" exclusion (multi-word phrases get quoted automatically).
# Example: ["manager", "intern", "night shift"]
EXCLUDE_TERMS = ["manager", "intern", "senior manager", "data engineer", "Full-Stack Software Engineer"]

JOB_TYPE = "fulltime"
HOURS_OLD = 1000.0
RESULTS_WANTED_PER_COUNTRY = 100

def build_search_term(base_term, exclude_terms):
    exclusions = ""
    for term in exclude_terms:
        term = term.strip()
        if not term:
            continue
        # Wrap multi-word phrases in quotes so Indeed treats them as an exact match
        if " " in term and not (term.startswith('"') and term.endswith('"')):
            term = f'"{term}"'
        exclusions += f" -{term}"
    return f"{base_term}{exclusions}"


FINAL_SEARCH_TERM = build_search_term(SEARCH_TERM, EXCLUDE_TERMS)
print(f"Using search term: {FINAL_SEARCH_TERM}")


def load_applied():
    if os.path.exists(APPLIED_FILE):
        with open(APPLIED_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_applied(applied_set):
    with open(APPLIED_FILE, "w") as f:
        json.dump(list(applied_set), f, indent=2)


def load_invalid():
    if os.path.exists(INVALID_FILE):
        with open(INVALID_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_invalid(invalid_set):
    with open(INVALID_FILE, "w") as f:
        json.dump(list(invalid_set), f, indent=2)


all_jobs = []

for c in COUNTRIES:
    print(f"Scraping Indeed for {c['label']}...")
    try:
        jobs = scrape_jobs(
            site_name="indeed",
            search_term=FINAL_SEARCH_TERM,
            location=c["location"],
            country_indeed=c["country_indeed"],
            job_type=JOB_TYPE,
            hours_old=HOURS_OLD,
            results_wanted=RESULTS_WANTED_PER_COUNTRY,
        )
        jobs["country_label"] = c["label"]
        print(f"  Found {len(jobs)} jobs in {c['label']}")
        all_jobs.append(jobs)
    except Exception as e:
        print(f"  Failed to scrape {c['label']}: {e}")

if not all_jobs:
    print("No jobs found for any country. Exiting.")
    raise SystemExit(0)

jobs = pd.concat(all_jobs, ignore_index=True)
print(f"\nTotal jobs found across all countries: {len(jobs)}")

columns_to_show = [
    "site", "job_url", "job_url_direct", "title", "company",
    "location", "date_posted", "job_type", "country_label",
]
jobs_filtered = jobs[columns_to_show].copy()

# Drop duplicate job URLs (a job could theoretically surface twice)
jobs_filtered = jobs_filtered.drop_duplicates(subset=["job_url"]).reset_index(drop=True)

# Exclude previously applied or invalid jobs (matched by job_url)
applied = load_applied()
invalid = load_invalid()
excluded_urls = applied.union(invalid)
jobs_filtered = jobs_filtered[~jobs_filtered["job_url"].isin(excluded_urls)].reset_index(drop=True)
print(
    f"Showing {len(jobs_filtered)} jobs after excluding {len(applied)} applied and {len(invalid)} invalid jobs"
)

# Per-country counts for the stats bar
country_counts = jobs_filtered["country_label"].value_counts().to_dict()
country_badges_html = "".join(
    f'<div class="stat-badge">{label}: <strong>{count}</strong></div>'
    for label, count in country_counts.items()
)

# Build filter buttons dynamically from the countries configured above
filter_buttons_html = '<button class="filter-btn active" data-country="all" onclick="filterCountry(\'all\')">All</button>'
for c in COUNTRIES:
    filter_buttons_html += (
        f'<button class="filter-btn" data-country="{c["label"]}" '
        f'onclick="filterCountry(\'{c["label"]}\')">{c["label"]}</button>'
    )

# Build HTML with styling and mark-applied functionality
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

    url_link = f'<a href="{job_url}" target="_blank">View</a>' if job_url else ""
    direct_link = f'<a href="{job_url_direct}" target="_blank">Direct</a>' if job_url_direct else ""

    # NOTE: we no longer pass the raw URL into the onclick attribute.
    # Embedding a JSON/double-quoted URL string inside an already
    # double-quoted HTML attribute broke the markup (the first quote
    # inside the URL prematurely closed the attribute), which is why
    # "Invalid" (and, less obviously, "Mark Applied") stopped working.
    # The row's data-url attribute already carries the URL, so the JS
    # functions below just read it from there via idx.
    rows_html += f"""
    <tr id="row-{idx}" data-url="{job_url}" data-country="{country_label}">
        <td><span class="country-tag">{country_label}</span></td>
        <td>{row["site"]}</td>
        <td>{url_link}</td>
        <td>{direct_link}</td>
        <td class="title-col">{title}</td>
        <td>{company}</td>
        <td>{location}</td>
        <td>{date_posted}</td>
        <td>{job_type}</td>
        <td>
            <button class="btn-apply" onclick="markApplied({idx})">Mark Applied</button>
            <button class="btn-invalid" onclick="markInvalid({idx})">Invalid</button>
        </td>
    </tr>"""

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Indeed Jobs - Cloud/DevOps Engineer</title>
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
        .btn-invalid-save {{
            background: #2563eb;
            color: #fff;
            border: none;
            padding: 10px 24px;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.2s;
        }}
        .btn-invalid-save:hover {{ background: #1d4ed8; }}
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
        .btn-invalid {{
            background: #f59e0b;
            color: #fff;
            border: none;
            padding: 6px 14px;
            border-radius: 5px;
            font-size: 12px;
            cursor: pointer;
            transition: background 0.2s;
            margin-left: 8px;
        }}
        .btn-invalid:hover {{ background: #d97706; }}
        .btn-invalid:disabled, .btn-apply:disabled {{
            opacity: 0.7;
            cursor: default;
        }}
        tr.invalid {{
            opacity: 0.45;
            filter: blur(0.5px);
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Job Listings — Cloud & DevOps Engineer</h1>
        <p>Indeed &bull; UK, Ireland &amp; New Zealand &bull; Fulltime &bull; Last 30 days</p>
    </div>
    <div class="stats">
        <div class="stat-badge">Total found: <strong>{len(jobs)}</strong></div>
        <div class="stat-badge">Showing: <strong>{len(jobs_filtered)}</strong></div>
        <div class="stat-badge">Already applied: <strong>{len(applied)}</strong></div>
        <div class="stat-badge">Invalid jobs: <strong>{len(invalid)}</strong></div>
        {country_badges_html}
    </div>
    <div class="controls">
        <div class="filter-group">
            {filter_buttons_html}
        </div>
        <button class="btn-save" onclick="saveApplied()">Save Applied Jobs</button>
        <button class="btn-invalid-save" onclick="saveInvalid()">Save Invalid Jobs</button>
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
        let appliedJobs = JSON.parse(localStorage.getItem('indeedApplied') || '[]');
        let invalidJobs = JSON.parse(localStorage.getItem('indeedInvalid') || '[]');

        // Restore applied state on page load
        appliedJobs.forEach(url => {{
            document.querySelectorAll('tr[data-url]').forEach(row => {{
                if (row.dataset.url === url) {{
                    row.classList.add('applied');
                    const applyButton = row.querySelector('.btn-apply');
                    if (applyButton) {{
                        applyButton.textContent = 'Applied';
                        applyButton.disabled = true;
                    }}
                    const invalidButton = row.querySelector('.btn-invalid');
                    if (invalidButton) {{
                        invalidButton.disabled = true;
                    }}
                }}
            }});
        }});

        // Restore invalid state on page load
        invalidJobs.forEach(url => {{
            document.querySelectorAll('tr[data-url]').forEach(row => {{
                if (row.dataset.url === url) {{
                    row.classList.add('invalid');
                    const invalidButton = row.querySelector('.btn-invalid');
                    if (invalidButton) {{
                        invalidButton.textContent = 'Invalid';
                        invalidButton.disabled = true;
                    }}
                    const applyButton = row.querySelector('.btn-apply');
                    if (applyButton) {{
                        applyButton.disabled = true;
                    }}
                }}
            }});
        }});

        // Both handlers now take only the row index and read the URL
        // straight off the row's data-url attribute — no more passing
        // a raw URL string through an inline onclick attribute.
        function markApplied(idx) {{
            const row = document.getElementById('row-' + idx);
            const url = row.dataset.url;
            if (row.classList.contains('applied')) return;
            row.classList.remove('invalid');
            row.classList.add('applied');
            const applyButton = row.querySelector('.btn-apply');
            if (applyButton) {{
                applyButton.textContent = 'Applied';
                applyButton.disabled = true;
            }}
            const invalidButton = row.querySelector('.btn-invalid');
            if (invalidButton) {{
                invalidButton.disabled = true;
            }}
            if (!appliedJobs.includes(url)) {{
                appliedJobs.push(url);
                localStorage.setItem('indeedApplied', JSON.stringify(appliedJobs));
            }}
        }}

        function markInvalid(idx) {{
            const row = document.getElementById('row-' + idx);
            const url = row.dataset.url;
            if (row.classList.contains('invalid')) return;
            row.classList.add('invalid');
            const invalidButton = row.querySelector('.btn-invalid');
            if (invalidButton) {{
                invalidButton.textContent = 'Invalid';
                invalidButton.disabled = true;
            }}
            const applyButton = row.querySelector('.btn-apply');
            if (applyButton) {{
                applyButton.disabled = true;
            }}
            if (!invalidJobs.includes(url)) {{
                invalidJobs.push(url);
                localStorage.setItem('indeedInvalid', JSON.stringify(invalidJobs));
            }}
        }}

        function saveApplied() {{
            const blob = new Blob([JSON.stringify(appliedJobs, null, 2)], {{type: 'application/json'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'applied_jobs.json';
            a.click();
            alert('Downloaded applied_jobs.json — place it next to indeed.py to exclude these jobs on next run.');
        }}

        function saveInvalid() {{
            const blob = new Blob([JSON.stringify(invalidJobs, null, 2)], {{type: 'application/json'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'invalid_jobs.json';
            a.click();
            alert('Downloaded invalid_jobs.json — place it next to indeed.py to exclude these jobs on next run.');
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
print(f"Opening in browser...")