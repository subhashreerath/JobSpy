import asyncio
from playwright.async_api import async_playwright

async def search_jobs_glassdoor():
    print("=" * 60)
    print("Testing Job Search on Glassdoor with Playwright")
    print("=" * 60)
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        try:
            print("\n1. Navigating to glassdoor.de...")
            await page.goto("https://www.glassdoor.de", wait_until="load", timeout=30000)
            
            print("2. Waiting for page to settle...")
            await page.wait_for_timeout(3000)  # Wait 3 seconds
            
            print("3. Checking page content...")
            content = await page.content()
            with open("/tmp/glassdoor_page.html", "w") as f:
                f.write(content)
            print(f"   HTML saved to /tmp/glassdoor_page.html ({len(content)} bytes)")
            
            # Check for common elements
            print("\n4. Checking for page elements:")
            
            # Check for search boxes
            search_boxes = await page.locator('input[type="search"], input[placeholder*="search" i]').count()
            print(f"   Search inputs: {search_boxes}")
            
            # Check for title
            title = await page.title()
            print(f"   Page title: {title}")
            
            # Check for specific Glassdoor elements
            if "security" in title.lower() or "captcha" in content.lower():
                print("   ⚠️  Glassdoor security/captcha page detected")
            else:
                print("   ✓ Regular Glassdoor page")
            
            print("\n✓ Test completed!")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
            import traceback
            traceback.print_exc()
        
        finally:
            await browser.close()

# Run the test
asyncio.run(search_jobs_glassdoor())
