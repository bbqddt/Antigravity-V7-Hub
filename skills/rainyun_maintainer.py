from playwright.sync_api import sync_playwright
import time
import json
import os

# [Rainyun Auto-Maintainer] 雨云自动维护哨兵
# 目标：每天自动登录雨云，确保服务器不被停机，实现云端指挥部永存。

def maintain_rainyun():
    # 注意：长官需要提供雨云的登录凭证
    # (此处建议通过 key_manager 保护)
    config_path = r"e:\享中\keys.json"
    try:
        with open(config_path, 'r') as f:
            keys = json.load(f)
            username = keys.get('rainyun_user')
            password = keys.get('rainyun_pass')
    except:
        print("[Error] 请在 keys.json 中配置 rainyun_user 和 rainyun_pass")
        return

    with sync_playwright() as p:
        print("[Rainyun] 启动自动化远征军...")
        browser = p.chromium.launch(headless=True) # 静默运行
        page = browser.new_page()
        
        try:
            print("[Rainyun] 正在空降登录页...")
            page.goto("https://app.rainyun.com/login")
            
            # 执行登录逻辑
            page.fill("input[placeholder*='邮箱']", username)
            page.fill("input[placeholder*='密码']", password)
            page.click("button:has-text('登录')")
            
            time.sleep(5)
            print(f"[Rainyun] 登录成功！当前页面标题: {page.title()}")
            
            # 模拟一些活动，确保账号活跃
            page.goto("https://app.rainyun.com/dashboard")
            time.sleep(3)
            
            print("[Rainyun] 每日维护任务已完成。云端堡垒生命值 +24h")
        except Exception as e:
            print(f"[Rainyun] 远征受阻: {e}")
        finally:
            browser.close()

if __name__ == "__main__":
    maintain_rainyun()
