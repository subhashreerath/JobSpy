import requests
from jobspy.glassdoor import Glassdoor
from jobspy.util import create_session
from jobspy.glassdoor.constant import headers, fallback_token

# Test connection to Glassdoor API
print("=" * 60)
print("Testing Glassdoor API Connection")
print("=" * 60)

base_url = "https://www.glassdoor.de"
print(f"\n1. Testing base URL: {base_url}")
try:
    response = requests.get(base_url, timeout=10)
    print(f"   Status: {response.status_code}")
    print(f"   ✓ Base URL accessible")
except Exception as e:
    print(f"   ✗ Error: {e}")

print(f"\n2. Testing GraphQL endpoint: {base_url}/graph")
try:
    session = create_session(proxies=None, ca_cert=None, has_retry=True)
    session.headers.update(headers)
    
    # Try simple HEAD request first
    response = session.head(f"{base_url}/graph", timeout_seconds=10)
    print(f"   HEAD Status: {response.status_code}")
except Exception as e:
    print(f"   ✗ Error: {e}")

print(f"\n3. Testing CSRF token fetch")
try:
    session = create_session(proxies=None, ca_cert=None, has_retry=True)
    res = session.get(f"{base_url}/Job/computer-science-jobs.htm", timeout_seconds=10)
    print(f"   Status: {res.status_code}")
    print(f"   ✓ Token page accessible")
except Exception as e:
    print(f"   ✗ Error: {e}")

print(f"\n4. Checking DNS resolution")
import socket
try:
    ip = socket.gethostbyname("www.glassdoor.de")
    print(f"   ✓ DNS resolved: {ip}")
except Exception as e:
    print(f"   ✗ DNS Error: {e}")

print("\n" + "=" * 60)
