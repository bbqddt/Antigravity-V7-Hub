import requests
import json

class CloudflareBridge:
    """
    🔱 Antigravity Cloudflare Bridge - 隐身斗篷接驳器
    职责：绕过本地代理，通过 Cloudflare Workers 全球 CDN 节点安全请求 Gemini/Claude。
    """
    def __init__(self, worker_url):
        self.worker_url = worker_url.rstrip('/')

    def secure_request(self, api_key, prompt):
        # 构造隐身请求路径
        endpoint = f"{self.worker_url}/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}"
        
        payload = {
            "contents": [{
                "parts": [{"text": prompt}]
            }]
        }
        
        headers = {'Content-Type': 'application/json'}
        
        print(f"📡 正在通过 Hermes 隐身通道发送请求: {self.worker_url}")
        
        try:
            # 这里的请求不再需要本地代理 proxies=...
            response = requests.post(endpoint, headers=headers, json=payload, timeout=30)
            return response.json()
        except Exception as e:
            print(f"❌ 隐身通道握手失败: {e}")
            return None

if __name__ == "__main__":
    # 长官已完成物理部署，现在正式启用！
    bridge = CloudflareBridge("https://deploy.bbqddt.workers.dev")
    print("✅ 隐身桥接逻辑已激活！Antigravity 进入幽灵模式。")
