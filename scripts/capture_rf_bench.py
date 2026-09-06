#!/usr/bin/env python3
"""Receive one bounded Pico bench tone using the Harness helper on wspr5."""
import argparse
import hashlib
import json
import math
from pathlib import Path
import shlex
import subprocess
import sys
import uuid


def remote(host, args, **kwargs):
    return subprocess.run(['ssh', host, shlex.join(args)], check=True, **kwargs)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--port', required=True)
    p.add_argument('--serial', required=True)
    p.add_argument('--revision', required=True)
    p.add_argument('--firmware', type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p.add_argument('--receiver-host', default='wspr5')
    p.add_argument('--capture-helper', default='/tmp/wsprrypico-capture-build/wspq-capture-soapy')
    p.add_argument('--sdr-serial', default='2404058C60')
    p.add_argument('--attenuation-db', type=float, required=True)
    p.add_argument('--tone', type=int, choices=range(4), default=0)
    p.add_argument('--duration-ms', type=int, choices=range(1, 10001), default=100, metavar='1..10000')
    args = p.parse_args()
    if args.receiver_host.startswith('-') or args.sdr_serial.startswith('-'):
        p.error('Invalid host or serial')
    if not math.isfinite(args.attenuation_db) or args.attenuation_db < 0:
        p.error('Attenuation must be finite and nonnegative')
    if not args.firmware.is_file():
        p.error('Firmware file does not exist')
    args.output.mkdir(parents=True, exist_ok=False)
    run_id = 'pico-' + uuid.uuid4().hex
    directory = '/tmp/' + run_id
    duration = args.duration_ms / 1000 + 6
    count = round(duration * 250000)
    manifest = dict(run_id=run_id, remote_directory=directory, receiver_host=args.receiver_host,
                    sdr_serial=args.sdr_serial, attenuation_db=args.attenuation_db,
                    capture_success=False, transmitter_success=False, qualification=False)
    capture = None
    try:
        remote(args.receiver_host, ['mkdir', directory], timeout=10)
        helper = [args.capture_helper, '--enable-physical-sdr', 'sdrplay', args.sdr_serial,
                  '3550000', str(count), '20', '250000', '200000', '0', 'false', 'false',
                  '100000', str(duration + 10), directory + '/capture.cf32',
                  directory + '/capture.json', run_id]
        manifest['capture_argv'] = helper
        with (args.output / 'receiver.log').open('w') as log:
            capture = subprocess.Popen(['ssh', args.receiver_host, shlex.join(helper)],
                                       stdout=log, stderr=subprocess.STDOUT)
            ready = ("import os,time,sys\np=" + repr(directory + '/capture.cf32.incomplete') +
                     "\nend=time.monotonic()+8\nwhile time.monotonic()<end:\n"
                     " if os.path.exists(p) and os.path.getsize(p)>65536: sys.exit(0)\n"
                     " time.sleep(.05)\nsys.exit(1)")
            remote(args.receiver_host, ['python3', '-c', ready], timeout=12)
            if capture.poll() is not None:
                raise RuntimeError('Receiver ended before tone command')
            command = [sys.executable, str(Path(__file__).with_name('rf_bench.py')),
                       '--port', args.port, '--serial', args.serial, '--revision', args.revision,
                       '--firmware', str(args.firmware), '--output', str(args.output / 'transmitter'),
                       'run', '--tone', str(args.tone), '--duration-ms', str(args.duration_ms),
                       '--delay-ms', '1000']
            with (args.output / 'transmitter.log').open('w') as txlog:
                # The client always sends STOP on run failure or timeout.
                tx = subprocess.run(command, stdout=txlog, stderr=subprocess.STDOUT)
            manifest['transmitter_success'] = tx.returncode == 0
            manifest['capture_returncode'] = capture.wait(timeout=duration + 15)
            manifest['capture_success'] = capture.returncode == 0
        if not manifest['capture_success']:
            raise RuntimeError('Receiver capture failed; inspect retained receiver log and remote metadata')
        subprocess.run(['scp', args.receiver_host + ':' + directory + '/capture.cf32',
                        args.receiver_host + ':' + directory + '/capture.json', str(args.output)],
                       check=True, timeout=60)
        meta = json.loads((args.output / 'capture.json').read_text())
        with (args.output / 'capture.cf32').open('rb') as iq:
            digest = hashlib.file_digest(iq, 'sha256').hexdigest()
        if (meta['output']['sha256'] != digest or meta['cleanup']['outcome'] != 'verified' or
                meta['retained_sample_count'] != count):
            raise RuntimeError('Capture hash/count/cleanup verification failed')
        if (meta['primary_outcome'] != 'success' or not meta['output']['complete'] or
                meta['output']['size_bytes'] != count * 8 or
                meta['resolved_device'] != dict(driver='sdrplay', serial=args.sdr_serial) or
                meta['actual_settings'] != dict(format='CF32', sample_rate_hz=250000,
                    bandwidth_hz=200000, center_frequency_hz=3550000, gain_db=20,
                    channel=0, agc=False, bias_tee=False)):
            raise RuntimeError('Capture identity/settings verification failed')
        manifest['capture_sha256'] = digest
    except BaseException as error:
        manifest['error'] = str(error)
        manifest['capture_success'] = False
        raise
    finally:
        try:
            if capture is not None and capture.poll() is None:
                # The remote helper has its own finite deadline; let it clean up.
                try:
                    capture.wait(timeout=duration + 15)
                except subprocess.TimeoutExpired:
                    capture.terminate()
                    capture.wait(timeout=5)
                    manifest['receiver_cleanup_unconfirmed'] = True
        finally:
            (args.output / 'session.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))
    return 0 if manifest['transmitter_success'] and manifest['capture_success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
