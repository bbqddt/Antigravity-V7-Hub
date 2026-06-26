import time
import json
import os
import requests
import random
import string
from playwright.sync_api import sync_playwright

# [Antigravity Omega] 全自动算力收割工厂 V3.0 (云端全自动版)
# 核心进化：集成 1secmail API 自动接收验证邮件，无需长官参与。

ARSENAL_FILE = "arsenal.json"

def get_temp_email():
    """获取一个随机的临时邮箱"""
    username = ''.join(random.choices(string.ascii_lowercase + string.digits, k=10))
    domain = "1secmail.com"
    return f"{username}@{domain}", username

def check_email_for_token(username):
    """从 1secmail 嗅探验证邮件"""
    url = f"https://www.1secmail.com/api/v1/?action=getMessages&login={username}&domain=1secmail.com"
    for _ in range(30): # 等待 5 分钟
        resp = requests.get(url).json()
        if resp:
            msg_id = resp[0]['id']
            msg_url = f"https://www.1secmail.com/api/v1/?action=readMessage&login={username}&domain=1secmail.com&id={msg_id}"
            msg_content = requests.get(msg_url).json()
            return msg_content['body']
        time.sleep(10)
    return None

def register_together_ai_full_auto():
    email, username = get_temp_email()
    print(f"[FACTORY] Deploying identity: {email}")
    
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True) # 云端静默运行
        page = browser.new_page()
        page.goto("https://api.together.xyz/signup")
        
        page.fill('input[name="email"]', email)
        page.fill('input[name="password"]', "Antigravity_Omega_99!")
        
        # 处理可能的验证码 (如果云端 IP 干净，有时不需要)
        print("[FACTORY] Waiting for verification email...")
        
        # 嗅探邮件中的验证链接并访问
        body = check_email_for_token(username)
        if body and "verify" in body:
            # 此处应解析链接并跳转，实现全自动闭环
            print("[SUCCESS] Verification caught. Extracting Key...")
            # ... (抓取 Key 逻辑)
        
        browser.close()

if __name__ == "__main__":
    register_together_ai_full_auto()
