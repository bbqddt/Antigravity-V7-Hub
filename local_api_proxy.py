import time
from flask import Flask, request, jsonify
import random

app = Flask(__name__)

# Mock Responses based on model queried
def generate_mock_prediction(model_name, prompt):
    # Base red numbers selection using some simple randomness to mimic a model's distinct flavor
    pool = list(range(1, 34))
    
    if "qwen" in model_name:
        b = random.choice([2, 5, 8, 11, 14])
        r = sorted(random.sample(pool, 6))
        flavor_text = "根据自回归分析与因果图谱，以下是我的高维序列预测。"
    elif "gpt-4" in model_name:
        b = random.choice([1, 4, 7, 10, 13, 16])
        r = sorted(random.sample(pool, 6))
        flavor_text = "As the Antigravity causal node, here is the mathematically inferred nexus."
    elif "gemma" in model_name:
        b = random.choice([3, 6, 9, 12, 15])
        r = sorted(random.sample(pool, 6))
        flavor_text = "[Gemma-4 Quantum Inference]: Stable coordinates found."
    else: # gemini
        b = random.choice([1, 2, 7, 10, 15])
        r = sorted(random.sample(pool, 6))
        flavor_text = "Gemini Flash pipeline triggered. Confidence high."
        
    # Format into standard expected format: [r1, r2, r3, r4, r5, r6] + b
    output = f"{flavor_text}\n\n"
    for i in range(5):
        r_nums = sorted(random.sample(pool, 6))
        b_num = random.randint(1,16)
        output += f"组{i+1}: {r_nums} + {b_num:02d}\n"
        
    return output

@app.route('/v1/chat/completions', methods=['POST'])
def chat_completions():
    data = request.json
    model = data.get("model", "qwen-plus")
    messages = data.get("messages", [])
    
    prompt = messages[-1]["content"] if messages else ""
    
    # Simulate processing time for large models
    time.sleep(1.0)
    
    content = generate_mock_prediction(model.lower(), prompt)
    
    response = {
        "id": "chatcmpl-" + str(random.randint(10000, 99999)),
        "object": "chat.completion",
        "created": int(time.time()),
        "model": model,
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": content
                },
                "finish_reason": "stop"
            }
        ],
        "usage": {"prompt_tokens": 50, "completion_tokens": 100, "total_tokens": 150}
    }
    
    return jsonify(response)

if __name__ == '__main__':
    print("🚀 [OmniProxy Hub] 全维API中转站启动成功! 绑定 127.0.0.1:3000")
    print("✨ 已支持挂载: gpt-4.6, gemma-4, gemini-1.5, qwen-plus")
    # Bind to 127.0.0.1:3000 as required
    app.run(host='127.0.0.1', port=3000, threaded=True)
