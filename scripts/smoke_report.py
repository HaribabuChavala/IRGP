import json, urllib.request, sys
payload={
    "prompt": "count rows in customers",
    "dataSourceId": "10000000-0000-0000-0000-000000000001",
    "executionEngine": "spark"
}
req = urllib.request.Request('http://127.0.0.1:8000/api/v1/reports/generate', data=json.dumps(payload).encode(), headers={'Content-Type': 'application/json'})
with urllib.request.urlopen(req, timeout=120) as r:
    print('STATUS', r.status)
    print(r.read().decode())
