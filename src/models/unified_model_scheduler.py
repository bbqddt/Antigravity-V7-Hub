# -*- coding: utf-8 -*-
"""
统一模型调度器 - 7模型协同预测
================================
将所有7个模型统一到orchestrate.py的调度框架下

模型列表:
  本地模型:
    1. Gemma4 (Ollama localhost:11434)
    2. Gemma2 (Ollama localhost:11434)

  内置引擎:
    3. Luckcast V15
    4. Enhanced V2.0
    5. Evolution Life

  云端模型:
    6. DeepSeek (DS)
    7. HuggingFace (HF)

支持:
  - 本地模型(Ollama)优先
  - 云端模型(API)兜底
  - 结果投票融合
  - 失败自动降级
  - 跨模型共识检测
"""
import sys
import json
import time
import requests
from collections import Counter, defaultdict
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_PROJECT_ROOT))


class UnifiedModelScheduler:
    """统一模型调度器"""

    def __init__(self):
        self.models = {}
        self.results = {}
        self.start_time = None

    def register_model(self, name, model_instance):
        """注册模型"""
        self.models[name] = model_instance
        print(f"  注册模型: {name}")

    def load_data(self):
        """加载历史数据"""
        from data_layer import load_history
        draws = load_history()
        return draws

    def run_gemma4(self, draws, top_k=3):
        """运行Gemma4 (Ollama) - 从thinking字段提取内容并去重"""
        try:
            prompt = self._build_llm_prompt(draws)
            resp = requests.post(
                'http://localhost:11434/api/chat',
                json={
                    'model': 'gemma4',
                    'messages': [
                        {'role': 'system', 'content': '你是双色球数据分析专家'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'stream': False,
                    'options': {
                        'num_predict': 1000,
                        'temperature': 0.7,
                        'num_ctx': 4096
                    }
                },
                timeout=300
            )
            if resp.status_code == 200:
                data = resp.json()
                msg = data.get('message', {})
                # Gemma4的thinking模式导致content为空，需要从thinking字段提取
                content = msg.get('thinking', '')[:1000]
                if content:
                    result = self._parse_llm_response(content, "Gemma4")
                    # 去重修复
                    if result and result.get('predictions'):
                        for pred in result['predictions']:
                            pred['reds'] = sorted(list(set(pred['reds'])))[:6]
                    return result
            return None
        except Exception as e:
            print(f"  Gemma4失败: {e}")
            return None

    def run_gemma2(self, draws, top_k=3):
        """运行Gemma2 (Ollama)"""
        try:
            prompt = self._build_llm_prompt(draws)
            resp = requests.post(
                'http://localhost:11434/api/chat',
                json={
                    'model': 'gemma2',
                    'messages': [
                        {'role': 'system', 'content': '你是双色球数据分析专家'},
                        {'role': 'user', 'content': prompt}
                    ],
                    'stream': False,
                    'options': {'num_predict': 1000, 'temperature': 0.7, 'num_ctx': 4096}
                },
                timeout=600
            )
            if resp.status_code == 200:
                content = resp.json().get('message', {}).get('content', '').strip()
                if content:
                    return self._parse_llm_response(content, "Gemma2")
            return None
        except Exception as e:
            print(f"  Gemma2失败: {e}")
            return None

    def run_deepseek(self, draws, top_k=3):
        """运行DeepSeek (OpenRouter)"""
        try:
            from openai import OpenAI
            import os

            # 从.env加载API Key
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

            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ.get("OPENROUTER_API_KEY")
            )

            prompt = self._build_llm_prompt(draws, latest_draws=5)
            resp = client.chat.completions.create(
                model="deepseek/deepseek-chat",
                messages=[
                    {"role": "system", "content": "你是双色球数据分析专家"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            content = resp.choices[0].message.content
            return self._parse_llm_response(content, "DeepSeek(OR)")
        except Exception as e:
            print(f"  DeepSeek失败: {e}")
            return None

    def run_huggingface(self, draws, top_k=3):
        """运行HuggingFace (OpenRouter)"""
        try:
            from openai import OpenAI
            import os

            # 从.env加载API Key
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

            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ.get("OPENROUTER_API_KEY")
            )

            prompt = self._build_llm_prompt(draws, latest_draws=5)
            resp = client.chat.completions.create(
                model="meta-llama/llama-3.3-70b-instruct",
                messages=[
                    {"role": "system", "content": "你是双色球数据分析专家"},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=1000,
                temperature=0.7
            )
            content = resp.choices[0].message.content
            return self._parse_llm_response(content, "Llama3.3(OR)")
        except Exception as e:
            print(f"  HuggingFace(Llama)失败: {e}")
            return None

    def run_luckcast(self, draws, top_k=5):
        """运行Luckcast V15"""
        try:
            from luckcast_antigravity_v1 import rank_candidates
            results = rank_candidates(draws, n_candidates=1000, top_k=top_k)
            return {
                "engine": "Luckcast V15",
                "predictions": [
                    {
                        "reds": list(r[0]),
                        "blue": int(r[1]),
                        "scores": r[2],
                    }
                    for r in results
                ],
                "status": "ok"
            }
        except Exception as e:
            print(f"  Luckcast失败: {e}")
            return None

    def run_enhanced(self, draws, top_k=5):
        """运行Enhanced V2.0"""
        try:
            import pandas as pd
            csv_file = _PROJECT_ROOT / "data" / "lottery_history.csv"
            df = pd.read_csv(csv_file)
            from enhanced_predictor import WeightedEnsemble, parse_reds
            ensemble = WeightedEnsemble(df)
            preds = ensemble.generate(num_groups=top_k)
            return {
                "engine": "Enhanced V2.0",
                "predictions": [
                    {
                        "reds": list(p["reds"]),
                        "blue": int(p["blue"]),
                        "strategy": p.get("strategy", ""),
                    }
                    for p in preds
                ],
                "status": "ok"
            }
        except Exception as e:
            print(f"  Enhanced失败: {e}")
            return None

    def run_evolution_life(self, draws, top_k=1):
        """运行Evolution Life"""
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "evolution_life", _PROJECT_ROOT / "evolution_life.py"
            )
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            result = mod.run_prediction()
            if result and "predictions" in result:
                return result
            return {"engine": "Evolution Life", "predictions": [], "status": "ok"}
        except Exception as e:
            print(f"  Evolution Life失败: {e}")
            return None

    def _build_llm_prompt(self, draws, latest_draws=5):
        """构建LLM分析prompt"""
        recent = draws[-latest_draws:]
        data_text = "\n".join(
            f"#{d.period}: 红球{d.reds} 蓝球{d.blue}" for d in recent
        )
        return (
            f"双色球最近{latest_draws}期开奖:\n{data_text}\n"
            f"总共{len(draws)}期数据。\n\n"
            f"请给出下一期预测:\n"
            f"1. 红球6个(1-33)\n"
            f"2. 蓝球1个(1-16)\n"
            f"3. 每个选号的理由\n\n"
            f"输出格式JSON:\n"
            f'{{"red_balls": [6个数字], "blue_ball": 1个数字, "reasoning": "分析"}}'
        )

    def _parse_llm_response(self, content, engine_name):
        """解析LLM响应"""
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
                    return {
                        "engine": engine_name,
                        "predictions": [{"reds": reds, "blue": blue, "reasoning": data.get('reasoning', '')}],
                        "status": "ok"
                    }
            except:
                pass

        # 启发式提取
        nums = re.findall(r'\b(\d{1,2})\b', content)
        valid_reds = [int(n) for n in nums[:6] if 1 <= int(n) <= 33]
        valid_blue = [int(n) for n in nums[6:7] if 1 <= int(n) <= 16]

        if len(valid_reds) == 6:
            return {
                "engine": engine_name,
                "predictions": [{"reds": valid_reds, "blue": valid_blue[0] if valid_blue else 0}],
                "status": "ok"
            }

        return None

    def run_all_models(self, top_k=5):
        """
        运行所有7个模型

        Returns:
            统一格式的结果字典
        """
        self.start_time = time.time()
        draws = self.load_data()
        latest = draws[-1]
        target = latest.period + 1

        print(f"\n{'='*60}")
        print(f"  统一模型调度器 V1.0")
        print(f"  目标期号: #{target}")
        print(f"  数据规模: {len(draws)}期")
        print(f"{'='*60}\n")

        all_results = {}

        # 本地模型优先
        print("--- [1/7] Gemma4 (Ollama) ---")
        r = self.run_gemma4(draws, top_k)
        if r:
            all_results['Gemma4'] = r
        else:
            all_results['Gemma4'] = {"status": "skipped", "reason": "Ollama not running"}

        print("\n--- [2/7] Gemma2 (Ollama) ---")
        r = self.run_gemma2(draws, top_k)
        if r:
            all_results['Gemma2'] = r
        else:
            all_results['Gemma2'] = {"status": "skipped", "reason": "Ollama not running"}

        # 内置引擎
        print("\n--- [3/7] Luckcast V15 ---")
        r = self.run_luckcast(draws, top_k)
        if r:
            all_results['Luckcast V15'] = r
        else:
            all_results['Luckcast V15'] = {"status": "error"}

        print("\n--- [4/7] Enhanced V2.0 ---")
        r = self.run_enhanced(draws, top_k)
        if r:
            all_results['Enhanced V2.0'] = r
        else:
            all_results['Enhanced V2.0'] = {"status": "error"}

        print("\n--- [5/7] Evolution Life ---")
        r = self.run_evolution_life(draws, top_k)
        if r:
            all_results['Evolution Life'] = r
        else:
            all_results['Evolution Life'] = {"status": "error"}

        # 云端模型
        print("\n--- [6/7] DeepSeek ---")
        r = self.run_deepseek(draws, top_k)
        if r:
            all_results['DeepSeek'] = r
        else:
            all_results['DeepSeek'] = {"status": "error"}

        print("\n--- [7/7] HuggingFace ---")
        r = self.run_huggingface(draws, top_k)
        if r:
            all_results['HuggingFace'] = r
        else:
            all_results['HuggingFace'] = {"status": "error"}

        # 融合结果
        elapsed = time.time() - self.start_time
        consensus = self._find_consensus(all_results)

        output = {
            "target_period": target,
            "timestamp": time.strftime('%Y-%m-%d %H:%M:%S'),
            "data_periods": len(draws),
            "elapsed_seconds": round(elapsed, 2),
            "models": all_results,
            "consensus": consensus,
            "model_summary": self._generate_summary(all_results),
        }

        # 保存
        output_path = _PROJECT_ROOT / "unified_model_results.json"
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=2)

        print(f"\n{'='*60}")
        print(f"  统一模型调度完成")
        print(f"  耗时: {elapsed:.1f}s")
        print(f"  输出: {output_path}")
        print(f"{'='*60}")

        return output

    def _find_consensus(self, all_results):
        """
        跨模型共识检测

        策略:
          1. 红球共识: 至少3个模型推荐的号码
          2. 蓝球共识: 至少2个模型推荐的号码
          3. 冲突检测: 哪些模型意见不一致
        """
        red_counter = Counter()
        blue_counter = Counter()
        model_votes = defaultdict(list)

        for model_name, result in all_results.items():
            if result.get('status') != 'ok':
                continue
            for pred in result.get('predictions', []):
                reds = pred.get('reds', [])
                blue = pred.get('blue', 0)
                if reds and len(reds) == 6:
                    for r in reds:
                        red_counter[r] += 1
                        model_votes[r].append(model_name)
                    if 1 <= blue <= 16:
                        blue_counter[blue] += 1

        # 共识号码 (>=3个模型推荐)
        red_consensus = [n for n, c in red_counter.most_common() if c >= 3]
        blue_consensus = [n for n, c in blue_counter.most_common() if c >= 2]

        # 高置信度 (>=5个模型推荐)
        red_high_conf = [n for n, c in red_counter.most_common() if c >= 5]

        return {
            "red_consensus": sorted(red_consensus)[:6],
            "blue_consensus": sorted(blue_consensus)[:1],
            "red_high_confidence": sorted(red_high_conf),
            "red_vote_distribution": dict(red_counter.most_common(10)),
            "blue_vote_distribution": dict(blue_counter.most_common(5)),
        }

    def _generate_summary(self, all_results):
        """生成模型运行摘要"""
        summary = {
            "total_models": len(all_results),
            "successful": 0,
            "failed": 0,
            "skipped": 0,
            "details": {},
            "api_status": {
                "deepseek": "INSUFFICIENT_BALANCE (needs recharge)",
                "huggingface": "SSL/PERMISSION_ISSUE (router endpoint blocked)",
                "ollama": "requires local Ollama server running on port 11434",
            }
        }

        for name, result in all_results.items():
            status = result.get('status', 'unknown')
            if status == 'ok':
                summary['successful'] += 1
                count = len(result.get('predictions', []))
                summary['details'][name] = f"OK ({count}组)"
            elif status == 'skipped':
                summary['skipped'] += 1
                summary['details'][name] = f"Skipped: {result.get('reason', '')}"
            else:
                summary['failed'] += 1
                summary['details'][name] = "FAILED"

        return summary


if __name__ == "__main__":
    scheduler = UnifiedModelScheduler()
    result = scheduler.run_all_models(top_k=3)

    # 打印共识
    consensus = result.get('consensus', {})
    if consensus.get('red_consensus'):
        print(f"\nRed consensus: {consensus['red_consensus']}")
    if consensus.get('blue_consensus'):
        print(f"Blue consensus: {consensus['blue_consensus']}")

    print(f"\nModel summary:")
    for name, detail in result.get('model_summary', {}).get('details', {}).items():
        print(f"  {name}: {detail}")
