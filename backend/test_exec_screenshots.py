import urllib.request
import urllib.parse
import json
import time

# 1. Load protocol
data = urllib.parse.urlencode({'filename': 'CLIN-EU-PAT-OPV-1-1-PQ-022- Manual - Registering Adverse Event Case.docx'}).encode()
req = urllib.request.Request('http://localhost:8000/api/load-sample-protocol', data=data)
session = json.loads(urllib.request.urlopen(req).read().decode())
session_id = session['session_id']
print('Session loaded:', session_id)

# 2. Start Execution
exec_data = json.dumps({
    'sim_mode': 'PASS',
    'username': 'sirihari.banda',
    'password': 'Clinevo@2026',
    'enterprise': 'Clinevo',
    'requires_approval': False,
    'headless': True
}).encode()
req2 = urllib.request.Request(f'http://localhost:8000/api/execute/{session_id}', data=exec_data, headers={'Content-Type': 'application/json'})
urllib.request.urlopen(req2)
print('Execution started, monitoring progress...')

for _ in range(12):
    time.sleep(2)
    res = urllib.request.urlopen(f'http://localhost:8000/api/session/{session_id}')
    session_after = json.loads(res.read().decode())
    passed = [s['step_id'] for s in session_after['steps'] if s['status'] == 'PASS']
    print(f"Passed steps ({len(passed)}): {passed}")
    if len(passed) >= 6:
        break

# Inspect screenshots on disk
import os
from pathlib import Path
sc_dir = Path("artifacts/screenshots") / session_id
if sc_dir.exists():
    for f in sorted(sc_dir.glob("*.png")):
        print(f"Screenshot: {f.name} size: {f.stat().st_size} bytes")
