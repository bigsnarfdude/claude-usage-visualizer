#!/usr/bin/env python3
"""
Playwright test script to identify dashboard issues
"""

import asyncio
import os
from playwright.async_api import async_playwright
from pathlib import Path

async def test_dashboard():
    """Test the Claude dashboard for issues"""
    dashboard_path = Path("/Users/vincent/Downloads/fixed_dashboard.html")
    
    if not dashboard_path.exists():
        print("❌ Dashboard file not found. Generating first...")
        return False
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(headless=False, slow_mo=1000)
        context = await browser.new_context()
        page = await context.new_page()
        
        # Set up console logging to capture errors
        page.on("console", lambda msg: print(f"🖥️  CONSOLE: {msg.type}: {msg.text}"))
        page.on("pageerror", lambda error: print(f"❌ PAGE ERROR: {error}"))
        
        try:
            # Navigate to dashboard
            file_url = f"file://{dashboard_path.absolute()}"
            print(f"🌐 Loading dashboard: {file_url}")
            
            await page.goto(file_url, wait_until="networkidle")
            
            # Take screenshot
            await page.screenshot(path="/Users/vincent/Downloads/dashboard_test.png")
            print("📸 Screenshot saved as dashboard_test.png")
            
            # Check for basic elements
            print("🔍 Checking dashboard elements...")
            
            # Header check
            header = await page.query_selector("h1")
            if header:
                title = await header.inner_text()
                print(f"✅ Title found: {title}")
            else:
                print("❌ No title found")
            
            # Metrics bar check
            metrics = await page.query_selector_all(".metric-value")
            print(f"📊 Found {len(metrics)} metrics")
            
            for i, metric in enumerate(metrics):
                value = await metric.inner_text()
                print(f"   Metric {i+1}: {value}")
            
            # Chart containers check
            charts = await page.query_selector_all(".chart-container")
            print(f"📈 Found {len(charts)} chart containers")
            
            # Check for Chart.js
            chart_elements = await page.query_selector_all("canvas")
            print(f"🎨 Found {len(chart_elements)} canvas elements for charts")
            
            # Table check
            table = await page.query_selector(".conversations-table")
            if table:
                rows = await page.query_selector_all(".conversations-table tbody tr")
                print(f"📋 Found conversation table with {len(rows)} rows")
            else:
                print("❌ No conversation table found")
            
            # Check for JavaScript errors by evaluating some basic functionality
            print("🧪 Testing JavaScript functionality...")
            
            # Test if Chart.js is loaded
            chart_loaded = await page.evaluate("typeof Chart !== 'undefined'")
            print(f"📊 Chart.js loaded: {chart_loaded}")
            
            # Test if data variables are available
            conversations_data = await page.evaluate("typeof conversations !== 'undefined'")
            stats_data = await page.evaluate("typeof stats !== 'undefined'")
            print(f"💾 Conversations data available: {conversations_data}")
            print(f"💾 Stats data available: {stats_data}")
            
            # Test filter tabs
            filter_tabs = await page.query_selector_all(".filter-tab")
            print(f"🏷️  Found {len(filter_tabs)} filter tabs")
            
            if filter_tabs:
                print("🖱️  Testing filter tab click...")
                await filter_tabs[0].click()
                await page.wait_for_timeout(1000)
                print("✅ Filter tab clickable")
            
            # Wait a bit to see the final state
            await page.wait_for_timeout(3000)
            
            print("✅ Dashboard test completed successfully!")
            return True
            
        except Exception as e:
            print(f"❌ Error during testing: {e}")
            await page.screenshot(path="/Users/vincent/Downloads/dashboard_error.png")
            return False
            
        finally:
            await browser.close()

async def main():
    print("🚀 Starting Playwright dashboard test...")
    success = await test_dashboard()
    
    if success:
        print("🎉 Test completed! Check the screenshots for visual verification.")
    else:
        print("💥 Test failed! Check error messages above.")

if __name__ == "__main__":
    asyncio.run(main())