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
    p.add_argument('--correction-ppb', type=int, choices=range(-100000, 100001), metavar='-100000..100000')
    p.add_argument('--center-hz', type=int, default=3550000, choices=range(3490000, 3560001), metavar='3490000..3560000')
    p.add_argument('--gain-db', type=int, default=20, choices=range(20, 49))
    p.add_argument('--receive-only', action='store_true', help='Observe with Pico output inactive')
    p.add_argument('--abort-after-ms', type=int, choices=range(1, 10001), metavar='1..10000')
    p.add_argument('--gpsdo-reference', action='store_true',
                   help='Enable wspr5 LBE-1421 output 1 at 3580000 Hz, then disable it')
    p.add_argument('--frame', action='store_true', help='162-symbol local synthetic frame')
    p.add_argument('--tone', type=int, choices=range(4), default=0)
    p.add_argument('--duration-ms', type=int, choices=range(1, 10001), default=100, metavar='1..10000')
    args = p.parse_args()
    if args.receive_only and (args.frame or args.abort_after_ms is not None):
        p.error('Receive-only cannot be combined with frame or abort')
    if args.receiver_host.startswith('-') or args.sdr_serial.startswith('-'):
        p.error('Invalid host or serial')
    if not math.isfinite(args.attenuation_db) or args.attenuation_db < 0:
        p.error('Attenuation must be finite and nonnegative')
    if not args.firmware.is_file():
        p.error('Firmware file does not exist')
    args.output.mkdir(parents=True, exist_ok=False)
    run_id = 'pico-' + uuid.uuid4().hex
    directory = '/var/tmp/' + run_id
    duration = (110.592 if args.frame else args.duration_ms / 1000) + 6
    if args.abort_after_ms is not None:
        duration = args.abort_after_ms / 1000 + 7
    count = round(duration * 250000)
    manifest = dict(run_id=run_id, remote_directory=directory, receiver_host=args.receiver_host,
                    sdr_serial=args.sdr_serial, attenuation_db=args.attenuation_db,
                    capture_success=False, transmitter_success=False, qualification=False)
    capture = None
    reference_attempted = False
    manifest['reference_disable_verified_by_cli'] = False if args.gpsdo_reference else None
    gpsdo = ['sudo', '-n', '/home/pi/lbgpsdo/.venv/bin/python',
             '/home/pi/lbgpsdo/lbe142x.py']
    def reference_command(arguments, name):
        with (args.output / name).open('w') as log:
            remote(args.receiver_host, gpsdo + arguments, timeout=20,
                   stdout=log, stderr=subprocess.STDOUT)
    try:
        remote(args.receiver_host, ['mkdir', directory], timeout=10)
        remote(args.receiver_host, ['python3', '-c',
               'import shutil,sys; free=shutil.disk_usage(sys.argv[1]).free; '
               'required=int(sys.argv[2]); '
               'sys.exit(0 if free >= required else \"Insufficient capture disk space\")',
               directory, str(count * 8 + 32 * 1024 * 1024)], timeout=10)
        if args.gpsdo_reference:
            reference_command(['detail', '-s', '0673ED0FA107'], 'reference-before.log')
            reference_attempted = True
            reference_command(['modify', '-s', '0673ED0FA107', '--f1', '3580000',
                               '--level1-low', '--pps-disable', '--enable1'], 'reference-enable.log')
            reference_command(['detail', '-s', '0673ED0FA107'], 'reference-active.log')
            manifest['reference'] = dict(serial='0673ED0FA107', output=1, frequency_hz=3580000,
                                         level='low', correction='offline simultaneous comparison')
        helper = [args.capture_helper, '--enable-physical-sdr', 'sdrplay', args.sdr_serial,
                  str(args.center_hz), str(count), str(args.gain_db), '250000', '200000', '0', 'false', 'false',
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
                       *([] if args.correction_ppb is None else ['--correction-ppb', str(args.correction_ppb)]),
                       *([] if args.abort_after_ms is None else ['--abort-after-ms', str(args.abort_after_ms)]),
                       *(['status'] if args.receive_only else
                         (['frame'] if args.frame else ['run', '--tone', str(args.tone),
                          '--duration-ms', str(args.duration_ms)]) + ['--delay-ms', '1000'])]
            with (args.output / 'transmitter.log').open('w') as txlog:
                # The client always sends STOP on run failure or timeout.
                tx = subprocess.run(command, stdout=txlog, stderr=subprocess.STDOUT)
            manifest['transmitter_success'] = tx.returncode == 0
            manifest['receive_only'] = args.receive_only
            if args.receive_only:
                result = json.loads((args.output / 'transmitter/result.json').read_text())
                if result.get('terminal', {}).get('output_active') is not False:
                    raise RuntimeError('Receive-only observation has active or unknown Pico output')
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
                (args.output / 'capture.cf32').stat().st_size != count * 8 or
                meta['resolved_device'] != dict(driver='sdrplay', serial=args.sdr_serial) or
                meta['actual_settings'] != dict(format='CF32', sample_rate_hz=250000,
                    bandwidth_hz=200000, center_frequency_hz=args.center_hz, gain_db=args.gain_db,
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
            try:
                if reference_attempted:
                    # Always attempt disable even if the final status read fails.
                    try:
                        reference_command(['detail', '-s', '0673ED0FA107'], 'reference-capture-end.log')
                    finally:
                        reference_command(['modify', '-s', '0673ED0FA107', '--disable1'],
                                          'reference-disable.log')
                    reference_command(['detail', '-s', '0673ED0FA107'], 'reference-after.log')
                    manifest['reference_disable_verified_by_cli'] = True
            finally:
                (args.output / 'session.json').write_text(json.dumps(manifest, indent=2) + '\n')
    print(json.dumps(manifest, indent=2))
    return 0 if manifest['transmitter_success'] and manifest['capture_success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
