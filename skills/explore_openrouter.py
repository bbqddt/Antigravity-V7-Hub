import sys
import os
import time
from playwright.sync_api import sync_playwright

def explore_custom_model():
    print("--- [Consultant] Exploring OpenRouter Custom Model Settings ---")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False)
            page = browser.new_page()
            
            # 直接跳转到模型的管理和创建页面
            print("[Step 1] Accessing OpenRouter Settings...")
            page.goto("https://openrouter.ai/settings")
            
            # 等待长官观察
            print("[WAIT] Please check the sidebar for 'Models' or 'Custom Models'.")
            time.sleep(20)
            
            # 搜索可能的入口链接
            custom_links = page.query_selector_all("a")
            for link in custom_links:
                text = link.inner_text().lower()
                if "custom" in text or "provider" in text or "add" in text:
                    print(f"[FOUND] Potential Entry: {text} -> {link.get_attribute('href')}")
            
            print("[INFO] Exploration complete. Check the browser window.")
            time.sleep(30) # 保持窗口让长官看个够
            browser.close()
    except Exception as e:
        print(f"[ERROR] Exploration failed: {e}")

if __name__ == "__main__":
    explore_custom_model()
