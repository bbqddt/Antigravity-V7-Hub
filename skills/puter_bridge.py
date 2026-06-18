import json
import os
import time
import re
import threading
import http.server
import socketserver
from playwright.sync_api import sync_playwright

# [Antigravity] Puter Bridge V2 - 正确的架构：本地 HTTP 服务器
# 核心修复：file:// 无法加载 CDN，必须通过 http://localhost 才能使 Puter.js 正常工作

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PORT = 18999
DECISION_FILE = os.path.join(BASE_DIR, "latest_puter_oracle.json")

def start_server():
    """在后台启动本地 HTTP 服务器"""
    handler = http.server.SimpleHTTPRequestHandler
    handler.log_message = lambda *args: None  # 静默日志
    with socketserver.TCPServer(("", PORT), handler) as httpd:
        httpd.serve_forever()

def fetch_puter_oracle():
    # 1. 启动本地服务器（后台线程）
    server_thread = threading.Thread(target=start_server, daemon=True)
    server_thread.start()
    time.sleep(1)
    print(f"[PUTER] Local server started at http://localhost:{PORT}")

    # 2. 用 Playwright 打开 http 版本的网关
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(f"http://localhost:{PORT}/PUTER_GATEWAY.html")

        # 3. 等待 Puter SDK 真正就绪（非固定睡眠）
        try:
            page.wait_for_function("() => typeof window.puter !== 'undefined'", timeout=30000)
            print("[PUTER] SDK loaded and ready. Injecting 26054 directive...")
        except:
            print("[ERROR] Puter SDK failed to load - check network/proxy.")
            browser.close()
            return None



        # 4. 注入指令
        page.evaluate("""
            puter.ai.chat('只输出JSON，不要任何说明。推演双色球26054期。格式: {"red":[n,n,n,n,n,n],"blue":n}')
            .then(res => {
                document.body.innerHTML += '<div id="oracle_result">' + res + '</div>';
            }).catch(err => {
                document.body.innerHTML += '<div id="oracle_result">ERROR:' + err + '</div>';
            });
        """)

        # 5. 等待结果（最多 90 秒）
        try:
            page.wait_for_selector("#oracle_result", timeout=90000)
            raw = page.inner_text("#oracle_result")
            print(f"[PUTER] Raw response: {raw[:200]}")
            
            match = re.search(r'\{.*?\}', raw, re.DOTALL)
            if match:
                data = json.loads(match.group(0))
                data["period"] = "26054"
                data["source"] = "Puter.js (Claude/GPT-4o Free)"
                with open(DECISION_FILE, "w") as f:
                    json.dump(data, f, indent=4)
                print(f"[SUCCESS] Oracle saved: {data}")
                return data
        except Exception as e:
            print(f"[ERROR] {e}")
        finally:
            browser.close()
    return None

if __name__ == "__main__":
    os.chdir(BASE_DIR)  # 必须切换到根目录，HTTP 服务器才能找到 HTML 文件
    result = fetch_puter_oracle()
    if result:
        print(f"[DONE] Puter oracle injected into system: {result}")
    else:
        print("[FAIL] Puter oracle not captured.")
