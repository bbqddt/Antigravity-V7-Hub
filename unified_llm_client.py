# -*- coding: utf-8 -*-
"""
Antigravity 统一 LLM 客户端 V1.0
================================
整合所有可用的 LLM 提供商，自动故障转移、负载均衡、重试机制

支持的提供商：
1. OpenRouter (免费模型可用)
2. SiliconFlow (需充值)
3. One API Gateway (Docker本地，仅容器内可用)
4. CC Switch (本地代理)
5. DeepRouter (多Key轮换)
6. Ollama (本地)
"""

import os
import sys
import json
import time
import logging
import requests
from pathlib import Path
from typing import List, Dict, Optional, Any
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from enum import Enum

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

# 加载环境变量
def load_env():
    env_path = _PROJECT_ROOT / ".env"
    if env_path.exists():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k, v = k.strip(), v.strip()
                if v:
                    os.environ[k] = v

load_env()

logger = logging.getLogger("UnifiedLLM")
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)


class ProviderStatus(Enum):
    UNKNOWN = "unknown"
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    FAILED = "failed"
    RATE_LIMITED = "rate_limited"


@dataclass
class ModelInfo:
    id: str
    provider: str
    free: bool = False
    context_length: int = 4096
    max_tokens: int = 4096


@dataclass
class ProviderConfig:
    name: str
    base_url: str
    api_key: str
    models: List[ModelInfo]
    timeout: int = 60
    max_retries: int = 3
    verify_ssl: bool = True
    enabled: bool = True
    status: ProviderStatus = ProviderStatus.UNKNOWN
    last_test: float = 0
    error_count: int = 0
    success_count: int = 0


class LLMProvider:
    """统一的 LLM 提供商基类"""
    
    def __init__(self, config: ProviderConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {config.api_key}",
            "Content-Type": "application/json",
        })
    
    def chat(self, messages: List[Dict], model: Optional[str] = None, 
             max_tokens: int = 1000, temperature: float = 0.7) -> Optional[str]:
        raise NotImplementedError
    
    def test(self) -> bool:
        raise NotImplementedError
    
    def get_models(self) -> List[ModelInfo]:
        return self.config.models


