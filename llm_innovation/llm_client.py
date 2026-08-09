# -*- coding: utf-8 -*-
"""
Antigravity LLM创新 — Gemini客户端 V2.0

封装Gemini API调用，支持：
- 多模型自动降级 (pro → flash → nano)
- 429配额超限自动等待重试
- 自动从.env或keys.json读取密钥

用法:
    from llm_innovation.llm_client import GeminiClient

    client = GeminiClient()
    if client.available:
        response = client.generate_content("请提出3个新的原语规格")
    else:
        print("LLM不可用，使用本地模式")
"""
import os
import json
import time
from pathlib import Path
from typing import Optional

_PROJECT_ROOT = Path(__file__).resolve().parent.parent


class GeminiClient:
    """Gemini API客户端 — 多模型降级 + 429自动重试"""

    # 模型降级链（按质量从高到低）
    MODEL_CHAIN = [
        "gemini-2.5-pro",
        "gemini-2.0-flash",
        "gemini-2.0-flash-lite",
        "gemini-1.5-flash",
        "gemini-1.5-pro",
    ]

    def __init__(self, model_name: Optional[str] = None):
        self.available = False
        self.client = None
        self.active_model = None

        # 获取API密钥
        api_key = os.environ.get("GEMINI_API_KEY")
        if not api_key:
            keys_file = _PROJECT_ROOT / "keys.json"
            if keys_file.exists():
                try:
                    with open(keys_file, "r") as f:
                        keys = json.load(f)
                        api_key = keys.get("gemini")
                except Exception:
                    pass

        if api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=api_key)
                self.available = True
            except ImportError:
                self.available = False

        self.model_name = model_name or self.MODEL_CHAIN[0]

    def generate_content(self, prompt: str, system_prompt: Optional[str] = None,
                         max_retries: int = 3, retry_delay: int = 40) -> Optional[str]:
        """
        发送内容生成请求，支持多模型降级和429自动重试。

        Args:
            prompt: 用户提示
            system_prompt: 系统提示
            max_retries: 最大重试次数
            retry_delay: 429错误时的等待秒数

        Returns:
            生成的文本，失败时返回None
        """
        if not self.available or not self.client:
            return None

        full_prompt = ""
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n---\n\n{prompt}"
        else:
            full_prompt = prompt

        models_tried = []
        for attempt in range(max_retries):
            for model in self.MODEL_CHAIN:
                if model in models_tried:
                    continue
                models_tried.append(model)
                self.active_model = model

                try:
                    response = self.client.models.generate_content(
                        model=model,
                        contents=full_prompt,
                    )
                    text = response.text

                    # 清理markdown标记
                    if text.startswith("```"):
                        text = text[text.index("\n") + 1:]
                    if text.endswith("```"):
                        text = text[:-4]
                    text = text.strip()

                    return text
                except Exception as e:
                    error_msg = str(e)
                    # 429配额超限 — 等待后重试
                    if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg:
                        wait_time = retry_delay
                        # 从错误信息中提取具体的retry_delay
                        if "retryDelay" in error_msg:
                            try:
                                wait_time = int(error_msg.split("retryDelay': '")[1].split('"')[0])
                            except:
                                pass
                        print(f"[Gemini] 429配额超限，等待{wait_time}s后重试 (模型: {model}, 第{attempt+1}次)")
                        time.sleep(wait_time)
                        models_tried = []  # 清空，下一轮从最高优先级模型重试
                        break
                    # 其他错误 — 换下一个模型
                    elif "model not found" in error_msg.lower() or "404" in error_msg:
                        print(f"[Gemini] 模型{model}不可用，尝试下一个...")
                        continue
                    else:
                        print(f"[Gemini] 错误: {error_msg[:100]}")
                        continue

        print(f"[Gemini] 所有模型尝试完毕，返回None")
        return None

    def is_available(self) -> bool:
        return self.available

    def get_active_model(self) -> Optional[str]:
        return self.active_model

    def __repr__(self):
        status = "available" if self.available else "unavailable (local mode)"
        model_info = f" (active: {self.active_model})" if self.active_model else ""
        return f"<GeminiClient({status}{model_info})>"
