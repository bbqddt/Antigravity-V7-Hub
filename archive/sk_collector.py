import sys
import json
import os
import time
from playwright.sync_api import sync_playwright

# [Antigravity Omega] API 自动收割机 V1.0
# 功能：自动登录 OpenRouter 并抓取当前账户下的所有有效 API Token
from pathlib import Path

_BASE_DIR = Path(__file__).resolve().parent.parent
KEYS_FILE = str(_BASE_DIR / "keys.json")

def harvest_tokens():
    print("🚀 [HARVEST] 启动 OpenRouter API 自动收割程序...")
    with sync_playwright() as p:
        # 使用持久化上下文，保留之前的登录状态
        user_data_dir = str(_BASE_DIR / "playwright_data")
        browser = p.chromium.launch_persistent_context(user_data_dir, headless=False)
        page = browser.new_page()
        
        print("[1/3] 正在渗透 OpenRouter 控制台...")
        page.goto("https://openrouter.ai/settings/keys")
        
        # 检查是否需要登录
        if "login" in page.url:
            print("⚠️  检测到需要身份校验，请在浏览器中完成登录。")
            page.wait_for_selector("text=Keys", timeout=300000) # 等待5分钟让用户登录

        print("[2/3] 正在扫描密钥特征区域...")
        time.sleep(5) # 等待异步数据加载
        
        # 尝试抓取页面上的 Key 信息 (根据 OpenRouter 的 DOM 结构提取)
        keys_elements = page.query_selector_all("code")
        tokens = []
        for el in keys_elements:
            txt = el.inner_text().strip()
            if txt.startswith("sk-or-"):
                tokens.append(txt)
                print(f"✅ 发现可用弹药: {txt[:10]}********")

        if tokens:
            print(f"[3/3] 成功捕获 {len(tokens)} 枚弹药！正在装填入库...")
            # 更新 keys.json
            current_keys = {}
            if os.path.exists(KEYS_FILE):
                with open(KEYS_FILE, "r") as f:
                    current_keys = json.load(f)
            
            # 我们取最新的第一个作为主输出，或者全部存起来
            current_keys["openrouter"] = tokens[0]
            current_keys["all_tokens"] = tokens
            
            with open(KEYS_FILE, "w") as f:
                json.dump(current_keys, f, indent=4)
            print("🔥 [VICTORY] 秘钥仓已同步更新。武器系统已满弹！")
        else:
            print("❌ 未能在页面上直接嗅探到 sk-or- 开头的密钥，请确保您已经创建了 Keys。")
            
        time.sleep(2)
        browser.close()

if __name__ == "__main__":
    harvest_tokens()
