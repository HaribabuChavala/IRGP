import json, os, time, urllib.request, sys

token = os.environ.get('TOKEN')
job_id = os.environ.get('JOB_ID')
if not token or not job_id:
    print('Missing TOKEN or JOB_ID', file=sys.stderr)
    sys.exit(2)

url = f'http://access-api:8000/api/v1/reports/jobs/{job_id}'
headers = {'Authorization': f'Bearer {token}'}

for i in range(60):
    req = urllib.request.Request(url, headers=headers, method='GET')
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            body = resp.read().decode()
            print(f'[{i}]', body)
            job = json.loads(body)
            status = job.get('status')
            if status in ('completed','failed'):
                print('Final status:', status)
                sys.exit(0 if status=='completed' else 1)
    except Exception as e:
        print('Request error', e)
    time.sleep(1)
print('Timed out waiting for job')
sys.exit(2)
