# -*- coding: utf-8 -*-
"""
DeepSeek API 客户端
用于双色球数据分析预测
"""
import sys
import json
import time
import requests

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

class DeepSeekClient:
    BASE_URL = "https://api.deepseek.com/chat/completions"
    
    def __init__(self, api_key=None):
        if api_key:
            self.api_key = api_key
        else:
            try:
                with open('../api_keys.json', 'r') as f:
                    cfg = json.load(f)
                    self.api_key = cfg.get('deepseek_api_key', '')
            except:
                self.api_key = ""
        
        if not self.api_key:
            import os
            self.api_key = os.environ.get('DEEPSEEK_API_KEY', '')
    
    def _build_prompt(self, draws, latest_draws=5):
        """构建分析prompt"""
        recent = draws[-latest_draws:]
        data_text = "\n".join(
            f"#{d.period}: 红球{d.reds} 蓝球{d.blue}" for d in recent
        )
        return (
            f"双色球最近{latest_draws}期开奖数据:\n{data_text}\n"
            f"总共{len(draws)}期数据。\n\n"
            f"请分析:\n"
            f"1. 热号(近20期出现>=3次)和冷号(近50期出现<=1次)\n"
            f"2. 遗漏值最大的5个号码\n"
            f"3. 奇偶比、大小比趋势\n"
            f"4. 对下一期的具体选号建议: 给出红球6个(1-33)和蓝球1个(1-16)\n"
            f"5. 每个选号的理由(基于数据支撑)\n\n"
            f"请用JSON格式输出:\n"
            f"{{\n"
            f'  "hot_numbers": [数字列表],\n'
            f'  "cold_numbers": [数字列表],\n'
            f'  "top_omit": [{"number": 数字, "omission": 遗漏期数}],\n'
            f'  "red_balls": [6个红球数字],\n'
            f'  "blue_ball": 蓝球数字,\n'
            f'  "reasoning": "分析理由"\n'
            f"}}\n"
        )
    
    def predict(self, draws, top_k=3, temperature=0.7):
        """
        调用DeepSeek API进行预测
        
        Args:
            draws: 历史开奖数据列表
            top_k: 生成几组预测
            temperature: 采样温度
            
        Returns:
            预测结果字典
        """
        prompt = self._build_prompt(draws, latest_draws=max(5, top_k * 2))
        
        payload = {
            "model": "deepseek-chat",
            "messages": [
                {
                    "role": "system",
                    "content": "你是双色球数据分析专家，精通统计学、概率论和时间序列分析。"
                               "你的任务是分析历史开奖数据，找出隐藏模式，给出下一期预测。"
                               "记住：双色球规则=红球6个(1-33)+蓝球1个(1-16)。"
            },
            {"role": "user", "content": prompt}
            ] * top_k,  # 多轮提问生成多组
            "temperature": temperature,
            "max_tokens": 2000,
            "stream": False,
        }
        
        try:
            resp = requests.post(
                self.BASE_URL,
                json=payload,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json"
                },
                timeout=120
            )
            resp.raise_for_status()
            result = resp.json()
            
            # 解析返回的JSON
            content = result['choices'][0]['message']['content']
            parsed = self._parse_response(content)
            
            return {
                "engine": "DeepSeek",
                "model": "deepseek-chat",
                "predictions": parsed,
                "raw_response": content[:500],
                "status": "ok"
            }
        except Exception as e:
            return {
                "engine": "DeepSeek",
                "status": "error",
                "error": str(e)
            }
    
    def _parse_response(self, content):
        """从LLM响应中提取预测"""
        predictions = []
        
        # 尝试从文本中提取JSON
        import re
        json_match = re.search(r'\{[^{}]*"red_balls"[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                predictions.append({
                    "reds": sorted(data.get('red_balls', [])),
                    "blue": data.get('blue_ball', 0),
                    "reasoning": data.get('reasoning', ''),
                    "hot_numbers": data.get('hot_numbers', []),
                    "cold_numbers": data.get('cold_numbers', []),
                })
            except:
                pass
        
        # 如果没解析到，尝试用启发式方法
        if not predictions:
            nums = re.findall(r'\b(?:red|红)(?:球)?[:\s]*(.+?)\b', content, re.IGNORECASE)
            if nums:
                for n in nums:
                    found = re.findall(r'\d+', n)
                    reds = sorted([int(x) for x in found[:6] if 1 <= int(x) <= 33])
                    blues = [int(x) for x in found[6:7] if 1 <= int(x) <= 16]
                    if len(reds) == 6:
                        predictions.append({
                            "reds": reds,
                            "blue": blues[0] if blues else 0,
                            "reasoning": content[:200],
                        })
        
        return predictions if predictions else [{"reds": [], "blue": 0, "reasoning": content[:300]}]


if __name__ == "__main__":
    # 测试DeepSeek客户端
    client = DeepSeekClient()
    print(f"DeepSeek API Key: {'*' * 8}{client.api_key[-4:]}")
    
    # 加载数据
    sys.path.insert(0, '..')
    from data_layer import load_history
    draws = load_history()
    print(f"数据: {len(draws)}期")
    
    # 运行预测
    result = client.predict(draws, top_k=3)
    print(f"状态: {result['status']}")
    if result['status'] == 'ok':
        for i, p in enumerate(result['predictions'], 1):
            print(f"  预测{i}: 红{p['reds']} 蓝{p['blue']}")
