# -*- coding: utf-8 -*-
"""
HuggingFace API 客户端
用于双色球数据分析预测
支持多个HF模型
"""
import sys
import json
import time
import requests

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

class HuggingFaceClient:
    """HuggingFace Inference API 客户端"""

    # 可用的文本生成模型 (使用serverless inference endpoints)
    MODELS = {
        "qwen": "https://api-inference.huggingface.co/models/Qwen/Qwen2.5-7B-Instruct",
        "mistral": "https://api-inference.huggingface.co/models/mistralai/Mistral-7B-Instruct-v0.3",
        "phi3": "https://api-inference.huggingface.co/models/microsoft/Phi-3-mini-128k-instruct",
    }

    def __init__(self, api_key=None, model="qwen"):
        if api_key:
            self.api_key = api_key
        else:
            try:
                with open('../api_keys.json', 'r') as f:
                    cfg = json.load(f)
                    self.api_key = cfg.get('huggingface_api_key', '')
            except:
                self.api_key = ""

        if not self.api_key:
            import os
            self.api_key = os.environ.get('HF_API_KEY', '')

        self.model_name = model
        # 注意: HF API有SSL问题，这里使用router endpoint
        self.url = f"https://router.huggingface.co/hf-inference/models/{model}"
    
    def _build_prompt(self, draws, latest_draws=5):
        """构建分析prompt"""
        recent = draws[-latest_draws:]
        data_text = "\n".join(
            f"#{d.period}: 红球{d.reds} 蓝球{d.blue}" for d in recent
        )
        return (
            f"<s>[INST] 双色球最近{latest_draws}期开奖数据:\n{data_text}\n"
            f"总共{len(draws)}期数据。\n\n"
            f"请分析:\n"
            f"1. 热号和冷号\n"
            f"2. 遗漏值分析\n"
            f"3. 对下一期的具体选号建议: 红球6个(1-33)和蓝球1个(1-16)\n\n"
            f"请用JSON格式输出:\n"
            f'{{"hot_numbers": [数字列表], "cold_numbers": [数字列表],'
            f'"red_balls": [6个红球数字], "blue_ball": 蓝球数字,'
            f'"reasoning": "分析理由"}}\n[/INST]\n'
        )
    
    def predict(self, draws, top_k=3, temperature=0.7):
        """
        调用HF API进行预测
        
        Args:
            draws: 历史开奖数据
            top_k: 生成几组预测
            temperature: 采样温度
            
        Returns:
            预测结果字典
        """
        predictions = []
        
        for i in range(top_k):
            prompt = self._build_prompt(draws)
            
            payload = {
                "inputs": prompt,
                "parameters": {
                    "max_new_tokens": 1500,
                    "temperature": temperature,
                    "top_p": 0.9,
                    "return_full_text": False,
                }
            }
            
            try:
                resp = requests.post(
                    self.url,
                    json=payload,
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json"
                    },
                    timeout=120
                )
                
                if resp.status_code == 429:
                    # Rate limited, wait and retry
                    time.sleep(5)
                    resp = requests.post(
                        self.url,
                        json=payload,
                        headers={
                            "Authorization": f"Bearer {self.api_key}",
                            "Content-Type": "application/json"
                        },
                        timeout=120
                    )
                
                resp.raise_for_status()
                result = resp.json()
                
                # 解析结果
                content = result[0]['generated_text'] if isinstance(result, list) else str(result)
                parsed = self._parse_response(content)
                if parsed:
                    predictions.append(parsed)
                    
            except Exception as e:
                print(f"  HF预测失败 (尝试 {i+1}/{top_k}): {e}")
                continue
        
        return {
            "engine": f"HuggingFace({self.model_name})",
            "model": self.model_name,
            "predictions": predictions,
            "status": "ok" if predictions else "error",
        }
    
    def _parse_response(self, content):
        """从LLM响应中提取预测"""
        import re
        predictions = []
        
        # 尝试JSON解析
        json_match = re.search(r'\{[^{}]*"red_balls"[^{}]*\}', content, re.DOTALL)
        if json_match:
            try:
                data = json.loads(json_match.group())
                reds = sorted([int(x) for x in data.get('red_balls', []) if 1 <= int(x) <= 33])
                blue = int(data.get('blue_ball', 0)) if 1 <= int(data.get('blue_ball', 0)) <= 16 else 0
                if len(reds) == 6:
                    return {"reds": reds, "blue": blue, "reasoning": data.get('reasoning', '')}
            except:
                pass
        
        # 启发式提取
        nums = re.findall(r'\b(\d{1,2})\b', content)
        valid_nums = [int(n) for n in nums if 1 <= int(n) <= 33]
        if len(valid_nums) >= 6:
            return {
                "reds": sorted(valid_nums[:6]),
                "blue": int(nums[6]) if len(nums) > 6 and 1 <= int(nums[6]) <= 16 else 0,
                "reasoning": content[:200]
            }
        
        return None
    
    def predict_multiple_models(self, draws, top_k=3):
        """
        使用多个HF模型进行预测（投票融合）
        
        Returns:
            多模型预测结果
        """
        results = {}
        for model_name in ["mistral", "phi3", "qwen"]:
            try:
                client = HuggingFaceClient(api_key=self.api_key, model=model_name)
                result = client.predict(draws, top_k=top_k)
                results[model_name] = result
                print(f"  [{model_name}] {len(result.get('predictions', []))}组预测")
            except Exception as e:
                results[model_name] = {"status": "error", "error": str(e)}
                print(f"  [{model_name}] 失败: {e}")
        
        return results


if __name__ == "__main__":
    # 测试HF客户端
    client = HuggingFaceClient()
    print(f"HF API Key: {'*' * 8}{client.api_key[-4:]}")
    print(f"Model URL: {client.url}")
    
    sys.path.insert(0, '..')
    from data_layer import load_history
    draws = load_history()
    print(f"数据: {len(draws)}期")
    
    result = client.predict(draws, top_k=3)
    print(f"状态: {result['status']}")
    if result['status'] == 'ok':
        for i, p in enumerate(result['predictions'], 1):
            print(f"  预测{i}: 红{p['reds']} 蓝{p['blue']}")
