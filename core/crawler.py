def sync(self):
        print(f"📡 [OpenClaw] 正在从中彩网提取因果数据...")
        # 强制指定保存路径，防止变量丢失
        save_path = "e:/享中/data/ssq_history_full.csv"
        save_dir = "e:/享中/data"
        
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
            
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)'}
        try:
            res = requests.get(self.url, headers=headers)
            res.encoding = 'utf-8'
            
            # 使用 lxml 引擎解析截图 15 中看到的 HTML 结构
            tables = pd.read_html(res.text, flavor='lxml')
            df = tables[0] 
            
            # 这里的清洗逻辑需对应截图 13 的中彩网表格：[期号, 红球, 蓝球]
            df_final = df.iloc[:, [0, 2, 3]]
            df_final.columns = ['id', 'reds', 'blue']
            
            # 落地存储，解决报错的关键一步
            df_final.to_csv(save_path, index=False)
            print(f"✅ [Antigravity] 权威数据已入库：{save_path}")
            return True
        except Exception as e:
            print(f"❌ 链路中断详情: {e}")
            return False