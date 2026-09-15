# -*- coding: utf-8 -*-
"""
Antigravity LLM创新 — 增强版多模型客户端 V3.0

支持的模型提供商:
- OpenRouter (聚合了50+开源/付费模型)
- DeepSeek (DeepSeek-V3, DeepSeek-R1)
- Silikon (免费额度)
- Together.ai (开源模型托管)
- Grok (x.ai)
- ChatGPT (OpenAI)
- Ollama (本地部署模型)

自动选择可用模型，LLM真正成为演进的"创意引擎"
"""
import os
import json
import time
import random
from pathlib import Path
from typing import Optional, List, Dict, Any
from collections import deque

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class LLMConfig:
    """LLM提供商配置管理"""

    # 模型优先级链 (按质量和可靠性排序)
    MODEL_CHAIN = [
        "anthropic/claude-3.5-sonnet",      # 高质量推理
        "google/gemini-2.5-pro",            # 最强Gemini
        "deepseek/deepseek-chat",           # DeepSeek V3
        "meta/llama-3.3-70b-instruct",      # Llama3.3
        "qwen/qwen-2.5-72b-instruct",       # 通义千问
        "microsoft/wizardlm-2-7b",          # 轻量
    ]

    # OpenRouter免费/便宜模型 (用于降级)
    FREE_MODELS = [
        "google/gemma-2-9b-cot",            # Google Gemma2
        "meta/llama-3.2-3b",                # 轻量
        "qwen/qwen-2.5-coder-7b",           # 代码优化
        "microsoft/phi-3-mini-128k",        # 极轻
    ]

    @staticmethod
    def load_keys():
        """从.env或key.json加载API密钥"""
        config = {}

        # 加载.env
        env_path = _PROJECT_ROOT / ".env"
        if env_path.exists():
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("#") or "=" not in line:
                        continue
                    key, _, value = line.partition("=")
                    env_key = key.strip()
                    value = value.strip()
                    if value:
                        os.environ.setdefault(env_key, value)

        # 加载keys.json
        keys_file = _PROJECT_ROOT / "keys.json"
        if keys_file.exists():
            try:
                with open(keys_file, "r", encoding="utf-8") as f:
                    keys = json.load(f)
                    # 设置环境变量
                    for key, value in keys.items():
                        if isinstance(value, str):
                            env_key = key.upper()
                            os.environ.setdefault(env_key, value)
            except Exception:
                pass

        # 收集所有密钥
        for provider in ["OPENROUTER_API_KEY", "DEEPSEEK_API_KEY", "GEMINI_API_KEY",
                        "OPENAI_API_KEY", "GROK_API_KEY", "SILICONFLOW_API_KEY"]:
            key = os.environ.get(provider)
            if key:
                config[provider] = key

        return config


