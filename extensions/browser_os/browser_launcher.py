#!/usr/bin/env python3
from playwright.sync_api import sync_playwright
import sys, time

def run_task(url, stay_open=False):
    with sync_playwright() as p:
        # Check if we should keep it open or just scrape
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        
        print(f"🌐 Navigating to {url}...")
        # ─── THE VERIFICATION STEP ───
        # 'networkidle' ensures the page isn't still downloading data in the background
        page.goto(url, wait_until="networkidle")
        
        # Verify specific element load (e.g., body)
        page.wait_for_selector("body")
        print("✅ Page Verified and Loaded.")
        
        title = page.title()
        print(f"📄 Result: {title}")
        
        if stay_open:
            print("⏳ Persistent Mode: Keeping browser active for 60s...")
            time.sleep(60) 
        
        browser.close()

if __name__ == "__main__":
    url_arg = sys.argv[1] if len(sys.argv) > 1 else "https://google.com"
    persist = "--persist" in sys.argv
    run_task(url_arg, stay_open=persist)
