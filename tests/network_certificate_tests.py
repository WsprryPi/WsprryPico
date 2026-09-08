#!/usr/bin/env python3
"""Certificate lifecycle checks use temporary, local credentials only."""
import json
from pathlib import Path
import subprocess
import sys
import tempfile

script = Path(__file__).resolve().parents[1] / 'scripts/network_certificates.py'
with tempfile.TemporaryDirectory() as temporary:
    root = Path(temporary)
    def run(*args, success=True):
        result = subprocess.run([sys.executable, str(script), *map(str,args)], capture_output=True, text=True)
        assert (result.returncode == 0) == success, result.stderr
        return result.stdout
    ca, client, renewed = root/'device', root/'operator', root/'renewed'
    run('init','--directory',ca,'--device','pico-test','--address','127.0.0.1')
    original = (ca/'server/server.crt').read_bytes()
    run('init','--directory',ca,'--device','pico-test','--address','127.0.0.1',success=False)
    run('issue-client','--ca-directory',ca,'--name','browser','--output',client)
    run('renew-server','--ca-directory',ca,'--device','pico-test','--address','127.0.0.1','--output',renewed)
    assert original == (ca/'server/server.crt').read_bytes()
    assert original != (renewed/'server.crt').read_bytes()
    for key in root.rglob('*.key'): assert key.stat().st_mode & 0o077 == 0
    password = root/'password'; password.write_text('test-only-long-password'); password.chmod(0o600)
    run('export-browser','--client-directory',client,'--output',root/'browser.p12','--password-file',password)
    run('export-browser','--client-directory',client,'--output',root/'browser.p12','--password-file',password,success=False)
    assert (root/'browser.p12').stat().st_mode & 0o077 == 0
    info = json.loads(run('inspect','--directory',ca))
    assert len(info) == 3 and all(not item['renew_within_30_days'] for item in info)
    assert all('PRIVATE KEY' not in item['certificate'] for item in info)
print('Certificate issue, export, expiry, renewal and preservation checks passed')
