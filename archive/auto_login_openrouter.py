import sys
import re
from playwright.sync_api import Playwright, sync_playwright, expect

def run(playwright: Playwright) -> None:
    # 禁用 headless 模式，确保你能看到浏览器界面进行登录操作
    browser = playwright.chromium.launch(headless=False)
    context = browser.new_context()
    page = context.new_page()
    
    print("正在连接 OpenRouter 矩阵...")
    page.goto("https://openrouter.ai/")
    
    # 提示用户手动操作
    print("⚠️  请在弹出的浏览器窗口中完成登录操作。")
    print("脚本将保持运行 10 分钟以供你完成身份校验。")
    
    # 保持窗口开启 600 秒 (10分钟)，让你有充裕时间登录
    page.wait_for_timeout(600000) 

    context.close()
    browser.close()

if __name__ == "__main__":
    with sync_playwright() as playwright:
        run(playwright)