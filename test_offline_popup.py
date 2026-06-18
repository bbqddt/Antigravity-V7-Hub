import sys
sys.path.append('E:/享中/skills')
import tg_remote_hub

# 清空嗅探池，强制断网模式
tg_remote_hub.PROXY_PORTS_TO_SNIFF = []
print("Simulating offline mode... Calling V8 Strike.")
tg_remote_hub.execute_v8_strike('计算1组', '/strike')
