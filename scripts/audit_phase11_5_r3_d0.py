"""Independent raw D0 success audit; diagnostic credit only, never R3 closure."""
import json
from pathlib import Path
from phase11_5_device_management import digest
from phase11_5_inventory import require
from phase11_5_pilot import Decoder, SERIAL, DEVICE
from phase11_5_pilot_supervisor import B_SERIAL, B_DEVICE, configuration
from phase11_5_r3_preflight import audit_inventory, decode_frame
from phase11_5_r3_capacity_plan import wtp_capacity_frame
from audit_phase11_5_r3_capacity_probe import rows

PACKET = '349634192b03f8a79bc8ef72c43eb30b6da201b35a79d3cc35067380de70c25c'


def audit(root):
    require(digest(root / 'packet.json') == PACKET, 'D0 frozen packet')
    packet = json.loads((root / 'packet.json').read_text())
    values = {}
    for name in ('before-b', 'before-a', 'after-flash-a', 'final-a', 'final-b'):
        b = name.endswith('-b')
        value = audit_inventory(root / (name + '.stdout'),
            dict(serial=B_SERIAL if b else SERIAL, device_id=B_DEVICE if b else DEVICE),
            packet['b_session'] if b else packet['a_session'],
            packet['stage_sha256']['scripts/phase11_5_inventory.py'])
        require(not (root / (name + '.stderr')).read_bytes(), 'D0 inventory stderr')
        info, status = value['info'], value['wtp']['STATUS']
        require(status['state'] == info['status']['state'] == 'empty' and
                status['output_active'] is info['status']['output_active'] is False and
                status['owner_id'] is status['job_id'] is None and
                info['status']['enabled'] is False and info['status']['storage_healthy'] is True and
                info['status']['last_error'] is None, 'D0 authoritative inactive state')
        values[name] = value
    before, deployed, final = (values[n] for n in ('before-a', 'after-flash-a', 'final-a'))
    require(before['wtp']['STATUS']['boot_id'] == packet['prior_boot'] and
            before['info']['revision'] == '2e43110f0530' and before['info']['recovery_boot'] is True and
            before['info']['fault_hash'] == 3833354787 and before['info']['fault_stage'] == 5,
            'D0 prior recovery identity')
    boot = deployed['wtp']['STATUS']['boot_id']
    require(boot != packet['prior_boot'], 'D0 new boot missing')
    def saved(value):
        station, network = configuration(value)
        return station, {k: network[k] for k in ('configured_hostname', 'control_configured')}
    for value in (deployed, final):
        info = value['info']
        require(value['wtp']['STATUS']['boot_id'] == boot and
                info['revision'] == packet['embedded_revision'] and not info['recovery_boot'] and
                all(info[k] == 0 for k in ('fault_stage', 'fault_hash', 'fault_pc', 'fault_status')) and
                info['fault_allocation_recorded'] is False and
                info['fault_allocation_request_bytes'] == 0 and
                info['fault_allocation_returned_null'] is None and
                info['system_clock_hz'] == 138000000 and info['rf_render_in_ram'] is True and
                info['status']['engine'] == 'pio-dma-gp2' and saved(value) == saved(before),
                'D0 deployed source/boot/configuration/fault')
        require(info['allocator_failures'] == '0' and
                info['heap_capacity_bytes'] - info['allocator_peak_bytes'] >= 32768,
                'D0 reserve or allocation failure')
        for core in (0, 1):
            require(info[f'core{core}_stack_guard_valid'] == 1 and
                    info[f'core{core}_stack_fault_status'] == 0 and
                    info[f'core{core}_stack_guard_limit'] - info[f'core{core}_stack_guard_bottom'] == 4096,
                    'D0 stack guard')
        require(all(int(info[k]) == 0 for k in ('launch_epoch','dma_irqs','alarm_irqs','tail_irqs')),
                'D0 unexpected RF activity')
    require(deployed['wtp']['CAPS'] == final['wtp']['CAPS'] and
            final['wtp']['CAPS']['max_payload_bytes'] == 65536 and
            final['info']['allocator_largest_successful_request_bytes'] == 65552,
            'D0 maximum allocation/CAPS')
    b0, b1 = values['before-b'], values['final-b']
    require(configuration(b0) == configuration(b1) and b0['wtp']['STATUS'] == b1['wtp']['STATUS'] and
            b0['wtp']['CAPS'] == b1['wtp']['CAPS'] and
            b0['wtp']['STATUS']['boot_id'] == 'feffcd075ab6cb0b74e7e0c2fde6c87f' and
            b0['info']['revision'] == b1['info']['revision'] == 'dbf1d86f0885-dirty', 'D0 B changed')
    trace = rows(root / 'diagnostic.jsonl')
    require(trace[0]['kind'] == 'start' and trace[0]['value'] == {'packet_sha256': PACKET} and
            trace[-1]['kind'] == 'finish' and
            trace[-1]['monotonic_ns'] - trace[0]['monotonic_ns'] <= 600_000_000_000,
            'D0 trace boundary/deadline')
    kinds = [r['kind'] for r in trace]
    prefix = ['start','bootsel_pending','tx','rx','bootsel_acknowledged']
    require(kinds[:5] == prefix and bytes.fromhex(trace[2]['value']['hex']) == b'BOOTSEL\n' and
            json.loads(bytes.fromhex(trace[3]['value']['hex'])) == {'ok':True,'rebooting':True} and
            trace[4]['value'] == {'ok':True,'rebooting':True}, 'D0 BOOTSEL acknowledged wire')
    p = 5
    if kinds[p] == 'bootsel_disconnect_cleanup':
        require(trace[p]['value']['errno'] in (5,19), 'D0 cleanup errno')
        p += 1
    require(kinds[p:p+3] == ['flash_pending','flash_exit','wtp_tx'] and
            trace[p]['value']['sha256'] == packet['image_sha256'] and trace[p+1]['value'] == {'exit':0},
            'D0 flash transition')
    require(trace[p]['value']['argv'] == ['/home/pi/phase11-4-e1/picotool-build/picotool', 'load','-v','-x',
            packet['root'] + '/diagnostic.uf2','--ser',SERIAL], 'D0 flash target/flags')
    flash = (root / 'flash.stdout').read_text()
    require('Verifying Flash:' in flash and '100%\n  OK' in flash and
            'The device was rebooted to start the application.' in flash and not (root / 'flash.stderr').read_bytes(),
            'D0 verified flash output')
    p += 2
    for operation, prefix in (('HELLO','wtp'),('STATUS','capacity')):
        start = trace[p]; p += 1
        require(start['kind'] == prefix + '_tx', 'D0 request ordering')
        wire = bytes.fromhex(start['value']['hex']); request = decode_frame(wire)
        require(request == start['value']['request'] and request['op'] == operation and
                request['session_id'] == packet['peer_session'], 'D0 request binding')
        if operation == 'STATUS':
            require(wire == wtp_capacity_frame(packet['peer_session'], packet['request_id']), 'D0 maximum bytes')
            written = 0
            while trace[p]['kind'] == 'capacity_write':
                v = trace[p]['value']; p += 1
                require(type(v['bytes']) is int and 0 < v['bytes'] <= 4096 and
                        v['total_written'] == written + v['bytes'], 'D0 write accounting')
                written += v['bytes']
            require(written == len(wire) == 65552, 'D0 incomplete maximum transfer')
        decoder = Decoder(); responses = []
        while trace[p]['kind'] == prefix + '_rx':
            responses.extend(decoder.feed(bytes.fromhex(trace[p]['value']['hex']))); p += 1
        require(not decoder.buffer and len(responses) == 1 and trace[p]['kind'] == prefix + '_message' and
                trace[p]['value'] == responses[0], 'D0 response raw wire')
        response = responses[0]
        require(all(response[k] == request[k] for k in ('op','session_id','request_id')) and
                response['ok'] is True and response['body']['boot_id'] == boot and
                trace[p]['monotonic_ns'] - start['monotonic_ns'] <= 5_000_000_000, 'D0 response identity/deadline')
        if operation == 'STATUS':
            require(response['body'] == final['wtp']['STATUS'], 'D0 maximum response authority')
        else:
            require(response['body']['device_id'] == DEVICE, 'D0 HELLO target')
        p += 1
    require(kinds[p:] == ['maximum_response','finish'] and trace[p]['value'] == final['wtp']['STATUS'],
            'D0 unexpected/missing work')
    result = json.loads((root / 'diagnostic-result.json').read_text())
    require(result == trace[-1]['value'] and result['status'] == 'MAXIMUM_RESPONDED_REQUIRES_AUDIT' and
            all(result[k] == 1 for k in ('flashes_started','bootsel_commands','maximum_requests_started')) and
            all(result[k] == 0 for k in ('rf_jobs','configuration_writes','wifi_cycles','heap_probes')),
            'D0 result/counters differ')
    return dict(status='D0_FRESH_BOOT_MAXIMUM_RESPONSE_VERIFIED', family_closed=False,
                packet_sha256=PACKET, source_revision=packet['source_revision'], boot_id=boot,
                complete_request_bytes=65552, rf_jobs=0, flashes=1, b_unchanged=True,
                historical_c0_cause_proven=False, firmware_remediation_verified=False)
