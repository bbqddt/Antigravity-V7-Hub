import os
import pandas as pd
from pathlib import Path
from luckcast_antigravity_v1 import Draw, rank_candidates

def load_history(csv_path):
    df = pd.read_csv(csv_path, on_bad_lines='skip')
    history = []
    # Order ascending by period, so the oldest is first, newest is last.
    df = df.sort_values('period', ascending=True)

    for _, row in df.iterrows():
        try:
            red_str = str(row['red'])
            blue_val = int(row['blue'])

            reds = [int(x) for x in red_str.split(',') if x.strip().isdigit()]
            if len(reds) == 6:
                history.append(Draw(red=reds, blue=blue_val))
        except:
            continue
    return history

def run():
    print("🚀 Project Zero-T: Structural Tension Evaluation Initiated...")
    _ROOT = Path(__file__).resolve().parent
    csv_file = _ROOT / "data" / "lottery_history.csv"

    history = load_history(str(csv_file))
    
    print(f"Loaded {len(history)} historical draws.")
    
    print("Ranking candidates... (This takes a moment due to mathematical combinations)")
    # run rank_candidates
    final_pool = rank_candidates(history, n_candidates=1000, top_k=3)
    
    print("\n" + "="*60)
    print("  🌌 Zero-T 反重力张力对冲方案 (Top 3)")
    print("="*60)
    
    for idx, (red, blue, scores) in enumerate(final_pool, 1):
        red_fmt = " ".join([f"{x:02d}" for x in red])
        print(f"Option {idx}: [ {red_fmt} ] | Blue: {blue:02d}")
        print(f"  Score: {scores['total_score']} (Struct: {scores['structure_score']} / Disturbance: {scores['disturbance_red_score']})")
        print("-" * 40)
        
if __name__ == "__main__":
    run()
