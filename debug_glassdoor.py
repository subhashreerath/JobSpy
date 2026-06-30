from jobspy import scrape_jobs
from jobspy.model import JobType, Country

# Try scraping with Indeed instead
print("=" * 50)
print("Testing Indeed")
print("=" * 50)

jobs = scrape_jobs(
    site_name="indeed",
    search_term="Cloud Engineer",
    location="Berlin",
    country="Germany",
    results_wanted=10,
)

print(f"Found {len(jobs)} jobs")
if len(jobs) > 0:
    print(jobs[['title', 'company', 'location']].head())
