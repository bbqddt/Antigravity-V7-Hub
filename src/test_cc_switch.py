# -*- coding: utf-8 -*-
"""测试 CC Switch 接入"""
import sys
sys.path.insert(0, 'e:/享中')

from llm_innovation.llm_engine import LLMEngine

engine = LLMEngine()
print("=== CC Switch 接入测试 ===")
print(f"可用供应商数量: {len(engine.providers)}")
print("供应商列表（按优先级）:")
for name, p in sorted(engine.providers.items(), key=lambda x: x[1].get('priority', 99)):
    print(f"  优先级 {p['priority']}: {name}")

if 'cc_switch' in engine.providers:
    print("\n[OK] CC Switch 已成功接入！正在测试调用...")
    result = engine.generate("用一句话介绍双色球彩票")
    print(f"回复: {result[:120] if result else '(无响应)'}")
else:
    print("\n[WARN] CC Switch 未检测到（可能CC Switch未运行），将自动使用备用供应商")
