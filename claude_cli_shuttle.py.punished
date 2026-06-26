import subprocess
import threading
import queue
import time
import os
from flask import Flask, request, jsonify

# [Antigravity Omega] Claude-Code "地道" 协议转换器
# 核心技巧：通过模拟 CLI 交互，白嫖 Anthropic 给予命令行工具的无限/高配免费额度。

app = Flask(__name__)
input_queue = queue.Queue()
output_queue = queue.Queue()

def claude_engine():
    print("🚀 [TUNNEL] 正在建立 Claude-Code 地道连接...")
    # 启动官方 CLI 进程
    process = subprocess.Popen(
        ["npx", "-y", "@anthropic-ai/claude-code"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        shell=True
    )

    def read_output():
        while True:
            line = process.stdout.readline()
            if not line: break
            # 捕获 Claude 的回复标记 (根据 CLI 输出特征识别)
            if "Claude:" in line or ">" in line:
                output_queue.put(line)
            print(f"[CLI Output] {line.strip()}")

    threading.Thread(target=read_output, daemon=True).start()

    while True:
        try:
            msg = input_queue.get(timeout=1)
            print(f"[TUNNEL] Injecting Command: {msg[:20]}...")
            process.stdin.write(msg + "\n")
            process.stdin.flush()
        except queue.Empty:
            continue

@app.route('/ask', methods=['POST'])
def ask():
    prompt = request.json.get("prompt")
    input_queue.put(prompt)
    
    # 简易等待逻辑 (实际应使用更复杂的流式解析)
    time.sleep(5) 
    response = ""
    while not output_queue.empty():
        response += output_queue.get()
    
    return jsonify({"answer": response or "Tunnel established. Processing command..."})

if __name__ == "__main__":
    # 在独立线程启动引擎
    threading.Thread(target=claude_engine, daemon=True).start()
    app.run(host='127.0.0.1', port=8090)
