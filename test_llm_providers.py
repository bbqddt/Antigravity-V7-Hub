import sys
sys.path.insert(0, r'E:\享中.worktrees\agents-invisible-pelican')
from unified_llm_client import UnifiedLLMClient

llm = UnifiedLLMClient()
results = llm.test_all()
print('LLM 测试结果:')
for name, ok in results.items():
    status = "OK" if ok else "FAIL"
    print('  {}: {}'.format(name, status))