import os
import sys
import subprocess
import json
import ctypes


def trigger_local_alert(title, msg):
    """本地桌面强制置顶弹窗"""
    print(f"[战报] 触发系统级置顶弹窗...")
    ctypes.windll.user32.MessageBoxW(0, msg, title, 0x40000 | 0x00000040)


def main():
    print("========================================")
    print("   [Antigravity V8 绝对本地物理打击]    ")
    print("========================================")
    print("正在启动 V8 零张力物理引擎...")

    group_count = 5
    base_dir = os.path.dirname(os.path.abspath(__file__))

    venv_python = os.path.join(base_dir, ".venv", "Scripts", "python.exe")
    if not os.path.exists(venv_python):
        venv_python = sys.executable

    v8_path = os.path.join(base_dir, "Antigravity_V8_Core.py")
    if not os.path.exists(v8_path):
        trigger_local_alert("Antigravity 警报", f"❌ 未找到核心引擎: {v8_path}")
        return

    try:
        subprocess.run([venv_python, v8_path, str(group_count)], check=True, cwd=base_dir)

        decision_path = os.path.join(base_dir, "latest_decision_v8.json")
        if os.path.exists(decision_path):
            with open(decision_path, "r", encoding='utf-8') as f:
                res = json.load(f)

            period = res.get('target_period', '未知')
            groups = res.get('groups', [])

            raw_msg = f"【期号 {period}】演算完成！\n"
            for idx, g in enumerate(groups, 1):
                raw_msg += f"第{idx}组: 红 {g['red']} | 蓝 {g['blue']:02d}\n"
            raw_msg += "\n(物理计算完成，绝对隔离外网干扰)"

            trigger_local_alert(f"Antigravity V8 绝密传达 (期号 {period})", raw_msg)

            # 尝试通过 TG 备份
            skills_dir = os.path.join(base_dir, "skills")
            if os.path.exists(skills_dir):
                sys.path.insert(0, skills_dir)
                try:
                    import tg_remote_hub
                    tg_msg = f"💠 *Antigravity V8.0 纯物理演算*\n🎯 目标期号: {period}\n\n"
                    for idx, g in enumerate(groups, 1):
                        tg_msg += f"👉 *第{idx}组*: 🔴 `[{g['red']}]` | 🔵 `{g['blue']:02d}`\n"
                    tg_msg += "\n[本消息由本地主动Strike发射]"

                    print("尝试将战果同步至 Telegram...")
                    success = tg_remote_hub.send_tg_msg(tg_msg, max_retries=1)
                    if success:
                        print("✅ 战报同步 Telegram 成功！")
                    else:
                        print("⚠️ Telegram 战报同步失败。数据已安全保留在本地。")
                except ImportError:
                    print("⚠️ Telegram 模块未安装，跳过同步。")
                except Exception as e:
                    print(f"尝试同步 Telegram 时出现异常: {e}")
        else:
            trigger_local_alert("Antigravity 警报", "❌ 演算核心输出断裂: 未找到 latest_decision_v8.json。")
    except Exception as e:
        trigger_local_alert("Antigravity 警报", f"❌ 物理对抗内核启动失败: {e}")


if __name__ == "__main__":
    main()
