import asyncio
from original_app import buscar_fantasia, buscar_en_todas_async
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)

print("--- 1. Testing Wrapper Directly ---")
result = buscar_fantasia()
print("Wrapper Logs:")
for l in result['log']:
    print(l)
print(f"Items found: {len(result['items'])}")

print("\n--- 2. Testing Async Orchestrator ---")
try:
    items, logs = asyncio.run(buscar_en_todas_async())
    print("Orchestrator Logs:")
    for l in logs:
        print(l)
    
    fantasia_items = [i for i in items if i['Tienda'] == "Fantasia Personajes"]
    print(f"\nTotal items: {len(items)}")
    print(f"Fantasia items: {len(fantasia_items)}")
except Exception as e:
    print(f"Orchestrator Error: {e}")
