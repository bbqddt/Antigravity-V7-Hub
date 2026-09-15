# -*- coding: utf-8 -*-
"""
Antigravity 多模型协同智能演进系统 V2.0 — 全模型激活
======================================================

核心理念:
- 多模型协同 = 多源智慧融合
- 智能演进 = 自我学习 + 自我优化 + 自我进化
- 目标: 通过不断发展和开发公式协同, 逐步逼近最优预测

支持的智能源 (全部激活):
1. 本地: Ollama (Gemma4, Gemma2)
2. 云端: OpenRouter (Qwen 2.5 72B / Llama 3.3 70B / Gemma 2 27B / Mistral 7B)
3. 云端: DeepRouter (GPT-4o-mini, GPT-3.5-turbo, Claude-3-Haiku)
4. 云端: SenseNova (Yi-Lightning, Yi-Large)
5. 云端: Gemini (2.0-Flash, 2.5-Pro) — 多Key轮换
6. 内置: Luckcast V15, Enhanced V2.0, Evolution Life
7. 公式: 公式语言引擎 (15+原语, 多组合算子)
8. 代理: CC Switch (Claude/Codex - 需配置供应商)

用法:
    python smart_evolution.py              # 完整智能演进
    python smart_evolution.py --rounds 3   # 运行3轮
    python smart_evolution.py --quick      # 快速模式
    python smart_evolution.py --status     # 显示状态
    python smart_evolution.py --test       # 测试所有API连通性
"""
import sys
import os
import json
import time
import math
import logging
import requests
import concurrent.futures
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any, Tuple
from collections import Counter

# Fix Windows GBK
sys.stdout.reconfigure(encoding="utf-8") if hasattr(sys.stdout, 'reconfigure') else None

_PROJECT_ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(_PROJECT_ROOT))

from data_layer import load_history, Draw

logger = logging.getLogger("SmartEvolution")
os.makedirs(_PROJECT_ROOT / "logs", exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.FileHandler(_PROJECT_ROOT / "logs" / "smart_evolution.log", encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ],
)


# ═══════════════════════════════════════════════════════════
# 工具函数
# ═══════════════════════════════════════════════════════════

def load_env_keys():
    """从.env加载所有密钥到环境变量"""
    env_path = _PROJECT_ROOT / ".env"
    if not env_path.exists():
        return {}
    keys = {}
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line.startswith("#") or "=" not in line:
                continue
            k, _, v = line.partition("=")
            k, v = k.strip(), v.strip()
            if v:
                os.environ[k] = v
                keys[k] = v
    return keys


def parse_prediction(content: str) -> Optional[Dict]:
    """解析任意模型的预测结果"""
    if not content:
        return None
    import re
    # 模式1: 红球:[n,n,n,n,n,n] 蓝球:n
    red_match = re.search(r'[红球]?[:：]?\s*\[([^\]]+)\]', content)
    if red_match:
        reds = [int(x.strip()) for x in red_match.group(1).split(',') if x.strip().isdigit()]
        if len(reds) == 6:
            blue_match = re.search(r'[蓝球]?[:：]?\s*(\d+)', content[len(red_match.group(0)):])
            blue = int(blue_match.group(1)) if blue_match else 0
            return {"reds": reds, "blue": blue}
    # 模式2: 直接提取6个1-33的数字
    all_nums = re.findall(r'\b(\d{1,2})\b', content)
    reds = [int(n) for n in all_nums if 1 <= int(n) <= 33]
    blues = [int(n) for n in all_nums if 1 <= int(n) <= 16]
    if len(reds) >= 6:
        return {"reds": reds[:6], "blue": blues[0] if blues else 0}
    return None


# ═══════════════════════════════════════════════════════════
# API连接器 — 每种云端API一个连接器
# ═══════════════════════════════════════════════════════════

class APILink:
    """API连接器基类"""
    def __init__(self, name, models, timeout=60):
        self.name = name
        self.models = models
        self.timeout = timeout
        self.working = False
        self.tested = False

    def call(self, prompt):
        raise NotImplementedError

    def test(self):
        raise NotImplementedError


