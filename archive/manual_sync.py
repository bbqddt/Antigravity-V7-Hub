import pandas as pd

new_data = [
    {"period": 26066, "red": "05,11,21,23,24,29", "blue": 16, "date": "2026-06-11"},
    {"period": 26065, "red": "07,08,16,24,30,32", "blue": 2, "date": "2026-06-09"},
    {"period": 26064, "red": "01,09,15,18,29,33", "blue": 15, "date": "2026-06-07"},
    {"period": 26063, "red": "02,08,25,28,30,31", "blue": 2, "date": "2026-06-04"},
    {"period": 26062, "red": "02,04,07,14,28,29", "blue": 9, "date": "2026-06-02"},
    {"period": 26061, "red": "01,04,05,15,23,28", "blue": 7, "date": "2026-05-31"},
    {"period": 26060, "red": "07,09,10,16,22,27", "blue": 11, "date": "2026-05-28"},
    {"period": 26059, "red": "08,16,26,28,29,30", "blue": 15, "date": "2026-05-26"},
    {"period": 26058, "red": "01,04,07,21,29,30", "blue": 1, "date": "2026-05-24"},
    {"period": 26057, "red": "01,10,22,24,28,30", "blue": 7, "date": "2026-05-21"}
]

csv_file = r"E:\享中\data/lottery_history.csv"

# Load existing data
try:
    df = pd.read_csv(csv_file, dtype={"blue": str})
    
    # Check if we already have 26066
    if 26066 not in df['period'].values:
        # Create dataframe for new data
        df_new = pd.DataFrame(new_data)
        # Combine new and old data
        df_combined = pd.concat([df_new, df], ignore_index=True)
        # Drop any duplicates just in case
        df_combined = df_combined.drop_duplicates(subset=["period"], keep="first")
        # Format the blue column to have leading zeros
        df_combined['blue'] = df_combined['blue'].apply(lambda x: f"{int(x):02d}")
        
        # Save back
        df_combined.to_csv(csv_file, index=False)
        print("[SUCCESS] 成功更新 10 期数据！最新期号：26066")
    else:
        print("[WARNING] 数据已存在。最新期号：", df['period'].max())
except Exception as e:
    print(f"Error: {e}")
