import sys
import os

# Add local jobspy to path (use local version instead of installed package)
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from jobspy import scrape_jobs
import webbrowser
import pandas as pd

# Run JobSpy for Xing only
jobs = scrape_jobs(
    site_name="xing",  # Only Xing
    search_term="Cloud Engineer, DevOps Engineer, AWS, Terraform",  # Your keywords
    location="germany",  # Optional: location filter
    country_indeed="germany",  # Full country name for Indeed (required parameter)
    job_type="fulltime",  # Fulltime jobs only
    xing_cookies={
        "_session_id": "542f6c8df7b5645a46bd3250e2cb69fd",  # Add your _session_id cookie value
        "session_id": "35868b63-1db5-4367-abad-d140990860a1",
        "_scid": "PgHI6QbllIUfFhHeTGRfHzgWhG-Lh5RW",
        },  # Add your _session_id cookie value
    results_wanted=50,  # Number of results
)

print(f"Found {len(jobs)} jobs")
print(jobs.head())

# Check if any jobs were found
if len(jobs) == 0:
    print("No jobs found from Xing.")
    print("Xing may require authentication. Try adding cookies or use Indeed/Glassdoor/Google instead.")
    sys.exit(0)

# Select only desired columns
columns_to_show = ["site", "job_url", "job_url_direct", "title", "company", "location", "date_posted", "job_type"]
jobs_filtered = jobs[columns_to_show].copy()

# Make links clickable by converting URLs to HTML anchor tags
jobs_filtered["job_url"] = jobs_filtered["job_url"].apply(lambda x: f'<a href="{x}" target="_blank">View</a>' if pd.notna(x) else "")
jobs_filtered["job_url_direct"] = jobs_filtered["job_url_direct"].apply(lambda x: f'<a href="{x}" target="_blank">View</a>' if pd.notna(x) else "")

# Save to HTML and open in browser
html_file = "xing_jobs.html"
jobs_filtered.to_html(html_file, index=False, escape=False)
print(f"Jobs saved to {html_file}")

# Open in default browser
webbrowser.open('file://' + os.path.realpath(html_file))
print(f"Opening {html_file} in browser...")