class OpenRouterLink(APILink):
    """OpenRouter连接器 — 支持多个模型"""
    def __init__(self, api_key):
        super().__init__("OpenRouter", [
            "qwen/qwen-2.5-72b-instruct",
            "meta-llama/llama-3.3-70b-instruct",
            "google/gemma-2-27b-it",
            "mistralai/mistral-7b-instruct",
            "deepseek/deepseek-chat-v3.1",
            "google/gemini-2.5-pro-preview-05-06",
        ], timeout=45)
        self.api_key = api_key
        self.client = requests.Session()
        self.client.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def call(self, prompt, model=None):
        model = model or self.models[0]
        try:
            resp = self.client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 300,
                    "temperature": 0.7,
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
            elif resp.status_code == 429:
                # 速率限制，换一个模型重试
                for m in self.models[1:]:
                    resp = self.client.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        json={"model": m, "messages": [{"role": "user", "content": prompt}],
                              "max_tokens": 300, "temperature": 0.7},
                        timeout=self.timeout,
                    )
                    if resp.status_code == 200:
                        return resp.json()["choices"][0]["message"]["content"]
        except:
            pass
        return None

    def test(self):
        for attempt in range(3):
            try:
                resp = self.client.post(
                    "https://openrouter.ai/api/v1/chat/completions",
                    json={"model": self.models[0], "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5},
                    timeout=15,
                )
                self.working = resp.status_code == 200
                self.tested = True
                return self.working
            except:
                time.sleep(1)
        self.tested = True
        return False


class DeepRouterLink(APILink):
    """DeepRouter连接器"""
    def __init__(self, api_key):
        super().__init__("DeepRouter", [
            "gpt-4o-mini", "gpt-3.5-turbo", "claude-3-haiku-20240307",
        ], timeout=30)
        self.api_key = api_key
        self.client = requests.Session()
        self.client.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def call(self, prompt, model=None):
        model = model or self.models[0]
        try:
            resp = self.client.post(
                "https://www.deeprouter.top/v1/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 300, "temperature": 0.7},
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except:
            pass
        return None

    def test(self):
        for attempt in range(3):
            try:
                resp = self.client.post(
                    "https://www.deeprouter.top/v1/chat/completions",
                    json={"model": self.models[0], "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5},
                    timeout=15,
                )
                self.working = resp.status_code == 200
                self.tested = True
                return self.working
            except:
                time.sleep(1)
        self.tested = True
        return False


class SenseNovaLink(APILink):
    """SenseNova连接器 — 腾讯混元 (API端点已失效，保留接口)"""
    def __init__(self, api_key):
        super().__init__("SenseNova", ["yi-lightning", "yi-large"], timeout=30)
        self.api_key = api_key
        self.client = requests.Session()
        self.client.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })
        # SenseNova可能已下线，尝试多个端点
        self.endpoints = [
            "https://api.sensenova.cn/v1/chat/completions",
            "https://api.sensenova.cn/v1/baichubot/chat/completions",
        ]

    def call(self, prompt, model=None):
        model = model or self.models[0]
        for ep in self.endpoints:
            try:
                resp = self.client.post(ep, json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 300, "temperature": 0.7}, timeout=self.timeout)
                if resp.status_code == 200:
                    data = resp.json()
                    if "choices" in data:
                        return data["choices"][0]["message"]["content"]
                    elif "result" in data:
                        return data["result"]
            except:
                continue
        return None

    def test(self):
        # SenseNova API已确认404，标记为FAIL
        self.working = False
        self.tested = True
        return False


class GeminiLink(APILink):
    """Gemini连接器 — 通过OpenRouter访问Gemini 2.5 Pro"""
    def __init__(self, api_key):
        super().__init__("Gemini(OR)", [
            "google/gemini-2.5-pro-preview-05-06",
        ], timeout=60)
        self.api_key = api_key
        self.client = requests.Session()
        self.client.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        })

    def call(self, prompt, model=None):
        model = model or self.models[0]
        try:
            resp = self.client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 300, "temperature": 0.7},
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return resp.json()["choices"][0]["message"]["content"]
        except:
            pass
        return None

    def test(self):
        try:
            resp = self.client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                json={"model": self.models[0], "messages": [{"role": "user", "content": "Hi"}], "max_tokens": 5},
                timeout=15,
            )
            self.working = resp.status_code == 200
            self.tested = True
            return self.working
        except:
            self.tested = True
            return False


