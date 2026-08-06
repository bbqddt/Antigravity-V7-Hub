import os
import sys
import time
import logging
import subprocess
import json
from pathlib import Path
from huggingface_hub import HfApi

# 确保核心路径已挂载

# 配置日志系统 (Hermes Pulse)
logging.basicConfig(
    level=logging.INFO,
    format='[HERMES-%(asctime)s] %(levelname)s: %(message)s',
    datefmt='%H:%M:%S'
)
logger = logging.getLogger("HermesAgent")

class HermesAgent:
    """
    Antigravity V20.0: 赫耳墨斯通讯与调度代理
    职能：数据镜像、指令下发、置信度监测、自主演进触发
    """
    
    def __init__(self):
        self.repo_id = "bbqddt2/Antigravity-Hive"
        self.local_root = Path(__file__).resolve().parent.parent
        self.state_file = self.local_root / "core/hermes_state.json"
        
        # 尝试获取 Token
        self.token = os.environ.get("HF_TOKEN")
        self.api = HfApi(token=self.token) if self.token else None
        
        # 初始状态负载
        self.state = {
            "last_heartbeat": "NEVER",
            "last_sync_status": "WAITING",
            "sync_success_count": 0,
            "intelligence_pulse": 0.0,
            "evolution_triggered": False,
            "message": "System check complete. Standing by."
        }
        
        # 核心文件同步清单
        self.sync_manifest = [
            "latest_predictions.csv",
            "latest_inference.json",
            "data/lottery_history.csv",
            str(self.local_root / "models" / "ssq_model_v985.pt"),
            "v19_time_nexus.py",
            "v18_omni_nexus.py"
        ]

    def _heartbeat_sync(self):
        """记录赫耳墨斯的心跳到状态文件，供 UI 捕捉"""
        self.state["last_heartbeat"] = time.strftime("%Y-%m-%d %H:%M:%S")
        try:
            with open(self.state_file, 'w', encoding='utf-8') as f:
                json.dump(self.state, f, indent=4)
        except Exception as e:
            logger.error(f"Heartbeat failure: {e}")

    def shuttle_sync(self):
        """[Messenger] 执行本地与云端的刚性镜像合龙"""
        logger.info("[Messenger] Starting ShuttleSync...")
        self.state["last_sync_status"] = "SYNCING..."
        self._heartbeat_sync()
        
        if not self.api:
            logger.error("Missing HF_TOKEN. Cloud sync skipped.")
            self.state["last_sync_status"] = "OFFLINE (No Token)"
            self._heartbeat_sync()
            return False
            
        success_count = 0
        for file_rel in self.sync_manifest:
            local_fp = self.local_root / file_rel.replace("/", "\\")
            if local_fp.exists():
                try:
                    self.api.upload_file(
                        path_or_fileobj=str(local_fp),
                        path_in_repo=file_rel,
                        repo_id=self.repo_id,
                        repo_type="space"
                    )
                    success_count += 1
                except Exception as e:
                    logger.warning(f"Sync interrupted for {file_rel}: {e}")
        
        self.state["sync_success_count"] = success_count
        self.state["last_sync_status"] = f"SUCCESS ({success_count}/{len(self.sync_manifest)})"
        self._heartbeat_sync()
        return True

    def intelligence_pulse(self, confidence_threshold=0.92):
        """[Informer] 侦听计算层的置信度脉冲"""
        inf_file = self.local_root / "latest_inference.json"
        if not inf_file.exists():
            return False
            
        try:
            with open(inf_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            top_cf = data.get("top_3_predictions", [{}])[0].get("confidence_score", 0)
            self.state["intelligence_pulse"] = top_cf
            logger.info(f"Intelligence Pulse detected: {top_cf:.4f}")
            
            if top_cf >= confidence_threshold:
                self.state["message"] = f"BREAKTHROUGH: Confidence {top_cf:.4f} detected!"
                self._heartbeat_sync()
                return True
        except Exception as e:
            logger.error(f"Pulse detection failed: {e}")
        return False

    def trigger_autonomous_evolution(self):
        """[Evolver] 唤醒 Gemini 2.5 进化器执行代码级自修复"""
        logger.info("Triggering LLM_EVOLVER for logic mutation...")
        self.state["evolution_triggered"] = True
        self._heartbeat_sync()
        
        try:
            evolver_path = self.local_root / "core/llm_evolver.py"
            if evolver_path.exists():
                subprocess.run(["python", str(evolver_path)], check=True)
                self.state["message"] = "Self-Evolution Complete. Logic mutated."
                self._heartbeat_sync()
                return True
        except Exception as e:
            logger.error(f"Autonomous evolution failed: {e}")
        return False

if __name__ == "__main__":
    hermes = HermesAgent()
    hermes.intelligence_pulse()
    hermes.shuttle_sync()
