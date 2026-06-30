import requests
import re

# More realistic browser headers
headers_browser = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
    "Accept-Encoding": "gzip, deflate, br",
    "DNT": "1",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1",
}

print("Testing different approaches to Glassdoor...")
print("=" * 60)

# Test 1: Regular requests without special headers
print("\n1. Regular requests (no special headers):")
try:
    response = requests.get("https://www.glassdoor.de/", timeout=10)
    print(f"   Status: {response.status_code}")
except Exception as e:
    print(f"   Error: {e}")

# Test 2: With browser headers
print("\n2. With browser headers:")
try:
    response = requests.get("https://www.glassdoor.de/", headers=headers_browser, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ Successfully accessed Glassdoor!")
except Exception as e:
    print(f"   Error: {e}")

# Test 3: Try /Job endpoint
print("\n3. Try /Job/index.htm:")
try:
    response = requests.get("https://www.glassdoor.de/Job/index.htm", headers=headers_browser, timeout=10)
    print(f"   Status: {response.status_code}")
    if response.status_code == 200:
        print(f"   ✓ Successfully accessed job page!")
        # Check for CSRF token
        pattern = r'"token":\s*"([^"]+)"'
        matches = re.findall(pattern, response.text)
        if matches:
            print(f"   Found CSRF token: {matches[0][:20]}...")
except Exception as e:
    print(f"   Error: {e}")

print("\n" + "=" * 60)
