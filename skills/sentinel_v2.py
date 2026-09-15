import logging
import subprocess
import time
import socket
import sys
from pathlib import Path

# 日志配置（使用 logging 而非重定向 stdout）
_BASE_DIR = Path(__file__).resolve().parent.parent
_LOG_FILE = _BASE_DIR / "sentinel_runtime.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(str(_LOG_FILE), encoding='utf-8'),
        logging.StreamHandler(sys.stdout),
    ]
)
logger = logging.getLogger("SentinelV2")

VENV_PYTHON = _BASE_DIR / ".venv" / "Scripts" / "python.exe"
# pythonw.exe 可能不存在，优先尝试 python.exe
if not VENV_PYTHON.exists():
    VENV_PYTHON = Path("python")

def check_port(port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)
    result = sock.connect_ex(('127.0.0.1', port))
    sock.close()
    return result == 0

def count_process(script_name):
    """用 wmic 检查某个脚本的运行实例数"""
    try:
        output = subprocess.check_output(
            ["wmic", "process", "where", "name='python.exe' or name='pythonw.exe'", "get", "CommandLine"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode('utf-8', errors='ignore')
        return sum(1 for line in output.splitlines() if script_name in line)
    except Exception:
        return -1

def kill_process(script_name):
    """精准杀掉匹配的进程，绝不误伤"""
    try:
        output = subprocess.check_output(
            ["wmic", "process", "where", "name='python.exe' or name='pythonw.exe'", "get", "CommandLine,ProcessId"],
            stderr=subprocess.DEVNULL, timeout=5
        ).decode('utf-8', errors='ignore')
        for line in output.splitlines():
            if script_name in line:
                parts = line.strip().split()
                pid = parts[-1]
                if pid.isdigit():
                    subprocess.run(["taskkill", "/f", "/pid", pid], capture_output=True)
    except Exception:
        pass

def spawn(script_path):
    """拉起一个干净的隐藏进程"""
    subprocess.Popen(
        [VENV_PYTHON, script_path],
        creationflags=subprocess.CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def heal_system():
    # 1. 监控 TG Remote Hub (进程检测)
    tg_count = count_process("tg_remote_hub.py")
    if tg_count == 0:
        spawn(str(_BASE_DIR / "skills" / "tg_remote_hub.py"))
    elif tg_count > 1:
        kill_process("tg_remote_hub.py")
        time.sleep(2)
        spawn(str(_BASE_DIR / "skills" / "tg_remote_hub.py"))

    # 2. 监控 127.0.0.1:12654 (无限算力代理)
    if not check_port(12654):
        api_count = count_process("local_api_proxy.py")
        if api_count == 0:
            spawn(str(_BASE_DIR / "local_api_proxy.py"))
        elif api_count > 1:
            kill_process("local_api_proxy.py")
            time.sleep(2)
            spawn(str(_BASE_DIR / "local_api_proxy.py"))

    # 3. 监控观测塔 (端口 8501)
    if not check_port(8501):
        streamlit_exe = str(_BASE_DIR / ".venv" / "Scripts" / "streamlit.exe")
        app_py = str(_BASE_DIR / "app.py")
        if Path(streamlit_exe).exists():
            app_count = count_process("app.py")
            if app_count > 0:
                kill_process("app.py")
                time.sleep(1)
            subprocess.Popen(
                [streamlit_exe, "run", app_py, "--server.port", "8501", "--server.headless", "true"],
                creationflags=subprocess.CREATE_NO_WINDOW,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL
            )

if __name__ == "__main__":
    while True:
        try:
            heal_system()
        except Exception:
            pass
        time.sleep(30)
