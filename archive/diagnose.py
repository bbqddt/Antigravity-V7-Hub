import requests
import json
from pathlib import Path

print("=== Antigravity 网络诊断 ===")

# 自动定位项目根目录
_BASE_DIR = Path(__file__).resolve().parent

# 1. 测试直连 Telegram
print("\n[1] 测试直连 Telegram API...")
try:
    r = requests.get("https://api.telegram.org", timeout=8)
    print(f"    结果: OK ({r.status_code})")
    direct_ok = True
except Exception as e:
    print(f"    结果: FAILED - {e}")
    direct_ok = False

# 2. 测试代理端口
proxies_to_test = [10808, 7890, 1080, 10809, 1087, 8080, 8118]
working_proxy = None
for port in proxies_to_test:
    proxies = {"http": f"http://127.0.0.1:{port}", "https": f"http://127.0.0.1:{port}"}
    try:
        r = requests.get("https://api.telegram.org", proxies=proxies, timeout=5)
        print(f"[2] 代理端口 {port}: OK ({r.status_code})")
        working_proxy = port
        break
    except Exception as e:
        print(f"[2] 代理端口 {port}: DEAD")

# 3. 读取 Token
print("\n[3] 读取 TG Token...")
try:
    with open(_BASE_DIR / "token_tg.txt", "r") as f:
        config = json.load(f)
    token = config.get("token", "")
    chat_id = config.get("chat_id", "")
    print(f"    Token: {token[:20]}...")
    print(f"    Chat ID: {chat_id}")
except Exception as e:
    print(f"    Token 读取失败: {e}")
    exit(1)

# 4. 测试能否拿到 Bot updates
print("\n[4] 测试 Bot API 连通性...")
test_url = f"https://api.telegram.org/bot{token}/getMe"

proxies_to_use = None
if working_proxy:
    proxies_to_use = {"http": f"http://127.0.0.1:{working_proxy}", "https": f"http://127.0.0.1:{working_proxy}"}
elif direct_ok:
    proxies_to_use = None

try:
    r = requests.get(test_url, proxies=proxies_to_use, timeout=10)
    print(f"    Bot API: OK - {r.json()}")
except Exception as e:
    print(f"    Bot API: FAILED - {e}")

print("\n=== 诊断完成 ===")
print(f"直连可用: {direct_ok}")
print(f"可用代理端口: {working_proxy}")
