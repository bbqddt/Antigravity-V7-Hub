import json
import os
import pandas as pd
from datetime import datetime
from pathlib import Path

class PerformanceTracker:
    """
    [Antigravity Omega] 闭环反馈与反噬审判官
    职责：无情地比对上一次推演结果与现实真理。若预测偏离，则生成惩罚性因子。
    """
    def __init__(self, history_csv, decision_json):
        self.history_csv = history_csv
        self.decision_json = decision_json
        _ROOT = Path(__file__).resolve().parent
        self.archive_log = str(_ROOT / "prediction_archive.json")
        self.punishment_file = str(_ROOT / "evolution_context.json")

    def execute_judgment(self):
        print("\n[JUDGMENT] 启动实战回溯审判协议...")
        if not os.path.exists(self.history_csv) or not os.path.exists(self.decision_json):
            print("[JUDGMENT] 缺乏比对数据，审判延后。")
            return self._default_context()

        # 获取现实最新一期
        df = pd.read_csv(self.history_csv)
        real_latest = df.iloc[0]
        real_period = str(real_latest['period'])
        real_reds = set(map(int, real_latest['red'].split(',')))
        real_blue = int(real_latest['blue'])

        # 加载上次预测
        with open(self.decision_json, 'r', encoding='utf-8') as f:
            decision = json.load(f)

        pred_period = decision.get('period', '')
        
        # 存档这一次（为了以后长线跟踪）
        self._archive_decision(decision)

        # 核心逻辑：如果现实已经更新到了我们预测的那一期
        if real_period == pred_period:
            print(f"[JUDGMENT] 真理已刷新至 {real_period}。开始鞭笞校对...")
            pred_reds = set(decision.get('red', []))
            pred_blue = decision.get('blue', 0)

            hit_reds = real_reds.intersection(pred_reds)
            hit_blue = (real_blue == pred_blue)
            red_score = len(hit_reds)
            
            print(f"  > 现实红球: {real_reds}")
            print(f"  > 预测红球: {pred_reds}")
            print(f"  > 命中红球数: {red_score}")
            print(f"  > 命中蓝球: {hit_blue}")

            # 奖惩逻辑与突变因子
            if red_score < 3 and not hit_blue:
                status = "CRITICAL_FAILURE"
                directive = "上期预测惨败！说明现有的特征权重与引力陷阱产生偏差。本次进化必须执行强烈突变，摒弃上次的选号逻辑，引入高维随机噪音！"
            elif red_score >= 3:
                status = "ADAPTIVE_SUCCESS"
                directive = "当前模型特征部分共振现实！继续深化流形降维的引力区，微调边缘数字。"
            else:
                status = "DEVIATION"
                directive = "预测存在系统性偏离，需强化冷热极限定律的筛查。"

            context = {
                "last_target_period": pred_period,
                "hit_reds_count": red_score,
                "hit_blue": hit_blue,
                "status": status,
                "mutation_directive": directive
            }
        else:
            print(f"[JUDGMENT] 现实期号 ({real_period}) 与预测期号 ({pred_period}) 不一致(真理尚未到来或已经错过)，维持正常突变阈值。")
            context = self._default_context()

        # 写出进化因子，供 evolution_life.py 吸食
        with open(self.punishment_file, 'w', encoding='utf-8') as f:
            json.dump(context, f, ensure_ascii=False, indent=4)
        
        return context

    def _archive_decision(self, decision):
        archive = []
        if os.path.exists(self.archive_log):
            try:
                with open(self.archive_log, 'r', encoding='utf-8') as f:
                    archive = json.load(f)
            except: pass
        
        # 防止重复归档同一期
        if not any(d.get('period') == decision.get('period') for d in archive):
            archive.append(decision)
            with open(self.archive_log, 'w', encoding='utf-8') as f:
                json.dump(archive, f, ensure_ascii=False, indent=4)

    def _default_context(self):
        return {
            "status": "NORMAL",
            "mutation_directive": "遵循标准演化规律，根据大数定律进行推演。"
        }

if __name__ == "__main__":
    _ROOT = Path(__file__).resolve().parent
    tracker = PerformanceTracker(
        str(_ROOT / "data" / "lottery_history.csv"),
        str(_ROOT / "latest_decision.json")
    )
    tracker.execute_judgment()
