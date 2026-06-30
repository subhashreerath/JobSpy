import cloudscraper
import json

print("=" * 60)
print("Testing Glassdoor with cloudscraper")
print("=" * 60)

scraper = cloudscraper.create_scraper()

try:
    print("\n1. Testing basic page access...")
    response = scraper.get("https://www.glassdoor.de/Job/index.htm", timeout=30)
    print(f"   Status: {response.status_code}")
    
    if response.status_code == 200:
        print("   ✓ Successfully bypassed Cloudflare!")
        print(f"   Content length: {len(response.text)} bytes")
        
        # Check page content
        if "glassdoor" in response.text.lower():
            print("   ✓ Glassdoor content found")
        if "job" in response.text.lower():
            print("   ✓ Job search elements found")
    
    print("\n2. Testing GraphQL API endpoint...")
    headers = {
        "Content-Type": "application/json",
        "apollographql-client-name": "job-search-next",
        "apollographql-client-version": "4.65.5",
    }
    
    payload = [{
        "operationName": "JobSearchResultsQuery",
        "variables": {
            "keyword": "Cloud Engineer",
            "locationId": 2826,  # Germany
            "locationType": "C",
            "numPerPage": 10,
            "pageNumber": 1,
        },
        "query": "query { test }"
    }]
    
    api_response = scraper.post(
        "https://www.glassdoor.de/graph",
        headers=headers,
        json=payload,
        timeout=30
    )
    
    print(f"   API Status: {api_response.status_code}")
    if api_response.status_code == 200:
        print("   ✓ API accessible!")
        print(f"   Response preview: {api_response.text[:200]}...")
    else:
        print(f"   Response: {api_response.text[:300]}...")
    
except Exception as e:
    print(f"   ✗ Error: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
