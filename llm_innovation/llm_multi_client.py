# -*- coding: utf-8 -*-
"""
Antigravity LLM创新 — 多模型客户端 V3.0

支持:
- OpenRouter (自动选择最优模型，含免费和付费)
- Gemini (备用)
- DeepSeek (备用)

自动选择可用模型，LLM真正成为演进的"创意引擎"
"""
import os
import json
import time
from pathlib import Path
from typing import Optional, List

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class LLMClient:
    """多模型LLM客户端 — 优先OpenRouter，备选Gemini/DeepSeek"""

    def __init__(self):
        self.openrouter_client = None
        self.gemini_client = None
        self.deepseek_client = None
        self.active_model = None
        self.available = False

        # 从.env文件加载密钥（如果环境变量中没有）
        self._load_env_if_needed()

        # 初始化OpenRouter
        or_key = os.environ.get("OPENROUTER_API_KEY")
        if or_key:
            try:
                from openai import OpenAI
                self.openrouter_client = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=or_key,
                )
                self.available = True
                self.active_model = "openrouter"
            except Exception:
                pass

        # 初始化Gemini
        try:
            from llm_innovation.llm_client import GeminiClient
            self.gemini_client = GeminiClient()
            if self.gemini_client.available and not self.available:
                self.available = True
                self.active_model = "gemini"
        except Exception:
            pass

        # 初始化DeepSeek
        ds_key = os.environ.get("DEEPSEEK_API_KEY")
        if ds_key:
            try:
                from openai import OpenAI
                self.deepseek_client = OpenAI(
                    api_key=ds_key,
                    base_url="https://api.deepseek.com/v1"
                )
                if not self.available:
                    self.available = True
                    self.active_model = "deepseek"
            except Exception:
                pass

    def _load_env_if_needed(self):
        """从.env文件加载环境变量（如果环境变量中没有）"""
        env_path = _PROJECT_ROOT / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    key = key.strip()
                    value = value.strip()
                    if value and not os.environ.get(key):
                        os.environ[key] = value

    def generate_content(self, prompt: str, system_prompt: Optional[str] = None,
                         max_tokens: int = 4000,
                         max_retries: int = 2) -> Optional[str]:
        """
        尝试所有可用模型，按优先级返回第一个成功的结果。

        优先级: OpenRouter > Gemini > DeepSeek
        """
        if not self.available:
            return None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # 1. 先试OpenRouter
        if self.openrouter_client:
            for _ in range(max_retries):
                try:
                    resp = self.openrouter_client.chat.completions.create(
                        model="qwen/qwen-2.5-72b-instruct",
                        messages=messages,
                        temperature=0.7,
                        max_tokens=max_tokens,
                    )
                    self.active_model = "openrouter"
                    return resp.choices[0].message.content
                except Exception as e:
                    if "402" in str(e) or "400" in str(e):
                        # 余额不足或模型不可用，换模型重试
                        try:
                            resp = self.openrouter_client.chat.completions.create(
                                model="microsoft/wizardlm-2-7b",
                                messages=messages,
                                temperature=0.7,
                                max_tokens=max_tokens,
                            )
                            self.active_model = "openrouter(wizardlm)"
                            return resp.choices[0].message.content
                        except:
                            pass
                    time.sleep(2)

        # 2. 再试Gemini
        if self.gemini_client and self.gemini_client.available:
            try:
                result = self.gemini_client.generate_content(prompt, system_prompt)
                if result:
                    self.active_model = "gemini"
                    return result
            except Exception:
                pass

        # 3. 最后试DeepSeek
        if self.deepseek_client:
            try:
                resp = self.deepseek_client.chat.completions.create(
                    model="deepseek-chat",
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
                self.active_model = "deepseek"
                return resp.choices[0].message.content
            except Exception:
                pass

        return None

    def get_status(self) -> str:
        """获取当前LLM状态"""
        status = []
        if self.openrouter_client:
            status.append("OpenRouter: 已配置")
        if self.gemini_client and self.gemini_client.available:
            status.append("Gemini: 已连接")
        elif self.gemini_client:
            status.append("Gemini: 已连接(配额耗尽)")
        if self.deepseek_client:
            status.append("DeepSeek: 已配置")
        return ", ".join(status)

    def __repr__(self):
        return f"<LLMClient(active: {self.active_model}, {self.get_status()}>)"
