import openai
import pandas as pd
import time
import os
import re
import streamlit as st
import concurrent.futures
from kaggle_sync import sync_latest_data 

# --- 1. 核心配置：OpenRouter 统帅钥匙 ---
OR_KEY = "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"
client = openai.OpenAI(
    api_key=OR_KEY,
    base_url="https://openrouter.ai/api/v1"
)

# --- 2. 物理提取器：将“审计文字”转为“表格数据” ---
def extract_logic_numbers(text):
    """
    核心：从模型的逻辑报告中强行提取 043 期红蓝球
    防止 KeyError: 'reds' 报错
    """
    # 提取红球 (01-33)
    reds = re.findall(r'\b(0[1-9]|[12]\d|3[0-3])\b', text)
    # 提取蓝球 (01-16)
    blues = re.findall(r'\b(0[1-9]|1[0-6])\b', text)
    
    # 格式化数据：取前6个独特红球，取最后1个蓝球
    final_reds = sorted(list(set(reds)))[:6]
    # 容错：如果没提取到，给一组逻辑兜底
    if len(final_reds) < 6:
        final_reds = ["07", "12", "13", "19", "22", "24"]
    
    final_blue = blues[-1] if blues else "16"
    
    return {
        "reds": final_reds,
        "blue": final_blue,
        "raw_report": text
    }

# --- 3. 联合作战矩阵：并发调度 ---
def matrix_audit_logic(data_info):
    council
