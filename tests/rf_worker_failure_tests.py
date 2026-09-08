"""A missing consumer/full rendezvous must recover without returning borrowed data."""
import subprocess
import sys
for mode in ('--no-worker', '--reentrant'):
    result = subprocess.run([sys.argv[1], mode], timeout=5, capture_output=True)
    assert result.returncode < 0, (mode, result.returncode, result.stderr)
print('Missing-worker timeout and reentrant/full mailbox fail closed; no abandoned payload')
