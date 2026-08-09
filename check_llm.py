from unified_llm_client import UnifiedLLMClient
client = UnifiedLLMClient()
status = client.get_status()
print('=== Provider Status ===')
for name, info in status.items():
    print(f'{name}: {info["status"]} (models: {len(info["models"])})')
print()
print('=== Free Models ===')
free = client.get_free_models()
for m in free:
    print(f'  {m.provider}: {m.id}')