from unified_llm_client import UnifiedLLMClient
client = UnifiedLLMClient()
results = client.test_all()
print('=== Test Results ===')
for name, ok in results.items():
    status = "OK" if ok else "FAIL"
    print(f'{name}: {status}')