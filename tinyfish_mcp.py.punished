import json
import sys
import os

# [Antigravity Omega] TinyFish MCP Bridge V1.0
# 为编辑器提供原生历史数据读取能力，消除模型盲区

def get_lottery_data():
    path = r"d:\Antigravity_V7\data\lottery_history.csv"
    try:
        if os.path.exists(path):
            with open(path, "r", encoding='utf-8') as f:
                lines = f.read().splitlines()
                # 返回最近50期数据作为强力推演素材
                return "\n".join(lines[-50:])
    except Exception as e:
        return f"Error reading data: {str(e)}"
    return "No history data found."

def main():
    # 极简 MCP 响应框架 (stdio 模式)
    while True:
        try:
            line = sys.stdin.readline()
            if not line: break
            request = json.loads(line)
            
            # 处理 MCP 列出工具请求
            if request.get("method") == "listTools":
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "tools": [{
                            "name": "get_lottery_history",
                            "description": "获取双色球最近50期的历史中奖数据，用于混沌推演。",
                            "inputSchema": {"type": "object", "properties": {}}
                        }]
                    }
                }
            
            # 处理工具调用
            elif request.get("method") == "callTool":
                data = get_lottery_data()
                response = {
                    "jsonrpc": "2.0",
                    "id": request.get("id"),
                    "result": {
                        "content": [{"type": "text", "text": data}]
                    }
                }
            else:
                response = {"jsonrpc": "2.0", "id": request.get("id"), "result": {}}

            sys.stdout.write(json.dumps(response) + "\n")
            sys.stdout.flush()
        except:
            break

if __name__ == "__main__":
    main()
