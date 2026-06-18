import time
import requests
import os
from playwright.sync_api import sync_playwright

# --- 1. 自动化任务配置中心 ---
# 以后增加新网站，只需在这里加一行，无需改动下方核心逻辑
TASKS = {
    "ngrok.com": {
        "name": "收割 ngrok 令牌",
        "save_to": r"E:\享中\ngrok_token.txt",
        "selector": 'input[readonly][type="password"], input#authtoken'
    },
    "openrouter.ai": {
        "name": "注入 OpenRouter Key",
        "key": "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",
        "selector": 'input[placeholder*="Key"], textarea'
    }
}

def get_ws_endpoint():
    """获取反重力浏览器的调试链路"""
    try:
        res = requests.get("http://127.0.0.1:9222/json/version", timeout=2)
        return res.json()['webSocketDebuggerUrl']
    except:
        return None

def execute_logic(page, url):
    """自动化引擎：根据当前网址自动匹配并执行任务"""
    for domain, config in TASKS.items():
        if domain in url:
            try:
                # 寻找页面上的目标元素
                target = page.locator(config["selector"]).first
                if not target.is_visible():
                    continue

                # 任务类型 A：提取数据并存盘 (例如 ngrok)
                if domain == "ngrok.com":
                    val = target.input_value()
                    if val and len(val) > 20:
                        with open(config["save_to"], "w") as f:
                            f.write(val)
                        # 终端实时反馈
                        print(f"\r✅ [{config['name']}] 成功捕获并同步至文件", end="")

                # 任务类型 B：自动填表 (例如 OpenRouter)
                elif domain == "openrouter.ai" and target.is_editable():
                    if not target.input_value():
                        target.fill(config["key"])
                        target.press("Enter")
                        print(f"\n⚡ [{config['name']}] API Key 已自动注入！")
            except:
                pass

def main():
    print("="*50)
    print("🚀 反重力 IDE 全能监控模式 - 已启动")
    print("🚦 逻辑：只需保持运行，切换网页即自动执行任务")
    print("="*50)

    while True:
        ws_url = get_ws_endpoint()
        if not ws_url:
            print("\r💤 等待浏览器开启调试模式 (9222)...", end="")
            time.sleep(3)
            continue

        try:
            with sync_playwright() as p:
                # 接管已有的浏览器
                browser = p.chromium.connect_over_cdp(ws_url)
                ctx = browser.contexts[0]
                
                while True:
                    if not ctx.pages:
                        break
                    
                    # 同时巡逻所有打开的标签页
                    for page in ctx.pages:
                        execute_logic(page, page.url)
                    
                    # 降低 CPU 占用，每秒巡逻一次
                    time.sleep(1) 
        except Exception as e:
            print(f"\n⚠️ 链路中断或页面刷新: {e}")
            time.sleep(2)

if __name__ == "__main__":
    main()