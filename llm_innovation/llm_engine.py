# -*- coding: utf-8 -*-
"""
Antigravity LLM创新引擎 V3.0 — 全渠道AI协同

支持的所有AI供应商:
0. CC Switch (最高优先级) - 本地代理 http://127.0.0.1:15721，路由Claude/Gemini/Codex
1. OpenRouter (已接入) - 免费模型: qwen/gemma/llama等
2. Gemini (已接入) - 免费层配额用完，自动降级
3. DeepSeek (已接入) - 余额不足，自动降级
4. Ollama (本地) - 需要安装，支持gemma/llama等
5. Together AI (预留) - 需要API Key
6. Perplexity (预留) - 需要API Key
7. Groq (预留) - 需要API Key
8. HuggingFace (预留) - 通过HF_TOKEN访问

自动故障转移: 按优先级依次尝试，一个失败自动换下一个
"""
import os
import json
import time
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class LLMEngine:
    """全渠道LLM引擎 — 多供应商自动故障转移"""

    def __init__(self):
        self.providers = {}
        self.active_provider = None
        self.available = False
        self.call_log = []  # 记录每次调用

        # 从.env加载密钥
        self._load_env()

        # 初始化所有可用供应商 — CC Switch最高优先级
        self._init_cc_switch()   # ★ 最高优先级：CC Switch本地代理
        self._init_ollama()
        self._init_openrouter()
        self._init_deeprouter()
        self._init_sensenova()
        self._init_gemini()
        self._init_deepseek()
        self._init_together()
        self._init_perplexity()
        self._init_groq()
        self._init_huggingface()

        # 重新排序：CC Switch > Ollama
        if "cc_switch" in self.providers:
            self.providers["cc_switch"]["priority"] = -1  # 最高优先
        if "ollama" in self.providers:
            self.providers["ollama"]["priority"] = 0

        # 确定可用供应商
        self._build_provider_list()

    def _load_env(self):
        """从.env文件加载所有密钥"""
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

    def _init_openrouter(self):
        """初始化OpenRouter"""
        or_key = os.environ.get("OPENROUTER_API_KEY")
        if or_key:
            try:
                from openai import OpenAI
                self.providers["openrouter"] = {
                    "client": OpenAI(base_url="https://openrouter.ai/api/v1", api_key=or_key),
                    "models": [
                        "qwen/qwen-2.5-72b-instruct",
                        "meta-llama/llama-3.3-70b-instruct",
                        "google/gemma-2-27b-it",
                        "mistralai/mistral-7b-instruct",
                    ],
                    "priority": 1,
                }
                self.available = True
            except Exception:
                pass

    def _init_deeprouter(self):
        """初始化DeepRouter — 多key轮换"""
        for i in range(1, 5):
            key = os.environ.get(f"DEEPRouter_API_KEY_{i}")
            if key:
                try:
                    from openai import OpenAI
                    self.providers["deeprouter"] = {
                        "client": OpenAI(api_key=key, base_url="https://www.deeprouter.top/v1"),
                        "models": ["gpt-4o-mini", "gpt-3.5-turbo", "claude-3-haiku-20240307"],
                        "priority": 2,
                    }
                    if not self.available:
                        self.available = True
                    break
                except Exception:
                    continue

    def _init_sensenova(self):
        """初始化SenseNova — 多key轮换"""
        for i in range(1, 5):
            key = os.environ.get(f"SENSENOVA_API_KEY_{i}")
            if key:
                try:
                    from openai import OpenAI
                    self.providers["sensenova"] = {
                        "client": OpenAI(api_key=key, base_url="https://api.sensenova.cn/v1"),
                        "models": ["yi-lightning", "yi-large"],
                        "priority": 4,
                    }
                    if not self.available:
                        self.available = True
                    break
                except Exception:
                    pass

    def _init_gemini(self):
        """初始化Gemini"""
        try:
            from llm_innovation.llm_client import GeminiClient
            gc = GeminiClient()
            if gc.available:
                self.providers["gemini"] = {
                    "client": gc,
                    "priority": 2,
                }
                if not self.available:
                    self.available = True
        except Exception:
            pass

    def _init_deepseek(self):
        """初始化DeepSeek"""
        ds_key = os.environ.get("DEEPSEEK_API_KEY")
        if ds_key:
            try:
                from openai import OpenAI
                self.providers["deepseek"] = {
                    "client": OpenAI(api_key=ds_key, base_url="https://api.deepseek.com/v1"),
                    "models": ["deepseek-chat", "deepseek-coder"],
                    "priority": 3,
                }
                if not self.available:
                    self.available = True
            except Exception:
                pass

    def _init_together(self):
        """初始化Together AI"""
        tg_key = os.environ.get("TOGETHER_API_KEY")
        if tg_key:
            try:
                from openai import OpenAI
                self.providers["together"] = {
                    "client": OpenAI(api_key=tg_key, base_url="https://api.together.xyz/v1"),
                    "models": [
                        "meta-llama/Llama-3-70b-chat-hf",
                        "mistralai/Mixtral-8x7B-Instruct-v0.1",
                        "Qwen/Qwen2.5-72B-Instruct",
                    ],
                    "priority": 4,
                }
                if not self.available:
                    self.available = True
            except Exception:
                pass

    def _init_perplexity(self):
        """初始化Perplexity"""
        px_key = os.environ.get("PERPLEXITY_API_KEY")
        if px_key:
            try:
                from openai import OpenAI
                self.providers["perplexity"] = {
                    "client": OpenAI(api_key=px_key, base_url="https://api.perplexity.ai"),
                    "models": ["sonar", "sonar-pro"],
                    "priority": 5,
                }
                if not self.available:
                    self.available = True
            except Exception:
                pass

    def _init_groq(self):
        """初始化Groq"""
        gx_key = os.environ.get("GROQ_API_KEY")
        if gx_key:
            try:
                from openai import OpenAI
                self.providers["groq"] = {
                    "client": OpenAI(api_key=gx_key, base_url="https://api.groq.com/openai/v1"),
                    "models": [
                        "llama-3.1-70b-versatile",
                        "mixtral-8x7b-32768",
                        "gemma2-9b-it",
                    ],
                    "priority": 6,
                }
                if not self.available:
                    self.available = True
            except Exception:
                pass

    def _init_cc_switch(self):
        """初始化 CC Switch 本地代理 — 路由Claude/Gemini/Codex，最高优先级"""
        cc_url = os.environ.get("CC_SWITCH_BASE_URL", "http://127.0.0.1:15721/v1")
        try:
            import requests
            # 探针：检查 CC Switch 是否在线
            probe = requests.get(cc_url.replace("/v1", "/"), timeout=3)
            if probe.status_code in (200, 404):  # 404 说明服务存在但路径不同，仍算在线
                from openai import OpenAI
                self.providers["cc_switch"] = {
                    "client": OpenAI(
                        api_key="cc-switch-local",  # 本地代理无需真实Key
                        base_url=cc_url,
                    ),
                    "models": [
                        "claude-sonnet-4-5",
                        "claude-3-5-haiku-20241022",
                        "gemini-2.0-flash",
                        "gemini-1.5-pro",
                    ],
                    "priority": -1,  # ★ 最高优先级
                    "name": "CC Switch",
                }
                self.available = True
        except Exception:
            pass  # CC Switch不在线，自动降级到下一个供应商

    def _init_ollama(self):
        """初始化Ollama本地模型 — 0延迟0费用"""
        try:
            import requests
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                if models:
                    model_names = [m.get("name", "") for m in models]
                    self.providers["ollama"] = {
                        "client": requests.Session(),
                        "base_url": "http://localhost:11434",
                        "models": model_names,
                        "priority": 1,  # 本地最快最便宜
                    }
                    if not self.available:
                        self.available = True
        except Exception:
            pass

    def _init_huggingface(self):
        """初始化HuggingFace"""
        hf_token = os.environ.get("HF_TOKEN")
        if hf_token:
            try:
                from huggingface_hub import InferenceClient
                self.providers["huggingface"] = {
                    "client": InferenceClient(token=hf_token),
                    "models": ["meta-llama/Llama-3.3-70B-Instruct"],
                    "priority": 8,
                }
                if not self.available:
                    self.available = True
            except Exception:
                pass

    def _init_deeprouter(self):
        """初始化DeepRouter"""
        for i in range(1, 5):
            key = os.environ.get(f"DEEPRouter_API_KEY_{i}")
            if key:
                try:
                    from openai import OpenAI
                    self.providers["deeprouter"] = {
                        "client": OpenAI(api_key=key, base_url="https://www.deeprouter.top/v1"),
                        "models": ["gpt-4o-mini", "gpt-3.5-turbo", "claude-3-haiku-20240307"],
                        "priority": 2,  # 仅次于OpenRouter
                    }
                    if not self.available:
                        self.available = True
                    break
                except Exception:
                    continue

    def _init_sensenova(self):
        """初始化SenseNova"""
        for i in range(1, 5):
            key = os.environ.get(f"SENSENOVA_API_KEY_{i}")
            if key:
                try:
                    from openai import OpenAI
                    self.providers["sensenova"] = {
                        "client": OpenAI(api_key=key, base_url="https://api.sensenova.cn/v1"),
                        "models": ["yi-lightning", "yi-large"],
                        "priority": 5,
                    }
                    if not self.available:
                        self.available = True
                    break
                except Exception:
                    pass

    def _build_provider_list(self):
        """按优先级排序可用供应商"""
        self.provider_list = sorted(
            self.providers.values(),
            key=lambda p: p.get("priority", 999)
        )

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 max_tokens: int = 4000, timeout: int = 60) -> Optional[str]:
        """
        尝试所有可用供应商，按优先级返回第一个成功的结果。

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_tokens: 最大token数
            timeout: 超时秒数

        Returns:
            生成的文本，所有供应商都失败返回None
        """
        start_time = time.time()
        errors = []

        for provider_name, provider in enumerate(self.provider_list):
            pname = list(self.providers.keys())[provider_name]

            try:
                result = self._call_provider(pname, provider, prompt, system_prompt, max_tokens, timeout)
                if result:
                    elapsed = time.time() - start_time
                    self.active_provider = pname
                    self.call_log.append({
                        "provider": pname,
                        "success": True,
                        "elapsed": round(elapsed, 2),
                        "timestamp": datetime.now().isoformat(),
                    })
                    return result
            except Exception as e:
                errors.append(f"{pname}: {str(e)[:100]}")

        # 所有供应商都失败
        self.call_log.append({
            "provider": "all_failed",
            "success": False,
            "errors": errors,
            "timestamp": datetime.now().isoformat(),
        })
        return None

    def _call_openrouter(self, provider, prompt, system_prompt, max_tokens):
        """调用OpenRouter"""
        client = provider["client"]
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for model in provider.get("models", []):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens,
                    timeout=30,
                )
                return resp.choices[0].message.content
            except Exception:
                continue
        return None

    def _call_gemini(self, provider, prompt, system_prompt, max_tokens):
        """调用Gemini"""
        gc = provider["client"]
        if gc.available:
            return gc.generate_content(prompt, system_prompt)
        return None

    def _call_deepseek(self, provider, prompt, system_prompt, max_tokens):
        """调用DeepSeek"""
        client = provider["client"]
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for model in provider.get("models", []):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content
            except Exception:
                continue
        return None

    def _call_together(self, provider, prompt, system_prompt, max_tokens):
        """调用Together AI"""
        client = provider["client"]
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for model in provider.get("models", []):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content
            except Exception:
                continue
        return None

    def _call_ollama(self, provider, prompt, system_prompt, max_tokens):
        """调用Ollama本地模型"""
        client = provider["client"]
        base_url = provider.get("base_url", "http://localhost:11434")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        # 优先尝试gemma2（content字段正常返回），gemma4的thinking模式导致content为空
        models = sorted(provider.get("models", []), key=lambda m: 0 if "gemma2" in m else 1)

        for model in models:
            try:
                resp = client.post(f"{base_url}/api/chat", json={
                    "model": model,
                    "messages": messages,
                    "stream": False,
                    "options": {"num_predict": max_tokens, "num_ctx": 4096},
                }, timeout=120)
                if resp.status_code == 200:
                    content = resp.json().get("message", {}).get("content", "").strip()
                    if content:
                        return content
            except Exception:
                continue
        return None

    def _call_deeprouter(self, provider, prompt, system_prompt, max_tokens):
        """调用DeepRouter"""
        client = provider["client"]
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for model in provider.get("models", []):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content
            except Exception:
                continue
        return None

    def _call_sensenova(self, provider, prompt, system_prompt, max_tokens):
        """调用SenseNova"""
        client = provider["client"]
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        for model in provider.get("models", []):
            try:
                resp = client.chat.completions.create(
                    model=model,
                    messages=messages,
                    temperature=0.7,
                    max_tokens=max_tokens,
                )
                return resp.choices[0].message.content
            except Exception:
                continue
        return None

    def _call_provider(self, name, provider, prompt, system_prompt, max_tokens, timeout):
        """分发到具体供应商"""
        if name == "openrouter":
            return self._call_openrouter(provider, prompt, system_prompt, max_tokens)
        elif name == "deeprouter":
            return self._call_deeprouter(provider, prompt, system_prompt, max_tokens)
        elif name == "sensenova":
            return self._call_sensenova(provider, prompt, system_prompt, max_tokens)
        elif name == "gemini":
            return self._call_gemini(provider, prompt, system_prompt, max_tokens)
        elif name == "deepseek":
            return self._call_deepseek(provider, prompt, system_prompt, max_tokens)
        elif name == "together":
            return self._call_together(provider, prompt, system_prompt, max_tokens)
        elif name == "ollama":
            return self._call_ollama(provider, prompt, system_prompt, max_tokens)
        return None

    def get_status(self) -> Dict:
        """获取引擎状态"""
        status = {
            "available": self.available,
            "active_provider": self.active_provider,
            "providers_configured": list(self.providers.keys()),
            "call_log_last": self.call_log[-3:] if self.call_log else [],
        }
        return status

    def __repr__(self):
        return f"<LLMEngine(active: {self.active_provider}, providers: {list(self.providers.keys())})>"
