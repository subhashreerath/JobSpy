import asyncio
from playwright.async_api import async_playwright
import json

async def fetch_via_playwright():
    print("=" * 60)
    print("Attempt: Fetch Glassdoor API via Playwright context")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("\n1. Loading Glassdoor home page...")
            await page.goto("https://www.glassdoor.de", wait_until="domcontentloaded", timeout=30000)
            
            print("2. Waiting for Cloudflare challenge...")
            await page.wait_for_timeout(5000)
            
            print("3. Checking current URL...")
            current_url = page.url
            print(f"   Current URL: {current_url}")
            
            print("4. Checking page title...")
            title = await page.title()
            print(f"   Page title: {title}")
            
            # If still on challenge page, try clicking "Check" or waiting for redirect
            if "moment" in title.lower():
                print("\n   Still on Cloudflare challenge, waiting for auto-resolution...")
                # Cloudflare sometimes auto-resolves after a delay
                await page.wait_for_load_state("networkidle", timeout=15000)
                await page.wait_for_timeout(3000)
                
                current_url = page.url
                title = await page.title()
                print(f"   After wait - URL: {current_url}")
                print(f"   After wait - Title: {title}")
            
            # Try to execute API call from browser context
            print("\n5. Attempting GraphQL API call from browser context...")
            
            # This would reuse cookies/session from browser
            api_response = await page.evaluate("""
            async () => {
                try {
                    const response = await fetch('https://www.glassdoor.de/graph', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'apollographql-client-name': 'job-search-next',
                        },
                        body: JSON.stringify([{
                            operationName: 'JobSearchResultsQuery',
                            variables: {},
                            query: 'query { test }'
                        }])
                    });
                    return {
                        status: response.status,
                        statusText: response.statusText
                    };
                } catch (e) {
                    return { error: e.message };
                }
            }
            """)
            
            print(f"   API Response: {json.dumps(api_response, indent=2)}")
            
        except Exception as e:
            print(f"   Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

asyncio.run(fetch_via_playwright())
