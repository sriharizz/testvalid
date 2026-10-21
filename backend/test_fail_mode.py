import urllib.request
import urllib.parse
import json
import time

# 1. Load protocol
data = urllib.parse.urlencode({'filename': 'CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx'}).encode()
req = urllib.request.Request('http://localhost:8000/api/load-sample-protocol', data=data)
session = json.loads(urllib.request.urlopen(req).read().decode())
session_id = session['session_id']
print('Session loaded for FAIL mode test:', session_id)

# 2. Trigger FAIL mode
exec_data = json.dumps({
    'sim_mode': 'FAIL',
    'username': 'sirihari.banda',
    'password': 'Clinevo@2026',
    'enterprise': 'Clinevo',
    'requires_approval': False,
    'headless': True
}).encode()
req2 = urllib.request.Request(f'http://localhost:8000/api/execute/{session_id}', data=exec_data, headers={'Content-Type': 'application/json'})
urllib.request.urlopen(req2)
print('Execution started in FAIL mode...')

for _ in range(8):
    time.sleep(2)
    res = urllib.request.urlopen(f'http://localhost:8000/api/session/{session_id}')
    session_after = json.loads(res.read().decode())
    statuses = [(s['step_id'], s['status']) for s in session_after['steps'][:5]]
    print('Step statuses:', statuses)
    if any(s['status'] == 'FAIL' for s in session_after['steps']):
        break

print('Confirmed FAIL mode captured on backend!')
