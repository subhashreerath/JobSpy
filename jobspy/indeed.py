from jobspy import scrape_jobs
import webbrowser
import os
import json
import pandas as pd

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APPLIED_FILE = os.path.join(SCRIPT_DIR, "applied_jobs.json")
HTML_FILE = os.path.join(SCRIPT_DIR, "indeed_jobs.html")


def load_applied():
    if os.path.exists(APPLIED_FILE):
        with open(APPLIED_FILE, "r") as f:
            return set(json.load(f))
    return set()


def save_applied(applied_set):
    with open(APPLIED_FILE, "w") as f:
        json.dump(list(applied_set), f, indent=2)


jobs = scrape_jobs(
    site_name="indeed",
    search_term="Cloud Engineer, DevOps Engineer",
    location="Deutschland",
    country_indeed="germany",
    job_type="fulltime",
    hours_old=720.0,
    results_wanted=500,
)

print(f"Found {len(jobs)} jobs")

columns_to_show = ["site", "job_url", "job_url_direct", "title", "company", "location", "date_posted", "job_type"]
jobs_filtered = jobs[columns_to_show].copy()

# Exclude previously applied jobs (matched by job_url)
applied = load_applied()
jobs_filtered = jobs_filtered[~jobs_filtered["job_url"].isin(applied)].reset_index(drop=True)
print(f"Showing {len(jobs_filtered)} jobs after excluding {len(applied)} previously applied")

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

    url_link = f'<a href="{job_url}" target="_blank">View</a>' if job_url else ""
    direct_link = f'<a href="{job_url_direct}" target="_blank">Direct</a>' if job_url_direct else ""

    rows_html += f"""
    <tr id="row-{idx}" data-url="{job_url}">
        <td>{row["site"]}</td>
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
        <p>Indeed Germany &bull; Fulltime &bull; Last 48 hours</p>
    </div>
    <div class="stats">
        <div class="stat-badge">Total found: <strong>{len(jobs)}</strong></div>
        <div class="stat-badge">Showing: <strong>{len(jobs_filtered)}</strong></div>
        <div class="stat-badge">Already applied: <strong>{len(applied)}</strong></div>
    </div>
    <div class="controls">
        <button class="btn-save" onclick="saveApplied()">Save Applied Jobs (update file)</button>
    </div>
    <table>
        <thead>
            <tr>
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

        // Restore applied state on page load
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
                localStorage.setItem('indeedApplied', JSON.stringify(appliedJobs));
            }}
        }}

        function saveApplied() {{
            // Download applied_jobs.json so user can replace the file
            const blob = new Blob([JSON.stringify(appliedJobs, null, 2)], {{type: 'application/json'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'applied_jobs.json';
            a.click();
            alert('Downloaded applied_jobs.json — place it next to indeed.py to exclude these jobs on next run.');
        }}
    </script>
</body>
</html>"""

with open(HTML_FILE, "w") as f:
    f.write(html_content)

print(f"Jobs saved to {HTML_FILE}")
webbrowser.open('file://' + os.path.realpath(HTML_FILE))
print(f"Opening in browser...")
