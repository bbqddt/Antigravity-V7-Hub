import pandas as pd
import re
import os

def auto_paste_and_save():
    print(">>> [实事求是] 准备接收 Web 端审计数据...")
    output_path = r"D:\Antigravity_V7\latest_predictions.csv"

    # 1. 交互式接收粘贴内容
    print("\n请在下方粘贴 AI 生成的推演结果（直接 Ctrl+V，完成后按 Enter 换行并按 Ctrl+Z 结束）:")
    print("-" * 50)
    
    input_lines = []
    while True:
        try:
            line = input()
            input_lines.append(line)
        except EOFError:
            break
    
    raw_text = "\n".join(input_lines)

    # 2. 强大的正则清洗逻辑 (自动抓取 01 02 03... 这种格式)
    # 匹配模式：寻找 6 个红球 + 1 个蓝球的特征
    pattern = r"(\d{2}\s+\d{2}\s+\d{2}\s+\d{2}\s+\d{2}\s+\d{2})\s*[:|｜\s-]\s*(\d{2})"
    matches = re.findall(pattern, raw_text)

    if not matches:
        print("❌ 错误：没在粘贴的内容里找到符合 [00 00 00 00 00 00 | 00] 格式的数据！")
        return

    # 3. 格式化数据
    formatted_results = []
    for red, blue in matches:
        formatted_results.append(f"{red} | {blue}")
    
    final_content = " ; ".join(formatted_results)

    # 4. 写入 CSV
    try:
        # 如果文件不存在，先写表头
        if not os.path.exists(output_path):
            with open(output_path, "w", encoding="utf-8") as f:
                f.write("period,audit_results\n")
        
        with open(output_path, "a", encoding="utf-8") as f:
            f.write(f"2026033,\"{final_content}\"\n")
        
        print(f"\n✨✨✨ [真正合龙] 成功提取到 {len(matches)} 组预测！")
        print(f"数据已自动压入：{output_path}")
        print("-" * 50)
    except Exception as e:
        print(f"💥 写入失败：{e}")

if __name__ == "__main__":
    auto_paste_and_save()
"""
[测试数据暂存区 / 待粘贴数据]
03 07 12 18 25 31 | 06

01 09 14 21 26 30 | 12

05 08 13 19 24 29 | 04

02 06 11 17 23 28 | 15

04 10 15 22 27 32 | 07

07 12 16 20 25 31 | 09

03 08 14 21 26 33 | 02

01 05 11 18 24 30 | 11

06 13 17 22 28 32 | 05

09 15 19 23 27 31 | 13
"""