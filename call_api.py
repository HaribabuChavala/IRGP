import json, os, urllib.request, sys

token = os.environ.get('TOKEN')
if not token:
    print('Missing TOKEN env var', file=sys.stderr)
    sys.exit(2)

with open('report_request.json','r') as f:
    body = json.load(f)

req = urllib.request.Request('http://access-api:8000/api/v1/reports/generate',
                             data=json.dumps(body).encode('utf-8'),
                             headers={
                                 'Content-Type':'application/json',
                                 'Authorization': f'Bearer {token}'
                             },
                             method='POST')

with urllib.request.urlopen(req, timeout=60) as resp:
    print(resp.status)
    print(resp.read().decode())