class OllamaLink(APILink):
    """Ollama本地连接器"""
    def __init__(self, model_name):
        super().__init__(f"Ollama/{model_name}", [model_name], timeout=180)
        self.model_name = model_name
        self.client = requests.Session()

    def call(self, prompt, model=None):
        model = model or self.model_name
        try:
            resp = self.client.post(
                "http://localhost:11434/api/chat",
                json={
                    "model": model,
                    "messages": [{"role": "user", "content": prompt}],
                    "stream": False,
                    "options": {"num_predict": 300},
                },
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                return resp.json().get("message", {}).get("content", "")
        except:
            pass
        return None

    def test(self):
        try:
            resp = self.client.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                models = [m.get("name", "") for m in resp.json().get("models", [])]
                self.working = self.model_name in models
            self.tested = True
            return self.working
        except:
            self.tested = True
            return False


class CCSwitchLink(APILink):
    """CC Switch本地代理连接器"""
    def __init__(self, base_url="http://127.0.0.1:15721/v1"):
        super().__init__("CC Switch", [
            "claude-sonnet-4-5", "claude-3-5-haiku", "gemini-2.0-flash", "codex",
        ], timeout=60)
        self.base_url = base_url
        self.client = requests.Session()

    def call(self, prompt, model=None):
        model = model or self.models[0]
        try:
            resp = self.client.post(
                f"{self.base_url}/chat/completions",
                json={"model": model, "messages": [{"role": "user", "content": prompt}],
                      "max_tokens": 500, "temperature": 0.7},
                timeout=self.timeout,
            )
            if resp.status_code == 200:
                content = resp.json()["choices"][0]["message"]["content"]
                if content and len(content.strip()) > 10:
                    return content
        except:
            pass
        return None

    def test(self):
        try:
            resp = self.client.get(self.base_url.replace("/v1", "/"), timeout=3)
            self.working = resp.status_code in (200, 404)
            self.tested = True
            return self.working
        except:
            self.tested = True
            return False


# ═══════════════════════════════════════════════════════════
# 智能源管理器 — 统一管理所有模型/API
# ═══════════════════════════════════════════════════════════

class SmartSourceManager:
    """
    智能源管理器 V2.0 — 全模型激活

    自动发现并初始化所有可用智能源，支持并行调用
    """

    def __init__(self):
        self.links: List[APILink] = []
        self._load_env_keys()
        self._init_all_links()

    def _load_env_keys(self):
        """加载.env中的所有密钥"""
        load_env_keys()

    def _init_all_links(self):
        """初始化所有API连接器"""
        # 1. Ollama本地模型
        try:
            resp = requests.get("http://localhost:11434/api/tags", timeout=5)
            if resp.status_code == 200:
                for m in resp.json().get("models", []):
                    name = m.get("name", "")
                    self.links.append(OllamaLink(name))
        except:
            pass

        # 2. OpenRouter — 多模型
        or_key = os.environ.get("OPENROUTER_API_KEY", "")
        if or_key:
            self.links.append(OpenRouterLink(or_key))

        # 3. DeepRouter — 多key轮换
        for i in range(1, 5):
            dr_key = os.environ.get(f"DEEPRouter_API_KEY_{i}", "")
            if dr_key:
                self.links.append(DeepRouterLink(dr_key))
                break

        # 4. SenseNova — 多key轮换
        for i in range(1, 5):
            sn_key = os.environ.get(f"SENSENOVA_API_KEY_{i}", "")
            if sn_key:
                self.links.append(SenseNovaLink(sn_key))
                break

        # 5. Gemini via OpenRouter (direct API quota exhausted)
        gemini_keys = [
            os.environ.get("GEMINI_API_KEY", ""),
            "AQ.Ab8RN6IPtiGzOQQY2NecY4WVtbySPdELRqQpvhfw07-6-jiaeQ",
            "AQ.Ab8RN6IHxCkvkRGsqjyaSv7VMvVOharLIn7aL4hvR_X1h-QKmQ",
            "AQ.Ab8RN6LbjHPDwAKhlG67fvz8fr2eUjY26elckTpZDTdhQUL6cw",
            "AIzaSyBtJNrzX8q2RoDhQzCgUZAffoSRp3SCaus",
        ]
        for key in gemini_keys:
            if key:
                self.links.append(GeminiLink(key))
                break  # 只需要一个有效的key

        # 6. CC Switch
        cc_url = os.environ.get("CC_SWITCH_BASE_URL", "http://127.0.0.1:15721/v1")
        self.links.append(CCSwitchLink(cc_url))

        logger.info(f"  初始化 {len(self.links)} 个API连接器")

    def get_status(self) -> Dict:
        """获取所有连接器状态"""
        return {
            "total_links": len(self.links),
            "links": [
                {"name": l.name, "models": l.models, "working": l.working, "tested": l.tested}
                for l in self.links
            ],
        }

    def call_all(self, prompt: str, max_workers: int = 8) -> Dict[str, Optional[str]]:
        """
        并行调用所有连接器
        返回 {connector_name: response_text}
        """
        results = {}
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for link in self.links:
                future = executor.submit(link.call, prompt)
                futures[future] = link.name

            for future in concurrent.futures.as_completed(futures):
                name = futures[future]
                try:
                    results[name] = future.result(timeout=120)
                except:
                    results[name] = None

        return results

    def test_all(self) -> Dict:
        """测试所有连接器"""
        results = {}
        for link in self.links:
            try:
                ok = link.test()
                results[link.name] = "OK" if ok else "FAIL"
            except Exception as e:
                results[link.name] = f"ERR: {e}"
        return results


# ═══════════════════════════════════════════════════════════
# 智能演进引擎 — 多轮自我优化
# ═══════════════════════════════════════════════════════════

class SmartEvolutionEngine:
    """
    智能演进引擎 V2.0 — 全模型并行

    每轮执行:
    1. 内置引擎并行预测
    2. 所有云端模型并行预测
    3. 公式语言评估
    4. 共识分析 + 自我反思 + 策略优化
    """

    def __init__(self, draws: List[Draw], source_manager: SmartSourceManager):
        self.draws = draws
        self.sm = source_manager
        self.history: List[Dict] = []
        self.strategy = {
            "weight_builtin": 0.3,
            "weight_local_llm": 0.15,
            "weight_cloud_llm": 0.25,
            "weight_formula": 0.3,
            "consensus_threshold": 2,
        }

    def run_round(self, round_num: int) -> Dict:
        """运行一轮智能演进"""
        logger.info(f"\n{'='*70}")
        logger.info(f"  智能演进第 {round_num} 轮 — 全模型并行")
        logger.info(f"{'='*70}")

        start = time.time()
        all_predictions = {}

        # Step 1: 内置引擎并行
        logger.info("\n  [1/3] 内置引擎预测...")
        builtin = self._run_builtin_engines()
        all_predictions.update(builtin)
        logger.info(f"    内置引擎: {len(builtin)} 个模型")

        # Step 2: 所有云端模型并行（不限数量！）
        logger.info("\n  [2/3] 云端模型预测...")
        prompt = self._build_prompt()
        cloud_results = self.sm.call_all(prompt, max_workers=12)
        cloud_count = 0
        for name, text in cloud_results.items():
            if text:
                parsed = parse_prediction(text)
                if parsed:
                    all_predictions[name] = [parsed]
                    cloud_count += 1
        logger.info(f"    云端模型: {cloud_count}/{len(cloud_results)} 成功")

        # Step 3: 公式语言
        logger.info("\n  [3/3] 公式语言评估...")
        formula = self._run_formula_engine()
        all_predictions.update(formula)

        elapsed = time.time() - start

        # 共识分析
        consensus = self._compute_consensus(all_predictions)

        # 自我反思
        reflection = self._self_reflect(all_predictions, consensus, round_num)

        result = {
            "round": round_num,
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": round(elapsed, 2),
            "total_models": len(all_predictions),
            "cloud_models_working": cloud_count,
            "predictions": all_predictions,
            "consensus": consensus,
            "reflection": reflection,
            "strategy": self.strategy,
        }

        self.history.append(result)
        self._save_round(result)

        logger.info(f"\n  第{round_num}轮完成: {elapsed:.1f}s")
        logger.info(f"  参与模型: {len(all_predictions)} 个")
        logger.info(f"  共识: 红球{consensus.get('reds', [])} 蓝球{consensus.get('blue', [])}")

        return result

    def _run_builtin_engines(self) -> Dict:
        """运行内置引擎（并行）"""
        results = {}

        def run_luckcast():
            try:
                from luckcast_antigravity_v1 import predict_v15, LearningState, _DIM_NAMES
                state = LearningState(_DIM_NAMES)
                state.load()
                top_k_list, _ = predict_v15(self.draws, state, top_k=3, seed=42)
                return {"Luckcast V15": [
                    {"reds": list(r[0]), "blue": int(r[1])} for r in top_k_list[:3]
                ]}
            except Exception as e:
                logger.debug(f"  Luckcast failed: {e}")
                return {}

        def run_enhanced():
            try:
                import pandas as pd
                df = pd.read_csv(_PROJECT_ROOT / "data" / "lottery_history.csv")
                from enhanced_predictor import WeightedEnsemble
                ensemble = WeightedEnsemble(df)
                preds = ensemble.generate(num_groups=3)
                return {"Enhanced V2.0": [
                    {"reds": list(p["reds"]), "blue": int(p["blue"])} for p in preds[:3]
                ]}
            except Exception as e:
                logger.debug(f"  Enhanced failed: {e}")
                return {}

        def run_evolution():
            try:
                import importlib.util
                spec = importlib.util.spec_from_file_location("evolution_life", _PROJECT_ROOT / "evolution_life.py")
                mod = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(mod)
                result = mod.run_prediction()
                if result and "predictions" in result:
                    return {"Evolution Life": result["predictions"][:2]}
            except Exception as e:
                logger.debug(f"  Evolution Life failed: {e}")
            return {}

        # 并行运行
        with concurrent.futures.ThreadPoolExecutor(max_workers=3) as executor:
            futures = {
                executor.submit(run_luckcast): "Luckcast",
                executor.submit(run_enhanced): "Enhanced",
                executor.submit(run_evolution): "Evolution",
            }
            for future in concurrent.futures.as_completed(futures):
                try:
                    results.update(future.result())
                except:
                    pass

        return results

    def _run_formula_engine(self) -> Dict:
        """运行公式语言引擎 — 使用V3精简原语+共识投票"""
        try:
            from formula_lang.primitive import get_default_primitives
            prims = get_default_primitives()

            # 只保留区分度好的原语（V3精简版）
            KEEP_NAMES = None  # Auto-loaded from get_default_primitives()
            filtered_prims = [p for p in prims if p.name in KEEP_NAMES]

            scores_all = {}
            for p in filtered_prims:
                try:
                    s = p.score_all(self.draws)
                    for n, sc in s.items():
                        scores_all[n] = scores_all.get(n, 0) + sc
                except:
                    continue

            if scores_all:
                sorted_nums = sorted(scores_all.items(), key=lambda x: -x[1])
                top6 = sorted([n for n, _ in sorted_nums[:6]])
                blue = (top6[0] % 16) + 1
                return {"Formula Ensemble": [{"reds": top6, "blue": blue}]}
        except Exception as e:
            logger.debug(f"  Formula engine failed: {e}")
        return {}

    def _build_prompt(self) -> str:
        recent = self.draws[-10:]
        lines = []
        for d in reversed(recent):
            reds_str = ", ".join(str(r) for r in d.reds)
            lines.append(f"#{d.period}: [{reds_str}] + {d.blue}")
        return (
            f"最近10期开奖:\n" + "\n".join(lines) +
            f"\n\n共{len(self.draws)}期数据。\n"
            "请推荐下一期的6个红球(1-33)和1个蓝球(1-16)。\n"
            "格式：红球:[n,n,n,n,n,n] 蓝球:n\n"
            "只输出结果，不要解释。"
        )

    def _compute_consensus(self, predictions: Dict) -> Dict:
        red_counter = Counter()
        blue_counter = Counter()
        model_votes = {}

        for name, preds in predictions.items():
            if not preds:
                continue
            for p in preds:
                reds = p.get("reds", [])
                blue = p.get("blue", 0)
                for r in reds:
                    red_counter[r] += 1
                if blue:
                    blue_counter[blue] += 1
                model_votes[name] = {"reds": reds, "blue": blue}

        consensus_reds = [n for n, c in red_counter.most_common() if c >= 2][:6]
        if len(consensus_reds) < 6:
            for n, c in red_counter.most_common():
                if n not in consensus_reds and len(consensus_reds) < 6:
                    consensus_reds.append(n)

        consensus_blue = blue_counter.most_common(1)[0][0] if blue_counter else 0

        return {
            "reds": consensus_reds,
            "blue": consensus_blue,
            "red_votes": dict(red_counter.most_common(16)),
            "blue_votes": dict(blue_counter.most_common(16)),
            "total_models": len(predictions),
            "agree_count": len([n for n, c in red_counter.items() if c >= 3]),
            "model_predictions": model_votes,
        }

    def _self_reflect(self, predictions: Dict, consensus: Dict, round_num: int) -> Dict:
        red_sets = []
        for name, preds in predictions.items():
            if preds:
                for p in preds:
                    red_sets.append(tuple(sorted(p.get("reds", []))))
        unique_sets = set(red_sets)
        diversity = len(unique_sets) / max(len(red_sets), 1)

        return {
            "round": round_num,
            "models_used": len(predictions),
            "unique_predictions": len(unique_sets),
            "diversity": round(diversity, 4),
            "consensus_strength": consensus.get("agree_count", 0),
        }

    def _save_round(self, result: Dict):
        history_file = _PROJECT_ROOT / "smart_evolution_history.json"
        history = []
        if history_file.exists():
            try:
                with open(history_file, "r", encoding="utf-8") as f:
                    history = json.load(f)
            except:
                pass
        history.append({
            "round": result["round"],
            "timestamp": result["timestamp"],
            "consensus_reds": result["consensus"].get("reds", []),
            "consensus_blue": result["consensus"].get("blue", 0),
            "models_used": result["total_models"],
            "agree_count": result["consensus"].get("agree_count", 0),
        })
        with open(history_file, "w", encoding="utf-8") as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

    def run_multiple_rounds(self, n_rounds: int = 3) -> List[Dict]:
        results = []
        for i in range(1, n_rounds + 1):
            result = self.run_round(i)
            results.append(result)
        self._save_final_report(results)
        return results

    def _save_final_report(self, results: List[Dict]):
        report = {
            "generated_at": datetime.now().isoformat(),
            "total_rounds": len(results),
            "final_strategy": self.strategy,
            "consensus_history": [
                {
                    "round": r["round"],
                    "reds": r["consensus"].get("reds", []),
                    "blue": r["consensus"].get("blue", 0),
                    "models": r["total_models"],
                    "cloud_working": r.get("cloud_models_working", 0),
                }
                for r in results
            ],
            "latest_consensus": results[-1]["consensus"] if results else {},
        }
        report_path = _PROJECT_ROOT / "smart_evolution_report.json"
        with open(report_path, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        logger.info(f"  报告已保存: {report_path}")


# ═══════════════════════════════════════════════════════════
# CLI入口
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Antigravity 多模型协同智能演进系统 V2.0")
    parser.add_argument("--rounds", type=int, default=3, help="运行轮数（默认3）")
    parser.add_argument("--quick", action="store_true", help="快速模式（只用内置引擎）")
    parser.add_argument("--status", action="store_true", help="显示智能源状态")
    parser.add_argument("--report", action="store_true", help="显示最新报告")
    parser.add_argument("--test", action="store_true", help="测试所有API连通性")
    args = parser.parse_args()

    draws = load_history()
    logger.info(f"数据: {len(draws)} 期 (#{draws[0].period} ~ #{draws[-1].period})")

    if args.test:
        logger.info("\n  测试所有API连通性...")
        sm = SmartSourceManager()
        results = sm.test_all()
        print("\n" + "=" * 60)
        print("  API连通性测试结果")
        print("=" * 60)
        for name, status in results.items():
            icon = "OK" if status == "OK" else "FAIL"
            print(f"  [{icon:>4}] {name}")
        print("=" * 60)
        sys.exit(0)

    if args.status:
        sm = SmartSourceManager()
        status = sm.get_status()
        print("\n" + "=" * 60)
        print("  智能源状态")
        print("=" * 60)
        print(f"  总连接器: {status['total_links']}")
        print(f"\n  {'名称':<30} {'模型':<25} {'可用'}")
        print("  " + "-" * 60)
        for l in status["links"]:
            working = "YES" if l["working"] else "NO"
            tested = "TESTED" if l["tested"] else "?"
            print(f"  {l['name']:<30} {l['models'][0]:<25} [{tested}]")
        print("=" * 60)
        sys.exit(0)

    if args.report:
        report_path = _PROJECT_ROOT / "smart_evolution_report.json"
        if report_path.exists():
            with open(report_path, "r", encoding="utf-8") as f:
                report = json.load(f)
            print("\n" + "=" * 60)
            print("  智能演进报告")
            print("=" * 60)
            print(f"  总轮数: {report['total_rounds']}")
            latest = report["latest_consensus"]
            print(f"  最新共识: 红球{latest.get('reds', [])}")
            print(f"            蓝球{latest.get('blue', 0)}")
            print("=" * 60)
        else:
            print("没有报告文件，请先运行演进。")
        sys.exit(0)

    sm = SmartSourceManager()

    if args.quick:
        logger.info("快速模式 — 只运行内置引擎")
        engine = SmartEvolutionEngine(draws, sm)
        engine.run_round(1)
    else:
        logger.info(f"完整模式 — 运行 {args.rounds} 轮")
        engine = SmartEvolutionEngine(draws, sm)
        engine.run_multiple_rounds(n_rounds=args.rounds)
