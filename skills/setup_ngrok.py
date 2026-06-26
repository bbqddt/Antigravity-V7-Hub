import sys
import os
import subprocess
import time

# [Antigravity V100.0] Ngrok Linker - No Bloat, No Emoji
TOKEN_FILE = r"E:\享中\ngrok_token.txt"

def run_ngrok_auth():
    print("--- [Linker] Starting Ngrok Config ---")
    
    if os.path.exists(TOKEN_FILE):
        with open(TOKEN_FILE, "r") as f:
            token = f.read().strip()
    else:
        print("[ALERT] No token found in E:\\享中\\ngrok_token.txt")
        return

    try:
        # Config token
        subprocess.run(["ngrok", "config", "add-authtoken", token], check=True)
        print("[SUCCESS] AuthToken Injected.")
        
        # Start Tunnel (Async)
        print("[LINK] Establishing Global Tunnel on Port 8501...")
        subprocess.Popen(["ngrok", "http", "8501"], shell=True)
        
        # Wait a bit for link generation
        time.sleep(3)
        print("[Antigravity] Tunnel should be active. Access your app via your ngrok dashboard URL.")
        
    except Exception as e:
        print(f"[ERROR] Failed to establish tunnel: {e}")

if __name__ == "__main__":
    run_ngrok_auth()
