"""Pure validation and bounded process cleanup for the opt-in B2/D2 harness."""
import signal
import json
import subprocess
import time

DEVICE = 'fd6127d11d6aca42a9905fa3fb1bf1d5'
REVISION = 'e4ff40a56180-dirty'
NAME = 'wsprrypico-0a60df.local'
ADDRESS = '192.168.1.47'
SERVER_SHA = '06496fe4d7a1ab45791d85cb0797fa55f76b8dc7ee931f9c7fa70823fef46016'


def require(condition, message):
    if not condition:
        raise ValueError(message)


def validate_info(info, boot, revision=REVISION):
    require(info.get('device_id') == DEVICE, 'wrong USB device')
    require(info.get('revision') == revision, 'wrong firmware revision')
    require(info.get('deployment_identity_matches') is True, 'deployment mismatch')
    require(info.get('recovery_boot') is False, 'watchdog/recovery boot observed')
    status = info['status']
    require(status['boot_id'] == boot, 'boot changed')
    require(status['engine'] == 'inhibited-standalone-simulator', 'wrong engine')
    require(status['output_active'] is False and status['enabled'] is False,
            'output or scheduling not inhibited')
    require(status['storage_healthy'] is True, 'unhealthy storage')


def validate_https(value, boot):
    require(value['http'] == 200 and value['server_sha256'] == SERVER_SHA,
            'HTTP status or server fingerprint mismatch')
    body = value['body']
    job = body['job']
    require(job['boot_id'] == boot and job['state'] == 'empty' and
            job['output_active'] is False and job['owner_id'] is None and
            job['job_id'] is None, 'HTTPS identity/output/owner mismatch')
    status = body['standalone']
    require(status['boot_id'] == boot and
            status['engine'] == 'inhibited-standalone-simulator' and
            status['enabled'] is False and status['output_active'] is False and
            status['storage_healthy'] is True, 'HTTPS standalone mismatch')
    network = body['network']
    require(network['deployment_identity_matches'] is True and
            network['configured_hostname'] == NAME and network['ipv4'] == ADDRESS,
            'HTTPS deployment/address mismatch')


def stop_process(process, grace=3):
    """Try graceful capture statistics, then TERM and KILL; never unbounded wait."""
    started = time.monotonic()
    signals = []
    for sig in (signal.SIGINT, signal.SIGTERM, signal.SIGKILL):
        if process.poll() is not None:
            break
        try:
            process.send_signal(sig)
        except ProcessLookupError:
            process.wait(timeout=grace)
            break
        signals.append(sig.name)
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            continue
    require(process.poll() is not None, 'child did not exit after bounded KILL')
    return {'exit': process.returncode, 'signals': signals,
            'seconds': time.monotonic() - started}


def campaign_decision(attempts, clean_required=8, unresolved_limit=3):
    """Never turn a failed/invalid attempt into a clean campaign through retry."""
    if any(a.get('observer_failure') for a in attempts):
        return 'HARNESS_INEFFECTIVE'
    if any(a.get('failure_point') for a in attempts):
        return 'FAILURE_POINT_DETECTED'
    failures = [a for a in attempts if a['result'] != 'PASS']
    if len(failures) >= unresolved_limit:
        return 'HARNESS_INEFFECTIVE'
    if not failures and len(attempts) >= clean_required:
        return 'NOT_REPRODUCED_IN_BOUNDED_CAMPAIGN'
    return 'CONTINUE'


def validate_host(value):
    addresses = json.loads(value['address'])
    require(value['mac'] == '90:de:80:47:b9:da', 'wrong USB dongle')
    require(len(addresses) == 1 and addresses[0]['ifname'] == 'wlan1' and
            any(i.get('family') == 'inet' and i.get('local') == '192.168.1.117'
                for i in addresses[0]['addr_info']), 'host address/interface changed')
    require(value['profile'] == '921301fe-cdfd-4965-8ac7-c96e9d908ea6', 'host profile changed')
    require('\n\tSSID: Bohica\n' in '\n' + value['link'] + '\n', 'host SSID changed')
    require(value['recovery_active'] == 'active' and value['recovery_enabled'] == 'enabled',
            'host recovery changed')
    return (value['link'].splitlines()[0], value['profile'])
