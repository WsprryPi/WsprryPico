"""Actual native parser refuses bad commands without clock or ACK-state mutation."""
import os
import subprocess
import sys
from fixture_process import FixtureProcess, process_scope
from network_control import NetworkControl

with process_scope(timeout=20):
    process = FixtureProcess([sys.argv[1]], stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE, text=True,
                             env={**os.environ, 'WSPRRY_NETWORK_TEST_MANUAL_CLOCK':'1'})
    controls = NetworkControl(process)
    assert controls.line().strip() == 'READY 18443 PSA 1 PEAK 2'
    for command, expected in [('SYNC 0','CONTROL ERROR SYNC'),
                              ('SYNC 01','CONTROL ERROR SYNC'),
                              ('TIME ADVANCE 01','CONTROL ERROR TIME'),
                              ('X'*512,'CONTROL ERROR OVERSIZED'),
                              ('SYNC 18446744073709551616','CONTROL ERROR SYNC'),
                              ('TIME ADVANCE -1','CONTROL ERROR TIME'),
                              ('TIME ADVANCE 18446744073709551615','CONTROL ERROR TIME'),
                              ('UNKNOWN','CONTROL ERROR UNKNOWN')]:
        process.send_line(command)
        assert process.line().strip() == expected
    controls.send('STATE')
    snapshot = controls.line().strip().split()
    assert snapshot[0] == 'STATE' and snapshot[9] == '1000000', snapshot
    controls.send('TIME ADVANCE 1')
    assert controls.line().strip() == 'TIME 1000001'
    controls.send('STATE')
    snapshot = controls.line().strip().split()
    assert snapshot[9] == '1000001', snapshot
    process.send_line('SYNC '+str(controls.sequence+2))
    assert process.line().strip() == 'CONTROL ERROR SYNC'
    controls.send('BARRIER')  # Invalid sequence did not advance the native counter.
    print('Actual native controls: malformed/stale/overflow/unknown refusal and exact monotonic advancement passed')
