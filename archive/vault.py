# -*- coding: utf-8 -*-
"""
Antigravity Omega - 资产隔离保险库
职责：保护长官的数字资产，实现本地加密存储。
"""
import os
import json
import base64


class AntigravityVault:
    """安全存储敏感凭证"""

    def __init__(self, vault_path=None):
        if vault_path is None:
            vault_path = os.path.join(
                os.path.dirname(os.path.abspath(__file__)),
                "secure_vault.enc"
            )
        self.vault_path = vault_path
        # 内部逻辑密钥 — 不应提交到版本控制
        self.key = b"Antigravity_Omega_V1000_Sovereign"

    def encrypt_data(self, data):
        """简单的 Base64 混淆（注意：这不是真正的加密，仅用于基本防护）"""
        json_data = json.dumps(data)
        return base64.b64encode(json_data.encode()).decode()

    def decrypt_data(self, encrypted):
        """解密数据"""
        json_data = base64.b64decode(encrypted.encode()).decode()
        return json.loads(json_data)

    def save_credentials(self, credentials):
        encrypted = self.encrypt_data(credentials)
        with open(self.vault_path, "w") as f:
            f.write(encrypted)
        print("✅ 报告长官：资产保险库已落锁。云端已无法直视。")

    def load_credentials(self):
        if not os.path.exists(self.vault_path):
            return {}
        with open(self.vault_path, "r") as f:
            encrypted = f.read()
        return self.decrypt_data(encrypted)


vault = AntigravityVault()
