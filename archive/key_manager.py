# -*- coding: utf-8 -*-
"""
Antigravity 安全密钥管理器 V2.0
从 .env / keys.json / 环境变量 中安全地加载 API Keys
所有密钥不会硬编码在源代码中
"""
import os
import json
from pathlib import Path


class KeyManager:
    """统一管理所有 API Keys"""

    def __init__(self, base_dir=None):
        self.base_dir = base_dir or Path(__file__).resolve().parent.parent
        self._cache = {}
        self._load_env()
        self._load_keys_json()

    def _load_env(self):
        """从 .env 文件加载"""
        env_file = self.base_dir / ".env"
        if env_file.exists():
            with open(env_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if "=" in line and not line.startswith("#"):
                        key, val = line.split("=", 1)
                        self._cache[key.strip()] = val.strip()

    def _load_keys_json(self):
        """从 keys.json 加载（兼容旧格式）"""
        keys_file = self.base_dir / "keys.json"
        if keys_file.exists():
            try:
                with open(keys_file, "r") as f:
                    data = json.load(f)
                if isinstance(data, dict):
                    for k, v in data.items():
                        env_key = k.upper()
                        self._cache[env_key] = str(v)
            except (json.JSONDecodeError, IOError):
                pass

    def get(self, key, default=""):
        """
        获取密钥，优先级：
        1. 环境变量
        2. .env 文件
        3. keys.json
        4. 默认值
        """
        env_val = os.environ.get(key)
        if env_val:
            return env_val
        return self._cache.get(key, default)

    def get_masked(self, key, visible_chars=4):
        """获取脱敏后的密钥用于日志显示"""
        val = self.get(key, "")
        if not val:
            return "(未配置)"
        if len(val) <= visible_chars:
            return "*" * len(val)
        return val[:visible_chars] + "..." + val[-visible_chars:]

    def has_key(self, key):
        """检查密钥是否已配置"""
        return bool(self.get(key, ""))


# 全局单例
_key_manager = None


def get_key_manager():
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


def get_key(key, default=""):
    return get_key_manager().get(key, default)


def get_masked_key(key):
    return get_key_manager().get_masked(key)
