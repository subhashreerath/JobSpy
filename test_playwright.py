import asyncio
from playwright.async_api import async_playwright
import re

async def test_glassdoor_with_playwright():
    print("=" * 60)
    print("Testing Glassdoor with Playwright")
    print("=" * 60)
    
    async with async_playwright() as p:
        # Launch browser
        print("\n1. Launching browser...")
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # Set user agent
        await page.context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => false,
            });
        """)
        
        try:
            print("2. Navigating to glassdoor.de...")
            await page.goto("https://www.glassdoor.de/Job/index.htm", wait_until="domcontentloaded", timeout=30000)
            print(f"   ✓ Page loaded successfully!")
            
            print("3. Checking page title...")
            title = await page.title()
            print(f"   Title: {title}")
            
            print("4. Looking for job listings...")
            # Wait for content to load
            try:
                await page.wait_for_selector('[data-test="jobcard"]', timeout=5000)
                job_cards = await page.locator('[data-test="jobcard"]').count()
                print(f"   ✓ Found {job_cards} job cards")
            except:
                print("   Note: Job cards not found immediately (may need search)")
            
            print("5. Checking HTML content length...")
            content = await page.content()
            print(f"   HTML content length: {len(content)} bytes")
            
            print("6. Looking for CSRF token...")
            # Check for token in page source
            if '"token"' in content:
                print("   ✓ Found token in page")
            
            print("\n✓ Playwright successfully accessed Glassdoor!")
            
        except Exception as e:
            print(f"   ✗ Error: {e}")
        
        finally:
            await browser.close()

# Run the test
asyncio.run(test_glassdoor_with_playwright())
