import time
import json
import os
import requests
from playwright.sync_api import sync_playwright

# [Antigravity Omega] 全球算力账户工厂 V2.0
# 目标：自动化注册高价值算力平台 (Together.ai, Groq 等)，实现弹药无限化。

ARSENAL_FILE = r"e:\享中\arsenal.json"

def generate_random_identity():
    # 模拟随机身份信息
    resp = requests.get("https://randomuser.me/api/").json()
    user = resp['results'][0]
    return {
        "email": f"{user['login']['username']}@example.com", # 实际应使用临时邮箱 API
        "password": "Antigravity_Omega_2099!",
        "name": f"{user['name']['first']} {user['name']['last']}"
    }

def register_together_ai():
    print("[FACTORY] Starting Together.ai production line...")
    identity = generate_random_identity()
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        page = browser.new_page()
        
        page.goto("https://api.together.xyz/signup")
        print(f"[1/4] Identity: {identity['email']}")
        
        page.fill('input[name="email"]', identity['email'])
        page.fill('input[name="password"]', identity['password'])
        
        print("[WAIT] Please complete CAPTCHA and Signup. System will wait FOREVER.")
        page.wait_for_selector("text=API Keys", timeout=0) # 无限期等待
        
        print("[2/4] Harvesting Keys...")

        key_element = page.query_selector("code")
        if key_element:
            new_key = key_element.inner_text().strip()
            print(f"🔥 [VICTORY] 捕获 Together AI Key: {new_key[:10]}...")
            
            # 存入矿山
            arsenal = []
            if os.path.exists(ARSENAL_FILE):
                with open(ARSENAL_FILE, "r") as f:
                    arsenal = json.load(f)
            if new_key not in arsenal:
                arsenal.append(new_key)
                with open(ARSENAL_FILE, "w") as f:
                    json.dump(arsenal, f, indent=4)
        
        print("[SUCCESS] Production Complete. Browser kept open for manual review.")
        while True: time.sleep(100)

if __name__ == "__main__":
    register_together_ai()
