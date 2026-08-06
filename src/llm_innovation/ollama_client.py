# -*- coding: utf-8 -*-
"""
Ollama本地LLM客户端 — 通过curl子进程调用(绕过Python IPv6代理问题)
"""
import sys
import json
import subprocess
from pathlib import Path
from typing import Optional, List, Dict

_PROJECT_ROOT = Path(__file__).resolve().parent

class OllamaClient:
    """本地Ollama客户端 — 通过curl调用避免代理问题"""

    MODELS = ['gemma4', 'gemma2']

    def __init__(self, model: str = 'gemma2'):
        self.model = model
        self.available = False
        self._test()

    def _test(self):
        """测试Ollama是否可用"""
        try:
            result = subprocess.run(
                ['curl', '-s', '--max-time', '5', 'http://127.0.0.1:11434/api/tags'],
                capture_output=True, text=True, encoding='utf-8'
            )
            if result.returncode == 0 and 'models' in result.stdout:
                self.available = True
        except:
            self.available = False

    def chat(self, message: str, system: str = None, temperature: float = 0.8) -> Optional[str]:
        """发送聊天请求"""
        if not self.available:
            return None

        try:
            msgs = []
            if system:
                msgs.append({'role': 'system', 'content': system})
            msgs.append({'role': 'user', 'content': message})

            data = json.dumps({
                'model': self.model,
                'messages': msgs,
                'stream': False,
                'options': {'temperature': temperature}
            }).encode()

            result = subprocess.run(
                ['curl', '-s', '--max-time', '120', '-X', 'POST',
                 'http://127.0.0.1:11434/api/chat',
                 '-H', 'Content-Type: application/json',
                 '-d', data],
                capture_output=True, text=True, encoding='utf-8'
            )

            if result.returncode == 0:
                resp = json.loads(result.stdout)
                return resp.get('message', {}).get('content', '')
            return None
        except Exception as e:
            print(f"[Ollama] Error: {e}")
            return None

    def generate_formula_ideas(self, count: int = 3) -> List[str]:
        """生成公式创意"""
        system = "You are a mathematical lottery prediction researcher. Focus on creative statistical and mathematical approaches."
        prompt = f"Generate {count} creative mathematical formula ideas for analyzing lottery number patterns (6 red balls 1-33, 1 blue ball 1-16). Each idea should be one sentence describing the mathematical concept. Focus on novel approaches, not basic probability."

        result = self.chat(prompt, system=system, temperature=0.9)
        if result:
            lines = [l.strip() for l in result.split('\n') if l.strip() and any(c.isdigit() for c in l)]
            return lines[:count] if lines else [result[:200]]
        return []

if __name__ == "__main__":
    client = OllamaClient()
    if client.available:
        print("Ollama: available")
        ideas = client.generate_formula_ideas(3)
        for i, idea in enumerate(ideas, 1):
            print(f"  {i}. {idea}")
    else:
        print("Ollama: NOT available (start with: ollama serve)")
