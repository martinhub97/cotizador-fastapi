import requests
import json

response = requests.get(
    'https://argenstats.com//api/v1/inflation?view=historical&from=2025-12-01&to=2026-02-30',
    headers={'x-api-key': 'as_prod_rYU1SREpFj6BVh6r166RvWdo9ZfxROBU'}
)

data = response.json()
print(json.dumps(data, indent=2))