class LLMEnhancedClient:
    """增强版LLM多客户端 — 支持多提供商自动降级 + 负载均衡"""

    def __init__(self):
        self.clients = {}  # 提供商 -> 客户端实例
        self.model_priorities = LLMConfig.MODEL_CHAIN
        self.free_models = LLMConfig.FREE_MODELS
        self.active_provider = None
        self.active_model = None
        self.available = False
        self.failure_history = {}  # 记录失败次数
        self.success_history = deque(maxlen=50)  # 最近50次请求记录

        # 初始化所有可用客户端
        self._init_clients()

    def _init_clients(self):
        """初始化所有可用的LLM客户端"""
        keys = LLMConfig.load_keys()

        # 1. OpenRouter
        if api_key_ok := keys.get("OPENROUTER_API_KEY"):
            try:
                from openai import OpenAI
                c = OpenAI(
                    base_url="https://openrouter.ai/api/v1",
                    api_key=api_key_ok,
                )
                # 只注册实际可用的提供商：探测 /api/key 验证密钥，
                # 401 密钥不注册，避免运行期请求风暴（诚实红线：不假装可用）
                try:
                    import requests as _rq
                    probe = _rq.get("https://openrouter.ai/api/v1/auth/key",
                                    headers={"Authorization": f"Bearer {api_key_ok}"},
                                    timeout=10)
                    if probe.status_code == 200:
                        self.clients["openrouter"] = c
                        self.available = True
                except Exception:
                    # 探测失败时保守注册（可能是网络瞬时问题），失败计数会兜底
                    self.clients["openrouter"] = c
                    self.available = True
            except ImportError:
                pass

        # 2. DeepSeek
        if keys.get("DEEPSEEK_API_KEY"):
            try:
                from openai import OpenAI
                self.clients["deepseek"] = OpenAI(
                    api_key=keys["DEEPSEEK_API_KEY"],
                    base_url="https://api.deepseek.com/v1"
                )
                self.available = True
            except ImportError:
                pass

        # 3. OpenAI (ChatGPT)
        if keys.get("OPENAI_API_KEY"):
            try:
                from openai import OpenAI
                self.clients["openai"] = OpenAI(api_key=keys["OPENAI_API_KEY"])
                self.available = True
            except ImportError:
                pass

        # 4. Gemini (从旧客户端复用)
        try:
            from llm_innovation.llm_client import GeminiClient
            self.clients["gemini"] = GeminiClient()
            if self.clients["gemini"].available:
                self.available = True
        except Exception:
            pass

        # 5. Ollama (本地)
        if os.environ.get("OLLAMA_HOST", "localhost:11434"):
            try:
                import requests
                resp = requests.get("http://localhost:11434/api/tags", timeout=2)
                if resp.status_code == 200:
                    self.clients["ollama"] = "available"
                    self.available = True
            except Exception:
                pass

    def generate_content(self, prompt: str, system_prompt: Optional[str] = None,
                        max_tokens: int = 4000,
                        temperature: float = 0.7,
                        max_retries: int = 3,
                        prefer_free: bool = False) -> Optional[str]:
        """
        尝试所有可用模型，按优先级返回第一个成功的结果

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大输出token
            temperature: 温度参数
            max_retries: 最大重试次数
            prefer_free: 是否优先使用免费模型

        Returns:
            生成的文本，失败时返回None
        """
        if not self.available:
            return None

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # 选择模型链
        if prefer_free:
            model_chain = self.free_models + self.model_priorities
        else:
            model_chain = self.model_priorities + self.free_models

        for model in model_chain:
            # 跳过经常失败的模型
            if self.failure_history.get(model, 0) > 5:
                continue

            result = self._try_model(model, messages, max_tokens, temperature, max_retries)
            if result:
                self.active_model = model
                self.success_history.append(model)
                return result

            # 记录失败
            self.failure_history[model] = self.failure_history.get(model, 0) + 1

        return None

    def _try_model(self, model: str, messages: List[Dict],
                   max_tokens: int, temperature: float,
                   max_retries: int) -> Optional[str]:
        """尝试单个模型"""
        try:
            # OpenRouter / OpenAI / DeepSeek
            if model in ["deepseek/deepseek-chat", "deepseek/deepseek-coder",
                         "anthropic/claude-3.5-sonnet", "google/gemini-2.5-pro",
                         "meta/llama-3.3-70b-instruct", "qwen/qwen-2.5-72b-instruct",
                         "microsoft/wizardlm-2-7b", "google/gemma-2-9b-cot",
                         "meta/llama-3.2-3b", "qwen/qwen-2.5-coder-7b",
                         "microsoft/phi-3-mini-128k"]:
                if "openrouter" in self.clients:
                    resp = self.clients["openrouter"].chat.completions.create(
                        model=model,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    return resp.choices[0].message.content

            # DeepSeek原生
            if model.startswith("deepseek/deepseek") and "deepseek" in self.clients:
                resp = self.clients["deepseek"].chat.completions.create(
                    model=model.replace("deepseek/", ""),
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content

            # Gemini
            if model.startswith("google/gemini") and "gemini" in self.clients:
                if hasattr(self.clients["gemini"], 'generate_content'):
                    prompt_text = messages[-1]["content"] if messages else ""
                    system = messages[0]["content"] if messages and messages[0]["role"] == "system" else None
                    return self.clients["gemini"].generate_content(prompt_text, system)

            # ChatGPT
            if model.startswith("openai/gpt") and "openai" in self.clients:
                resp = self.clients["openai"].chat.completions.create(
                    model=model.replace("openai/", ""),
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content

            # Ollama (本地)
            if model in ["llama3.2", "gemma2", "qwen2.5"] and "ollama" in self.clients:
                import requests as req
                resp = req.post("http://localhost:11434/api/chat", json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {
                        "temperature": temperature,
                        "num_predict": max_tokens,
                    }
                }, timeout=300)
                if resp.status_code == 200:
                    return resp.json().get("message", {}).get("content", "")

        except Exception as e:
            error_msg = str(e)
            # 密钥级硬失败：直接返回None并让调用方跳过该提供商路径，
            # 避免逐模型重试造成请求风暴
            low = error_msg.lower()
            if "401" in low or "403" in low or "invalid_api_key" in low or "unauthorized" in low:
                return None
            # 处理速率限制
            if "429" in error_msg or "rate limit" in low:
                time.sleep(5)
            # 其他错误继续下一个模型
            pass

        return None

    def get_status(self) -> str:
        """获取当前LLM客户端状态"""
        status = []
        for provider in self.clients:
            if provider == "ollama":
                status.append("Ollama(local): ✓")
            else:
                status.append(f"{provider}: ✓")
        return ", ".join(status)

    def __repr__(self):
        return f"<LLMEnhancedClient(available: {self.available}, active: {self.active_model})>"

    def reset_failures(self, model: Optional[str] = None):
        """重置失败计数（模型恢复时使用）"""
        if model:
            self.failure_history.pop(model, None)
        else:
            self.failure_history.clear()