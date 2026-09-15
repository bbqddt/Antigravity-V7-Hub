# -*- coding: utf-8 -*-
"""
Antigravity Evolution Life — 持续进化核心

修复：
1. 路径改为相对项目根目录
2. 期号动态计算
3. sklearn 缺失时优雅降级
4. 模型持久化：保存/加载随机森林模型到 models/ 目录
"""
import numpy as np
import pandas as pd
import json
import os
import pickle
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent

try:
    from sklearn.manifold import SpectralEmbedding
    HAS_SKLEARN = True
except ImportError:
    SpectralEmbedding = None
    HAS_SKLEARN = False

try:
    from sklearn.ensemble import RandomForestRegressor
    HAS_RF = True
except ImportError:
    HAS_RF = False


class EvolutionLife:
    def __init__(self, history_path=None):
        if history_path is None:
            candidates = [
                _PROJECT_ROOT / "data" / "lottery_history.csv",
                _PROJECT_ROOT / "data" / "ssq_history_full.csv",
            ]
            for c in candidates:
                if c.exists():
                    history_path = str(c)
                    break
            if history_path is None:
                print("❌ 未找到历史数据文件")
                return
        self.history_path = history_path
        self.decision_path = str(_PROJECT_ROOT / "latest_decision.json")
        self.model_dir = _PROJECT_ROOT / "models"
        self.model_dir.mkdir(parents=True, exist_ok=True)
        self.red_model_path = self.model_dir / "rf_red_model.pkl"
        self.blue_model_path = self.model_dir / "rf_blue_model.pkl"
        self.meta_path = self.model_dir / "evolution_meta.json"

    def _load_models(self):
        """加载持久化的模型"""
        red_model = None
        blue_model = None
        meta = None

        if self.red_model_path.exists():
            try:
                with open(self.red_model_path, "rb") as f:
                    red_model = pickle.load(f)
            except Exception as e:
                print(f"[WARN] 红球模型加载失败: {e}")

        if self.blue_model_path.exists():
            try:
                with open(self.blue_model_path, "rb") as f:
                    blue_model = pickle.load(f)
            except Exception as e:
                print(f"[WARN] 蓝球模型加载失败: {e}")

        if self.meta_path.exists():
            try:
                with open(self.meta_path, "r", encoding="utf-8") as f:
                    meta = json.load(f)
            except Exception as e:
                print(f"[WARN] 元数据加载失败: {e}")

        return red_model, blue_model, meta

    def _save_models(self, red_model, blue_model, last_train_period):
        """保存模型和训练元数据"""
        try:
            with open(self.red_model_path, "wb") as f:
                pickle.dump(red_model, f)
            with open(self.blue_model_path, "wb") as f:
                pickle.dump(blue_model, f)
            with open(self.meta_path, "w", encoding="utf-8") as f:
                json.dump({
                    "last_train_period": last_train_period,
                    "trained_at": str(Path(self.history_path).stat().st_mtime),
                }, f, indent=2)
            print(f"[INFO] 模型已持久化到 {self.model_dir}")
        except Exception as e:
            print(f"[WARN] 模型保存失败: {e}")

    def _need_retrain(self) -> bool:
        """检查是否需要重新训练模型"""
        if not self.meta_path.exists():
            return True
        try:
            with open(self.meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            # 如果数据文件被修改过，需要重新训练
            data_mtime = Path(self.history_path).stat().st_mtime
            return meta.get("trained_at", "") != str(data_mtime)
        except Exception:
            return True

    def backtest_and_evolve(self):
        print("[INIT] Evolution Life: Entering self-negation phase...")
        df = pd.read_csv(self.history_path)

        latest_period = int(df['period'].iloc[0])
        target_period = latest_period + 1

        # 准备数据
        reds = np.array([list(map(int, r.split(','))) for r in df['red']])
        blues = df['blue'].values.astype(float)

        if HAS_SKLEARN and HAS_RF:
            # 流形嵌入
            se = SpectralEmbedding(n_components=10, affinity='nearest_neighbors')
            features = se.fit_transform(reds)

            train_X = features[:-1]

            # 检查是否需要重新训练
            if self._need_retrain():
                print("[TRAIN] 训练新模型...")
                red_model = RandomForestRegressor(n_estimators=200, random_state=42)
                red_model.fit(train_X, reds[1:])

                blue_model = RandomForestRegressor(n_estimators=100, random_state=42)
                blue_model.fit(train_X, blues[1:])

                # 保存模型
                self._save_models(red_model, blue_model, latest_period)
            else:
                print("[LOAD] 使用持久化模型...")
                red_model, blue_model, meta = self._load_models()
                if red_model is None or blue_model is None:
                    print("[WARN] 持久化模型损坏，重新训练...")
                    red_model = RandomForestRegressor(n_estimators=200, random_state=42)
                    red_model.fit(train_X, reds[1:])
                    blue_model = RandomForestRegressor(n_estimators=100, random_state=42)
                    blue_model.fit(train_X, blues[1:])
                    self._save_models(red_model, blue_model, latest_period)

            current_state = features[-1].reshape(1, -1)
            pred_raw = red_model.predict(current_state)[0]

            pred_reds = sorted([int(round(x)) for x in pred_raw])
            final_reds = []
            for r in pred_reds:
                r = max(1, min(33, r))
                while r in final_reds:
                    r = (r % 33) + 1
                final_reds.append(r)

            pred_blue = int(round(blue_model.predict(current_state)[0]))
            pred_blue = max(1, min(16, pred_blue))
        else:
            # 降级：基于频率的简单预测
            print("[WARN] sklearn unavailable, using frequency fallback...")
            freq = {}
            for r in reds:
                for n in r:
                    freq[n] = freq.get(n, 0) + 1

            # 选出现频率最高的6个号
            sorted_nums = sorted(freq.items(), key=lambda x: -x[1])
            final_reds = [n for n, _ in sorted_nums[:6]]
            while len(final_reds) < 6:
                final_reds.append(len(final_reds) + 1)
            final_reds = sorted(set(final_reds))[:6]

            # 蓝球：选出现频率最高的
            blue_freq = {}
            for b in blues:
                blue_freq[int(b)] = blue_freq.get(int(b), 0) + 1
            pred_blue = max(blue_freq, key=blue_freq.get) if blue_freq else 8

        result = {
            "period": str(target_period),
            "red": sorted(final_reds),
            "blue": pred_blue,
            "engine": "Evolution Life V1.1 (RF+Spectral Persisted)",
            "status": "Computed",
        }

        with open(self.decision_path, "w", encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=4)

        print(f"[SUCCESS] New coordinates evolved: {result['red']} | Blue: {result['blue']}")
        return result


def run_prediction():
    """独立入口函数，供 orchestrator 调用"""
    evolver = EvolutionLife()
    if evolver.history_path:
        return evolver.backtest_and_evolve()
    return None


if __name__ == "__main__":
    evolver = EvolutionLife()
    if evolver.history_path:
        evolver.backtest_and_evolve()
