import os
import sys
import subprocess
import json
import ctypes

def trigger_local_alert(title, msg):
    """本地桌面强制置顶弹窗"""
    print(f"[战报] 触发系统级置顶弹窗...")
    # 0x40000 = MB_TOPMOST, 0x00000040 = MB_ICONASTERISK
    ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40000 | 0x00000040)

def main():
    print("========================================")
    print("   [Antigravity V8 绝对本地物理打击]    ")
    print("========================================")
    print("正在启动 V8 零张力物理引擎...")
    
    group_count = 5  # 默认计算 5 组
    v8_path = r"e:\享中\Antigravity_V8_Core.py"
    venv_python = r"e:\享中\.venv\Scripts\python.exe"
    
    try:
        # 直接拉起本地物理计算，完全不依赖网络和代理
        subprocess.run([venv_python, v8_path, str(group_count)], check=True)
        
        decision_path = r"e:\享中\latest_decision_v8.json"
        if os.path.exists(decision_path):
            with open(decision_path, "r", encoding='utf-8') as f:
                res = json.load(f)
            
            period = res.get('target_period', '未知')
            groups = res.get('groups', [])
            
            raw_msg = f"【期号 {period}】演算完成！\n"
            for idx, g in enumerate(groups, 1):
                raw_msg += f"第{idx}组: 红 {g['red']} | 蓝 {g['blue']:02d}\n"
                
            raw_msg += "\n(物理计算完成，绝对隔离外网干扰)"
            
            # 弹窗强制显示结果
            trigger_local_alert(f"Antigravity V8 绝密传达 (期号 {period})", raw_msg)
            
            # 尝试通过 TG 备份（如果网络能通的话）
            try:
                sys.path.append(r"e:\享中\skills")
                import tg_remote_hub
                # 构造 tg 用的 markdown 文本
                tg_msg = f"💠 *Antigravity V8.0 纯物理演算*\n🎯 目标期号: {period}\n\n"
                for idx, g in enumerate(groups, 1):
                    tg_msg += f"👉 *第{idx}组*: 🔴 `[{g['red']}]` | 🔵 `{g['blue']:02d}`\n"
                tg_msg += "\n[本消息由本地主动Strike发射]"
                
                print("尝试将战果同步至 Telegram...")
                success = tg_remote_hub.send_tg_msg(tg_msg, max_retries=1)
                if success:
                    print("✅ 战报同步 Telegram 成功！")
                else:
                    print("⚠️ 网络封锁，Telegram 战报同步失败。数据已安全保留在本地。")
            except Exception as e:
                print(f"尝试同步 Telegram 时出现异常: {e}")
                
        else:
            trigger_local_alert("Antigravity 警报", "❌ 演算核心输出断裂: 未找到 latest_decision_v8.json。")
    except Exception as e:
        trigger_local_alert("Antigravity 警报", f"❌ 物理对抗内核启动失败: {e}")

if __name__ == "__main__":
    main()
