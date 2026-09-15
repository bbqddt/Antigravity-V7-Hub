import os
import asyncio
import pandas as pd
import requests
from bs4 import BeautifulSoup

class SSQCrawler:
    def __init__(self):
        # 500.com 历史数据接口 (newercs 为全量接口)
        self.url = "http://datachart.500.com/ssq/history/newercs.php"

    async def run_open_claw(self, max_pages=1):
        """
        异步入口，完美兼容主引擎的 await 调用。
        内部使用线程池执行同步抓取。
        """
        print(f"📡 [OpenClaw] 正在异步提取实时开奖数据...")
        result = await asyncio.to_thread(self._sync_fetch_and_parse)
        return result

    def run(self, max_pages=1):
        """同步入口，可直接调用"""
        print(f"📡 [OpenClaw] 正在提取实时开奖数据...")
        return self._sync_fetch_and_parse()

    def _sync_fetch_and_parse(self):
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        save_path = os.path.join(base_dir, "data", "lottery_history.csv")
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
        
        try:
            # 1. 抓取页面
            response = requests.get(self.url, headers=headers, timeout=20)
            response.encoding = 'utf-8'
            
            # 2. 直接利用 Pandas 读取 HTML 中的所有表格
            # 500.com 的开奖表格通常是页面中的第一个或唯一一个大表
            tables = pd.read_html(response.text, flavor='lxml')
            if not tables:
                print("❌ 错误：页面中未找到任何数据表格。")
                return False
                
            df_web = tables[0]
            
            # 3. 数据清洗 (针对 500.com 结构)
            # 列名通常包含：期号, 红球, 蓝球 等
            # 根据截图观察，我们需要提取 [期号, 红1, 红2, 红3, 红4, 红5, 红6, 蓝球, 开奖日期]
            # 500.com 原始表格可能存在多级表头或冗余列，这里做强力对齐
            
            # 识别关键列索引 (基于 500.com 典型结构: 0=期号, 1-6=红球, 7=蓝球, 15=日期)
            # 这里的索引需根据真实页面进行微调，此处采用通用偏移量
            df_new = df_web.iloc[:, [0, 1, 2, 3, 4, 5, 6, 7, 15]].copy()
            df_new.columns = ['id', 'r1', 'r2', 'r3', 'r4', 'r5', 'r6', 'b', 'date']
            
            # 转换 ID 为整数，过滤非数字行
            df_new['id'] = pd.to_numeric(df_new['id'], errors='coerce')
            df_new = df_new.dropna(subset=['id']).sort_values('id')
            df_new['id'] = df_new['id'].astype(int)
            
            # 补齐系统要求的冗余 blue 列
            df_new['blue'] = df_new['b']
            
            # 4. 差量更新逻辑
            if os.path.exists(save_path):
                df_local = pd.read_csv(save_path)
                last_id = df_local['id'].max()
                
                # 仅保留比本地更新的数据
                df_to_append = df_new[df_new['id'] > last_id]
                
                if not df_to_append.empty:
                    df_final = pd.concat([df_local, df_to_append], ignore_index=True)
                    df_final.to_csv(save_path, index=False)
                    print(f"✅ 数据自动对齐成功！新增 {len(df_to_append)} 期记录 (最新期号: {df_final['id'].iloc[-1]})")
                else:
                    print("🟢 已经是最新状态，无需追加。")
            else:
                # 首次创建
                df_new.to_csv(save_path, index=False)
                print(f"📦 首次初始化数据库，存入 {len(df_new)} 条记录。")
                
            return True
            
        except Exception as e:
            print(f"❌ 链路同步失败: {e}")
            return False