class OpenRouterProvider(LLMProvider):
    """OpenRouter 提供商 - 支持免费模型"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # 默认免费模型
        self.free_models = [
            "nvidia/nemotron-3-ultra-550b-a55b:free",
            "nvidia/nemotron-3-super-120b-a12b:free",
            "google/gemma-4-26b-a4b-it:free",
            "openai/gpt-oss-20b:free",
            "meta-llama/llama-3.1-8b-instruct:free",
        ]
    
    def chat(self, messages: List[Dict], model: Optional[str] = None,
             max_tokens: int = 1000, temperature: float = 0.7) -> Optional[str]:
        model = model or self.free_models[0]
        
        for attempt in range(self.config.max_retries):
            try:
                # 优先尝试免费模型
                models_to_try = [model] + [m for m in self.free_models if m != model]
                
                for m in models_to_try:
                    resp = self.session.post(
                        f"{self.config.base_url}/chat/completions",
                        json={
                            "model": m,
                            "messages": messages,
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                        },
                        timeout=self.config.timeout,
                        verify=self.config.verify_ssl,
                    )
                    if resp.status_code == 200:
                        self.config.success_count += 1
                        self.config.status = ProviderStatus.HEALTHY
                        return resp.json()["choices"][0]["message"]["content"]
                    elif resp.status_code == 402:
                        # 余额不足，尝试下一个免费模型
                        continue
                    elif resp.status_code == 429:
                        # 速率限制
                        self.config.status = ProviderStatus.RATE_LIMITED
                        time.sleep(2 ** attempt)
                        break
                
            except requests.exceptions.SSLError:
                logger.warning(f"OpenRouter SSL错误，尝试 verify=False")
                self.config.verify_ssl = False
                continue
            except Exception as e:
                logger.warning(f"OpenRouter 请求失败: {e}")
                time.sleep(1)
        
        self.config.error_count += 1
        self.config.status = ProviderStatus.FAILED
        return None
    
    def test(self) -> bool:
        try:
            resp = self.session.post(
                f"{self.config.base_url}/chat/completions",
                json={"model": self.free_models[0], "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5},
                timeout=15,
                verify=self.config.verify_ssl,
            )
            self.config.status = ProviderStatus.HEALTHY if resp.status_code == 200 else ProviderStatus.FAILED
            return resp.status_code == 200
        except:
            self.config.status = ProviderStatus.FAILED
            return False


class SiliconFlowProvider(LLMProvider):
    """SiliconFlow 提供商"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.free_models = [
            "Qwen/Qwen3-8B",
            "Qwen/Qwen3-14B",
            "Qwen/Qwen3-32B",
            "THUDM/GLM-4-9B-0414",
            "zai-org/GLM-5.2",
        ]
    
    def chat(self, messages: List[Dict], model: Optional[str] = None,
             max_tokens: int = 1000, temperature: float = 0.7) -> Optional[str]:
        model = model or self.free_models[0]
        
        for attempt in range(self.config.max_retries):
            try:
                models_to_try = [model] + [m for m in self.free_models if m != model]
                
                for m in models_to_try:
                    resp = self.session.post(
                        f"{self.config.base_url}/chat/completions",
                        json={
                            "model": m,
                            "messages": messages,
                            "max_tokens": max_tokens,
                            "temperature": temperature,
                        },
                        timeout=self.config.timeout,
                        verify=self.config.verify_ssl,
                    )
                    if resp.status_code == 200:
                        self.config.success_count += 1
                        self.config.status = ProviderStatus.HEALTHY
                        return resp.json()["choices"][0]["message"]["content"]
                    elif resp.status_code == 402:
                        continue
                    elif resp.status_code == 429:
                        self.config.status = ProviderStatus.RATE_LIMITED
                        time.sleep(2 ** attempt)
                        break
                        
            except Exception as e:
                logger.warning(f"SiliconFlow 请求失败: {e}")
                time.sleep(1)
        
        self.config.error_count += 1
        self.config.status = ProviderStatus.FAILED
        return None
    
    def test(self) -> bool:
        try:
            resp = self.session.post(
                f"{self.config.base_url}/chat/completions",
                json={"model": self.free_models[0], "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5},
                timeout=15,
                verify=self.config.verify_ssl,
            )
            self.config.status = ProviderStatus.HEALTHY if resp.status_code == 200 else ProviderStatus.FAILED
            return resp.status_code == 200
        except:
            self.config.status = ProviderStatus.FAILED
            return False


class OneAPIProvider(LLMProvider):
    """One API 网关提供商 (本地 Docker) - 仅容器内部可用，Cloudflare 拦截宿主机访问"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        # One API 内部配置的模型
        self.internal_models = [
            "deepseek-ai/DeepSeek-V3",
            "meta-llama/llama-3.1-8b-instruct:free",
            "gpt-3.5-turbo",
            "gpt-4o-mini",
        ]
        # 标记为仅容器内可用
        self.config.enabled = False  # 宿主机默认禁用
    
    def chat(self, messages: List[Dict], model: Optional[str] = None,
             max_tokens: int = 1000, temperature: float = 0.7) -> Optional[str]:
        if not self.config.enabled:
            logger.warning("One API: 仅容器内部可用，宿主机被 Cloudflare 拦截")
            return None
        model = model or self.internal_models[0]
        
        for attempt in range(self.config.max_retries):
            try:
                resp = self.session.post(
                    f"{self.config.base_url}/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=self.config.timeout,
                    verify=self.config.verify_ssl,
                )
                if resp.status_code == 200:
                    self.config.success_count += 1
                    self.config.status = ProviderStatus.HEALTHY
                    return resp.json()["choices"][0]["message"]["content"]
                elif resp.status_code == 402:
                    logger.warning(f"One API: 余额不足")
                elif resp.status_code == 500:
                    logger.warning(f"One API: 内部错误 - {resp.text[:200]}")
                    
            except Exception as e:
                logger.warning(f"One API 请求失败: {e}")
                time.sleep(1)
        
        self.config.error_count += 1
        self.config.status = ProviderStatus.FAILED
        return None
    
    def test(self) -> bool:
        if not self.config.enabled:
            return False
        try:
            resp = self.session.get(
                f"{self.config.base_url}/models",
                timeout=10,
                verify=self.config.verify_ssl,
            )
            self.config.status = ProviderStatus.HEALTHY if resp.status_code == 200 else ProviderStatus.FAILED
            return resp.status_code == 200
        except:
            self.config.status = ProviderStatus.FAILED
            return False


class CCSwitchProvider(LLMProvider):
    """CC Switch 本地代理提供商"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.models_list = [
            "claude-sonnet-4-5",
            "claude-3-5-haiku",
            "gemini-2.0-flash",
            "codex",
        ]
    
    def chat(self, messages: List[Dict], model: Optional[str] = None,
             max_tokens: int = 1000, temperature: float = 0.7) -> Optional[str]:
        model = model or self.models_list[0]
        
        for attempt in range(self.config.max_retries):
            try:
                resp = self.session.post(
                    f"{self.config.base_url}/chat/completions",
                    json={
                        "model": model,
                        "messages": messages,
                        "max_tokens": max_tokens,
                        "temperature": temperature,
                    },
                    timeout=self.config.timeout,
                    verify=self.config.verify_ssl,
                )
                if resp.status_code == 200:
                    content = resp.json()["choices"][0]["message"]["content"]
                    if content and len(content.strip()) > 10:
                        self.config.success_count += 1
                        self.config.status = ProviderStatus.HEALTHY
                        return content
            except Exception as e:
                logger.warning(f"CC Switch 请求失败: {e}")
                time.sleep(1)
        
        self.config.error_count += 1
        self.config.status = ProviderStatus.FAILED
        return None
    
    def test(self) -> bool:
        try:
            # 测试基础连通性
            base = self.config.base_url.replace("/v1", "")
            resp = self.session.get(base, timeout=5, verify=self.config.verify_ssl)
            self.config.status = ProviderStatus.HEALTHY if resp.status_code in (200, 404) else ProviderStatus.FAILED
            return resp.status_code in (200, 404)
        except:
            self.config.status = ProviderStatus.FAILED
            return False


