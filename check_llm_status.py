import sys
sys.path.insert(0, r'E:\享中.worktrees\agents-invisible-pelican')
from unified_llm_client import UnifiedLLMClient

llm = UnifiedLLMClient()
status = llm.get_status()
print('Status check (before test):')
for k, v in status.items():
    print('  {}: {}'.format(k, v['status']))

print()
print('Running test_all...')
results = llm.test_all()
print('Test results:')
for k, v in results.items():
    print('  {}: {}'.format(k, 'OK' if v else 'FAIL'))

status = llm.get_status()
print()
print('Status check (after test):')
for k, v in status.items():
    print('  {}: {}'.format(k, v['status']))