import requests
import webbrowser
import os
import json
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APPLIED_FILE = os.path.join(SCRIPT_DIR, "applied_jobs_arbeitnow.json")
EXCLUDED_FILE = os.path.join(SCRIPT_DIR, "excluded_keywords_arbeitnow.json")
HTML_FILE = os.path.join(SCRIPT_DIR, "arbeitnow_jobs.html")
API_URL = "https://www.arbeitnow.com/api/job-board-api"

SEARCH_KEYWORDS = [
    "cloud engineer",
    "devops",
    "platform engineer",
    "site reliability",
    "aws engineer",
    "azure engineer",
    "devops engineer",
    "cloud architect"
]

# Hardcoded default exclusions
DEFAULT_EXCLUDE_KEYWORDS = [
    "data engineer",
    "data science",
    "machine learning",
    "SAP",
    "Senior Data Engineer",
    "Data Platform Engineer",
    "Senior Full Stack Developer",
    "Senior SAP BTP Developer",
    "Senior SAP Cloud Developer"
    # Add more exclusion keywords here as needed
]

MAX_PAGES = 50


def load_applied():
    if os.path.exists(APPLIED_FILE):
        with open(APPLIED_FILE, "r") as f:
            return set(json.load(f))
    return set()


def load_excluded_keywords():
    """Load both default and user-added exclusion keywords"""
    excluded = set(DEFAULT_EXCLUDE_KEYWORDS)
    if os.path.exists(EXCLUDED_FILE):
        try:
            with open(EXCLUDED_FILE, "r") as f:
                user_excluded = json.load(f)
                if isinstance(user_excluded, list):
                    excluded.update(user_excluded)
        except (json.JSONDecodeError, IOError):
            pass
    return excluded


def fetch_jobs():
    all_jobs = []
    for page in range(1, MAX_PAGES + 1):
        print(f"Fetching page {page}...")
        resp = requests.get(API_URL, params={"page": page}, timeout=30)
        if resp.status_code != 200:
            print(f"  Got status {resp.status_code}, stopping.")
            break
        data = resp.json().get("data", [])
        if not data:
            break
        all_jobs.extend(data)
    print(f"Fetched {len(all_jobs)} total jobs from API")
    return all_jobs


def matches_keywords(job):
    title = job.get("title", "").lower()
    tags = " ".join(job.get("tags", [])).lower()
    description = job.get("description", "").lower()
    searchable = f"{title} {tags}"
    # Check title and tags first (fast), fall back to description for broader match
    for kw in SEARCH_KEYWORDS:
        if kw in searchable:
            return True
    for kw in SEARCH_KEYWORDS:
        if kw in description:
            return True
    return False

def should_exclude(job, exclude_keywords):
    """Check if job matches any exclusion keywords"""
    title = job.get("title", "").lower()
    tags = " ".join(job.get("tags", [])).lower()
    description = job.get("description", "").lower()
    
    # Check title and tags first (higher priority for exclusion)
    for kw in exclude_keywords:
        kw_lower = kw.lower()
        if kw_lower in title or kw_lower in tags:
            return True
    
    # Fall back to description search (to avoid false positives)
    for kw in exclude_keywords:
        kw_lower = kw.lower()
        if kw_lower in description:
            return True
    
    return False

def format_date(timestamp):
    try:
        return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d")
    except (TypeError, ValueError, OSError):
        return ""


# Fetch and filter
all_jobs = fetch_jobs()
matched_jobs = [j for j in all_jobs if matches_keywords(j)]

# Load exclusion keywords
exclude_keywords = load_excluded_keywords()

# Exclude jobs with exclusion keywords
excluded_jobs = [j for j in matched_jobs if should_exclude(j, exclude_keywords)]
filtered_by_exclusion = [j for j in matched_jobs if not should_exclude(j, exclude_keywords)]

print(f"Matched {len(matched_jobs)} keyword jobs, excluded {len(excluded_jobs)} with exclusion keywords")
if excluded_jobs and len(excluded_jobs) <= 5:
    print("Excluded jobs:")
    for job in excluded_jobs:
        print(f"  - {job.get('title')} at {job.get('company_name')}")

# Deduplicate by URL
seen = set()
unique_jobs = []
for job in filtered_by_exclusion:
    url = job.get("url", "")
    if url and url not in seen:
        seen.add(url)
        unique_jobs.append(job)

print(f"After deduplication: {len(unique_jobs)} Cloud/DevOps/Platform jobs")

# Exclude applied
applied = load_applied()
filtered_jobs = [j for j in unique_jobs if j.get("url", "") not in applied]
print(f"Showing {len(filtered_jobs)} after excluding {len(applied)} previously applied")

