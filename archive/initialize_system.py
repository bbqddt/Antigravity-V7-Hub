import os

def initialize():
    """初始化数据阵地 - 自动使用当前项目目录"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    data_dir = os.path.join(base_dir, 'data')
    target_file = os.path.join(data_dir, 'lottery_history.csv')

    print(f"🚀 开始初始化阵地: {base_dir}")

    try:
        if not os.path.exists(data_dir):
            os.makedirs(data_dir)
            print(f"✅ 成功创建目录: {data_dir}")
        else:
            print(f"ℹ️ 目录已存在，准备注入数据。")

        content = "期号,红球,蓝球\n"
        samples = [
            "2026032,02 05 12 18 24 31,07",
            "2026031,01 08 15 22 26 33,04",
            "2026030,03 07 11 21 25 30,12",
            "2026029,05 09 14 23 28 32,01",
            "2026028,06 10 16 20 27 29,15",
            "2026027,04 11 13 19 25 32,08",
            "2026026,02 07 15 22 26 30,03",
            "2026025,01 09 14 21 28 33,11",
            "2026024,05 12 18 24 27 31,06",
            "2026023,03 08 16 23 29 32,14"
        ]

        with open(target_file, 'w', encoding='utf-8-sig') as f:
            f.write(content + "\n".join(samples))

        print(f"✅ 数据已强行落地: {target_file}")
        print("\n🔥 统帅，现在您可以检查数据目录了！")

    except Exception as e:
        print(f"❌ 强建失败，原因可能是目录权限受限: {e}")

if __name__ == "__main__":
    initialize()