class OllamaProvider(LLMProvider):
    """Ollama 本地模型提供商"""
    
    def __init__(self, config: ProviderConfig):
        super().__init__(config)
        self.base_url = config.base_url
    
    def chat(self, messages: List[Dict], model: Optional[str] = None,
             max_tokens: int = 1000, temperature: float = 0.7) -> Optional[str]:
        model = model or (self.config.models[0].id if self.config.models else "gemma2")
        
        for attempt in range(self.config.max_retries):
            try:
                resp = requests.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": model,
                        "messages": messages,
                        "stream": False,
                        "options": {"num_predict": max_tokens, "temperature": temperature},
                    },
                    timeout=self.config.timeout,
                )
                if resp.status_code == 200:
                    content = resp.json().get("message", {}).get("content", "")
                    if content:
                        self.config.success_count += 1
                        self.config.status = ProviderStatus.HEALTHY
                        return content
            except Exception as e:
                logger.warning(f"Ollama 请求失败: {e}")
                time.sleep(1)
        
        self.config.error_count += 1
        self.config.status = ProviderStatus.FAILED
        return None
    
    def test(self) -> bool:
        try:
            resp = requests.get(f"{self.base_url}/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                self.config.status = ProviderStatus.HEALTHY
                return len(models) > 0
        except:
            pass
        self.config.status = ProviderStatus.FAILED
        return False


class DeepRouterProvider(LLMProvider):
    """DeepRouter 提供商 - 多Key轮换"""
    
    def __init__(self, configs: List[ProviderConfig]):
        self.config = configs[0] if configs else None  # 使用第一个配置作为主配置
        self.configs = configs
        self.current_index = 0
        self.providers = [OpenRouterProvider(c) for c in configs]  # 复用OpenRouter逻辑
    
    def _get_provider(self) -> OpenRouterProvider:
        provider = self.providers[self.current_index]
        self.current_index = (self.current_index + 1) % len(self.providers)
        return provider
    
    def chat(self, messages: List[Dict], model: Optional[str] = None,
             max_tokens: int = 1000, temperature: float = 0.7) -> Optional[str]:
        for _ in range(len(self.providers)):
            provider = self._get_provider()
            result = provider.chat(messages, model, max_tokens, temperature)
            if result:
                return result
        return None
    
    def test(self) -> bool:
        return any(p.test() for p in self.providers)


class UnifiedLLMClient:
    """统一 LLM 客户端 - 自动故障转移、负载均衡"""
    
    def __init__(self):
        self.providers: Dict[str, LLMProvider] = {}
        self.provider_order: List[str] = []
        self._init_providers()
    
    def _init_providers(self):
        """初始化所有可用提供商"""
        
        # 1. OpenRouter (优先 - 有免费模型)
        or_key = os.environ.get("OPENROUTER_API_KEY")
        if or_key:
            config = ProviderConfig(
                name="OpenRouter",
                base_url=os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"),
                api_key=or_key,
                models=[
                    ModelInfo(id="nvidia/nemotron-3-ultra-550b-a55b:free", provider="OpenRouter", free=True),
                    ModelInfo(id="google/gemma-4-26b-a4b-it:free", provider="OpenRouter", free=True),
                    ModelInfo(id="meta-llama/llama-3.1-8b-instruct:free", provider="OpenRouter", free=True),
                    ModelInfo(id="openai/gpt-oss-20b:free", provider="OpenRouter", free=True),
                ],
                timeout=60,
                verify_ssl=False,  # 网络问题时禁用SSL验证
            )
            self.providers["OpenRouter"] = OpenRouterProvider(config)
            self.provider_order.append("OpenRouter")
        
        # 2. SiliconFlow
        sf_key = os.environ.get("SILICONFLOW_API_KEY")
        if sf_key:
            config = ProviderConfig(
                name="SiliconFlow",
                base_url=os.environ.get("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1"),
                api_key=sf_key,
                models=[
                    ModelInfo(id="Qwen/Qwen3-8B", provider="SiliconFlow", free=True),
                    ModelInfo(id="THUDM/GLM-4-9B-0414", provider="SiliconFlow", free=True),
                    ModelInfo(id="zai-org/GLM-5.2", provider="SiliconFlow", free=False),
                ],
                timeout=60,
                verify_ssl=False,
            )
            self.providers["SiliconFlow"] = SiliconFlowProvider(config)
            self.provider_order.append("SiliconFlow")
        
        # 3. One API Gateway (本地 Docker)
        one_key = os.environ.get("ONE_API_KEY")
        one_url = os.environ.get("ONE_API_BASE_URL", "http://localhost:3001/v1")
        if one_key:
            config = ProviderConfig(
                name="OneAPI",
                base_url=one_url,
                api_key=one_key,
                models=[
                    ModelInfo(id="deepseek-ai/DeepSeek-V3", provider="OneAPI", free=False),
                    ModelInfo(id="meta-llama/llama-3.1-8b-instruct:free", provider="OneAPI", free=True),
                ],
                timeout=30,
                verify_ssl=False,
            )
            self.providers["OneAPI"] = OneAPIProvider(config)
            self.provider_order.append("OneAPI")
        
        # 4. CC Switch
        cc_url = os.environ.get("CC_SWITCH_BASE_URL", "http://127.0.0.1:15721/v1")
        cc_key = os.environ.get("CC_SWITCH_API_KEY")
        if cc_key:
            config = ProviderConfig(
                name="CCSwitch",
                base_url=cc_url,
                api_key=cc_key,
                models=[
                    ModelInfo(id="claude-sonnet-4-5", provider="CCSwitch", free=False),
                    ModelInfo(id="gemini-2.0-flash", provider="CCSwitch", free=False),
                ],
                timeout=60,
                verify_ssl=False,
            )
            self.providers["CCSwitch"] = CCSwitchProvider(config)
            self.provider_order.append("CCSwitch")
        
        # 5. DeepRouter (多Key)
        dr_keys = []
        for i in range(1, 5):
            key = os.environ.get(f"DEEPRouter_API_KEY_{i}")
            if key:
                dr_keys.append(key)
        if dr_keys:
            configs = []
            for key in dr_keys:
                configs.append(ProviderConfig(
                    name=f"DeepRouter-{dr_keys.index(key)+1}",
                    base_url="https://www.deeprouter.top/v1",
                    api_key=key,
                    models=[ModelInfo(id="gpt-4o-mini", provider="DeepRouter", free=False)],
                    timeout=30,
                ))
            self.providers["DeepRouter"] = DeepRouterProvider(configs)
            self.provider_order.append("DeepRouter")
        
        # 6. Ollama (本地)
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=3)
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                for m in models:
                    name = m.get("name", "")
                    if name:
                        config = ProviderConfig(
                            name=f"Ollama-{name}",
                            base_url="http://localhost:11434",
                            api_key="",
                            models=[ModelInfo(id=name, provider="Ollama", free=True)],
                            timeout=180,
                        )
                        self.providers[f"Ollama-{name}"] = OllamaProvider(config)
                        self.provider_order.append(f"Ollama-{name}")
        except:
            pass
        
        logger.info(f"初始化完成: {len(self.providers)} 个提供商 - {self.provider_order}")
    
    def chat(self, messages: List[Dict], model: Optional[str] = None,
             max_tokens: int = 1000, temperature: float = 0.7,
             provider: Optional[str] = None) -> Optional[str]:
        """
        统一调用接口
        
        Args:
            messages: 消息列表
            model: 指定模型 (可选)
            max_tokens: 最大token数
            temperature: 温度
            provider: 指定提供商 (可选，不指定则自动故障转移)
        
        Returns:
            模型回复文本，失败返回 None
        """
        if provider and provider in self.providers:
            return self.providers[provider].chat(messages, model, max_tokens, temperature)
        
        # 自动故障转移：按优先级尝试
        for p_name in self.provider_order:
            if p_name not in self.providers:
                continue
            p = self.providers[p_name]
            if p.config.status == ProviderStatus.FAILED and p.config.error_count > 5:
                continue
            
            logger.info(f"尝试提供商: {p_name}")
            result = p.chat(messages, model, max_tokens, temperature)
            if result:
                logger.info(f"✓ {p_name} 成功")
                return result
            else:
                logger.warning(f"✗ {p_name} 失败，尝试下一个")
        
        logger.error("所有提供商均失败")
        return None
    
    def chat_parallel(self, messages: List[Dict], max_workers: int = 4,
                      max_tokens: int = 1000, temperature: float = 0.7) -> Dict[str, Optional[str]]:
        """并行调用所有健康的提供商"""
        results = {}
        healthy_providers = [
            (name, p) for name, p in self.providers.items()
            if p.config.status != ProviderStatus.FAILED or p.config.error_count <= 5
        ]
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for name, provider in healthy_providers:
                future = executor.submit(provider.chat, messages, None, max_tokens, temperature)
                futures[future] = name
            
            for future in as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result(timeout=120)
                except Exception as e:
                    logger.warning(f"{name} 并行调用异常: {e}")
                    results[name] = None
        
        return results
    
    def test_all(self) -> Dict[str, bool]:
        """测试所有提供商"""
        results = {}
        for name, provider in self.providers.items():
            try:
                ok = provider.test()
                results[name] = ok
                logger.info(f"测试 {name}: {'通过' if ok else '失败'}")
            except Exception as e:
                results[name] = False
                logger.error(f"测试 {name} 异常: {e}")
        return results
    
    def get_status(self) -> Dict:
        """获取所有提供商状态"""
        return {
            name: {
                "status": p.config.status.value,
                "models": [m.id for m in p.config.models],
                "success_count": p.config.success_count,
                "error_count": p.config.error_count,
            }
            for name, p in self.providers.items()
        }
    
    def get_free_models(self) -> List[ModelInfo]:
        """获取所有免费模型"""
        free_models = []
        for provider in self.providers.values():
            for m in provider.config.models:
                if m.free:
                    free_models.append(m)
        return free_models