# Build HTML
rows_html = ""
for idx, job in enumerate(filtered_jobs):
    url = job.get("url", "")
    title = job.get("title", "")
    company = job.get("company_name", "")
    location = job.get("location", "")
    remote = "Remote" if job.get("remote") else ""
    tags = ", ".join(job.get("tags", []))
    date = format_date(job.get("created_at"))
    job_types = ", ".join(job.get("job_types", []))

    location_display = f"{location}"
    if remote:
        location_display += ' <span class="remote-tag">Remote</span>'

    rows_html += f"""
    <tr id="row-{idx}" data-url="{url}">
        <td class="title-col"><a href="{url}" target="_blank">{title}</a></td>
        <td>{company}</td>
        <td>{location_display}</td>
        <td><span class="tags">{tags}</span></td>
        <td>{job_types}</td>
        <td>{date}</td>
        <td><button class="btn-apply" onclick="markApplied({idx}, '{url}')">Mark Applied</button></td>
    </tr>"""

# Format exclude keywords for display
excluded_list_html = ""
for kw in sorted(exclude_keywords):
    excluded_list_html += f'<span class="excluded-tag">{kw} <button class="btn-remove-exclude" onclick="removeExclude(\'{kw}\')">✕</button></span>'

html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Arbeitnow Jobs - Cloud/DevOps/Platform Engineer</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f172a;
            padding: 30px;
            color: #e2e8f0;
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
        }}
        .header h1 {{
            font-size: 28px;
            color: #f8fafc;
            margin-bottom: 8px;
        }}
        .header p {{
            color: #94a3b8;
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
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 8px;
            padding: 10px 20px;
            font-size: 14px;
        }}
        .stat-badge strong {{ color: #38bdf8; }}
        .controls {{
            text-align: center;
            margin-bottom: 30px;
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
            margin-right: 10px;
        }}
        .btn-save:hover {{ background: #059669; }}
        
        /* Exclusion Management Section */
        .exclusion-section {{
            background: #1e293b;
            border: 1px solid #334155;
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 30px;
        }}
        .exclusion-section h3 {{
            color: #f8fafc;
            font-size: 16px;
            margin-bottom: 15px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}
        .exclusion-input-group {{
            display: flex;
            gap: 10px;
            margin-bottom: 15px;
            flex-wrap: wrap;
        }}
        .exclusion-input-group input {{
            flex: 1;
            min-width: 250px;
            background: #0f172a;
            border: 1px solid #334155;
            border-radius: 6px;
            padding: 10px 14px;
            color: #e2e8f0;
            font-size: 14px;
        }}
        .exclusion-input-group input::placeholder {{
            color: #64748b;
        }}
        .exclusion-input-group input:focus {{
            outline: none;
            border-color: #38bdf8;
        }}
        .btn-add-exclude {{
            background: #f59e0b;
            color: #fff;
            border: none;
            padding: 10px 20px;
            border-radius: 6px;
            font-size: 14px;
            cursor: pointer;
            transition: background 0.2s;
            white-space: nowrap;
        }}
        .btn-add-exclude:hover {{ background: #d97706; }}
        
        .excluded-keywords {{
            display: flex;
            flex-wrap: wrap;
            gap: 8px;
        }}
        .excluded-tag {{
            background: #7c3aed;
            color: #fff;
            padding: 6px 12px;
            border-radius: 20px;
            font-size: 13px;
            display: inline-flex;
            align-items: center;
            gap: 6px;
        }}
        .btn-remove-exclude {{
            background: none;
            border: none;
            color: #fff;
            cursor: pointer;
            font-size: 16px;
            padding: 0;
            line-height: 1;
        }}
        .btn-remove-exclude:hover {{
            opacity: 0.7;
        }}
        
        table {{
            width: 100%;
            border-collapse: collapse;
            background: #1e293b;
            border-radius: 12px;
            overflow: hidden;
            box-shadow: 0 4px 12px rgba(0,0,0,0.3);
        }}
        thead {{
            background: #7c3aed;
        }}
        th {{
            padding: 14px 16px;
            text-align: left;
            font-weight: 600;
            font-size: 13px;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #fff;
        }}
        td {{
            padding: 12px 16px;
            border-bottom: 1px solid #334155;
            font-size: 14px;
        }}
        tr:hover {{ background: #334155; }}
        tr.applied {{
            background: #064e3b !important;
            opacity: 0.6;
        }}
        tr.applied .btn-apply {{
            background: #475569;
            cursor: default;
        }}
        tr.applied .btn-apply::after {{ content: " ✓"; }}
        .title-col {{ font-weight: 500; max-width: 300px; }}
        .title-col a {{
            color: #38bdf8;
            text-decoration: none;
            font-weight: 500;
        }}
        .title-col a:hover {{ text-decoration: underline; color: #7dd3fc; }}
        .remote-tag {{
            background: #065f46;
            color: #6ee7b7;
            padding: 2px 8px;
            border-radius: 10px;
            font-size: 11px;
            font-weight: 600;
            margin-left: 6px;
        }}
        .tags {{
            color: #94a3b8;
            font-size: 12px;
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
            color: #94a3b8;
        }}
    </style>
</head>
<body>
    <div class="header">
        <h1>Arbeitnow — Job Listings</h1>
        <p>Cloud &bull; DevOps &bull; Platform &bull; SRE &bull; Infrastructure &bull; Kubernetes &bull; AWS &bull; Azure</p>
    </div>
    <div class="stats">
        <div class="stat-badge">Total from API: <strong>{len(all_jobs)}</strong></div>
        <div class="stat-badge">Matched keywords: <strong>{len(matched_jobs)}</strong></div>
        <div class="stat-badge">After exclusions: <strong>{len(unique_jobs)}</strong></div>
        <div class="stat-badge">Showing: <strong>{len(filtered_jobs)}</strong></div>
        <div class="stat-badge">Already applied: <strong>{len(applied)}</strong></div>
    </div>
    
    <div class="exclusion-section">
        <h3>🚫 Manage Exclusion Keywords</h3>
        <div class="exclusion-input-group">
            <input type="text" id="excludeInput" placeholder="Enter role or keyword to exclude (e.g., 'data engineer')" />
            <button class="btn-add-exclude" onclick="addExclude()">Add Exclusion</button>
            <button class="btn-save" onclick="saveExclusions()">Save to File</button>
        </div>
        <div class="excluded-keywords" id="excludedList">
            {excluded_list_html}
        </div>
    </div>
    
    <div class="controls">
        <button class="btn-save" onclick="saveApplied()">Save Applied Jobs</button>
        <button class="btn-save" style="background: #ef4444;" onclick="resetLocalStorage()">Reset Applied (Clear Local Data)</button>
    </div>
    
    {"<table><thead><tr><th>Title</th><th>Company</th><th>Location</th><th>Tags</th><th>Type</th><th>Posted</th><th>Action</th></tr></thead><tbody>" + rows_html + "</tbody></table>" if filtered_jobs else '<div class="empty-state"><h2>No new jobs found</h2><p>All matched listings have been marked as applied, or no results matched your keywords.</p></div>'}

    <script>
        let appliedJobs = JSON.parse(localStorage.getItem('arbeitnowApplied') || '[]');
        let excludedKeywords = JSON.parse(localStorage.getItem('arbeitnowExcluded') || '[]');

        // Load applied jobs styling
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
                localStorage.setItem('arbeitnowApplied', JSON.stringify(appliedJobs));
            }}
        }}

        function addExclude() {{
            const input = document.getElementById('excludeInput');
            const keyword = input.value.trim().toLowerCase();
            
            if (!keyword) {{
                alert('Please enter a keyword');
                return;
            }}
            
            if (excludedKeywords.includes(keyword)) {{
                alert('This keyword is already excluded');
                return;
            }}
            
            excludedKeywords.push(keyword);
            localStorage.setItem('arbeitnowExcluded', JSON.stringify(excludedKeywords));
            input.value = '';
            updateExcludedList();
            alert('Exclusion added! Click "Save to File" to persist it permanently.');
        }}

        function removeExclude(keyword) {{
            excludedKeywords = excludedKeywords.filter(k => k !== keyword.toLowerCase());
            localStorage.setItem('arbeitnowExcluded', JSON.stringify(excludedKeywords));
            updateExcludedList();
        }}

        function updateExcludedList() {{
            const list = document.getElementById('excludedList');
            list.innerHTML = excludedKeywords.map(kw => 
                `<span class="excluded-tag">${{kw}} <button class="btn-remove-exclude" onclick="removeExclude('${{kw}}')">✕</button></span>`
            ).join('');
        }}

        function saveExclusions() {{
            const blob = new Blob([JSON.stringify(excludedKeywords, null, 2)], {{type: 'application/json'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'excluded_keywords_arbeitnow.json';
            a.click();
            alert('Downloaded excluded_keywords_arbeitnow.json — place it next to arbeitnow.py to persist these exclusions permanently.\\n\\nNext time you run the script, it will automatically load these exclusions.');
        }}

        function saveApplied() {{
            const blob = new Blob([JSON.stringify(appliedJobs, null, 2)], {{type: 'application/json'}});
            const a = document.createElement('a');
            a.href = URL.createObjectURL(blob);
            a.download = 'applied_jobs_arbeitnow.json';
            a.click();
            alert('Downloaded applied_jobs_arbeitnow.json — place it next to arbeitnow.py to exclude these jobs on next run.');
        }}

        function resetLocalStorage() {{
            if (confirm('This will clear all "Applied" markings from browser memory. Are you sure?')) {{
                appliedJobs = [];
                excludedKeywords = [];
                localStorage.removeItem('arbeitnowApplied');
                localStorage.removeItem('arbeitnowExcluded');
                alert('Browser data cleared! Refresh the page to see all jobs again.');
                location.reload();
            }}
        }}

        // Allow Enter key to add exclusion
        document.getElementById('excludeInput').addEventListener('keypress', function(e) {{
            if (e.key === 'Enter') addExclude();
        }});
    </script>
</body>
</html>"""

with open(HTML_FILE, "w") as f:
    f.write(html_content)

print(f"\nJobs saved to {HTML_FILE}")
webbrowser.open('file://' + os.path.realpath(HTML_FILE))
print("Opening in browser...")
