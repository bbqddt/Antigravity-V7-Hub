import sys
import os
import time
from playwright.sync_api import sync_playwright

# [Antigravity V100.0] Auto-Login & Key Retrieval (No Emoji Version)
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
TOKEN_FILE = str(_BASE_DIR / "token.txt")

def run_auto():
    print("--- [AutoOp] Initializing Playwright ---")
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=False) # 允许长官观测
            page = browser.new_page()
            
            print("[Step 1] Navigating to OpenRouter...")
            page.goto("https://openrouter.ai/keys")
            
            # 给予长官足够的时间进行人工登录干预 (60秒)
            print("[WAIT] Please ensure login is complete on the browser window.")
            time.sleep(40)
            
            # 尝试抓取第一个 API Key (基于页面的 selector)
            print("[Step 2] Attempting to retrieve Key...")
            try:
                # 寻找包含密钥的元素，这里使用常见的密钥前缀或选择器
                key_elements = page.query_selector_all("code")
                for el in key_elements:
                    val = el.inner_text().strip()
                    if val.startswith("sk-or-"):
                        with open(TOKEN_FILE, "w", encoding='utf-8') as f:
                            f.write(val)
                        print(f"[SUCCESS] Key saved to {TOKEN_FILE}")
                        browser.close()
                        return
                print("[WARNING] No valid Key found on page.")
            except Exception as inner_e:
                print(f"[ERROR] Inner grabber failed: {inner_e}")
            
            browser.close()
    except Exception as e:
        print(f"[CRITICAL] Playwright failure: {e}")

if __name__ == "__main__":
    run_auto()