# 便捷函数
_client = None

def get_client() -> UnifiedLLMClient:
    global _client
    if _client is None:
        _client = UnifiedLLMClient()
    return _client


def chat(messages: List[Dict], **kwargs) -> Optional[str]:
    """快捷调用"""
    return get_client().chat(messages, **kwargs)


def chat_parallel(messages: List[Dict], **kwargs) -> Dict[str, Optional[str]]:
    """快捷并行调用"""
    return get_client().chat_parallel(messages, **kwargs)


if __name__ == "__main__":
    # 测试
    print("=" * 60)
    print("统一 LLM 客户端测试")
    print("=" * 60)
    
    client = UnifiedLLMClient()
    
    # 测试所有提供商
    print("\n[测试连通性]")
    results = client.test_all()
    
    print("\n[状态汇总]")
    status = client.get_status()
    for name, info in status.items():
        print(f"  {name}: {info['status']} (成功:{info['success_count']}, 失败:{info['error_count']})")
    
    print("\n[免费模型]")
    free = client.get_free_models()
    for m in free:
        print(f"  {m.provider}: {m.id}")
    
    print("\n[单次调用测试]")
    test_msg = [{"role": "user", "content": "Say hello in Chinese"}]
    result = client.chat(test_msg, max_tokens=20)
    print(f"结果: {result}")
    
    print("\n[并行调用测试]")
    results = client.chat_parallel(test_msg, max_tokens=20)
    for name, res in results.items():
        print(f"  {name}: {res[:50] if res else 'None'}")