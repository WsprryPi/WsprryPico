#!/usr/bin/env python3
"""Injected finite B station-loss/fallback/recovery proof; no jobs or RF.

Adapters are root-owned and hardware opt-in. observe_ap returns a fresh record:
interface=observer_interface, scan_fresh=True, scan_ssids=list, associated_ssid=str|None,
link_observed=True, http_raw=bytes (complete interface-bound GET identity reply
when associated), http_device_id=exact B, socket_outcome='reply'|'refused'|
'network_unreachable'|'association_lost'. Timeout alone is inconclusive.
Host preflight is supplied as context['interfaces'] with exact interface/state/
connection records; wlan0 disconnected, wlan2 exact own fixture, management
eth0/wlan1 retained. No cached scan or INFO LED establishes AP withdrawal.
"""
import hashlib
import time
from phase12_composition_audit import counter
from phase12_recovery_device import DEVICE,strict,resource_health
from inhibited_network_acceptance import check_status


def require(ok,message):
    if not ok:raise ValueError(message)


def run(context,fixture,observe_info,observe_wtp,associate_ap,observe_ap,evidence,
        *,clock=time.monotonic,sleeper=time.sleep):
    start=clock();down_attempted=False;joined=False;primary=None
    from phase12_fixture_roles import role_map
    roles=context.get('radio_roles',role_map())
    require(roles==role_map(roles.get('selection')) and roles['selection'] in ('engineering','swapped'),'exact independent role mapping')
    observer_interface=roles['observer'];host_ap=roles['host_ap']
    interfaces=context['interfaces']
    require(interfaces[observer_interface]['state']=='disconnected' and interfaces[observer_interface]['connection'] is None,
            observer_interface+' must be unused')
    require(interfaces[host_ap]['connection']==context['fixture_connection'] and
            interfaces['eth0']['state']=='connected' and interfaces['wlan1']['state']=='connected',
            'owned AP and management interface identity')
    require(context['ssid']=='WsprryPico-0a9d89' and 8<=len(context['password'])<=63,'exact password-protected B AP')
    require(context['no_join_cookie_token_reply'] is True,'caller must prove no retention actions or pending replies')
    def budget():require(clock()-start<900,'network case fifteen-minute ceiling')
    def info():
        budget();value,raw=observe_info();require(isinstance(raw,bytes) and strict(raw)==value,'actual INFO bytes')
        resource_health(value);s=value['status']
        require(value['device_id']==DEVICE and value['revision']==context['source_commit'][:12] and
                s['boot_id']==context['boot_id'] and s['engine']=='inhibited-standalone-simulator' and
                s['enabled'] is False and s['output_active'] is False and s['storage_healthy'] is True and
                value['provisioning_source']=='provisioned' and value['access_state']=='healthy' and
                counter(value['provisioning_generation'],'profile generation')==context['profile_generation'],
                'exact healthy inactive engineering B')
        require(value['softap_retained_sessions']==0,'no retained application sessions')
        require(value['lan_wtp_mode']=='engineering-tls' and
                counter(value['softap_session_inactivity_ms'],'inactivity')==900000 and
                counter(value['softap_session_absolute_ms'],'absolute')==43200000,'ordinary engineering sessions')
        evidence.record('network_info',raw_hex=raw.hex(),sha256=hashlib.sha256(raw).hexdigest())
        authority,wire=observe_wtp();require(isinstance(wire,bytes) and wire,'actual readonly WTP wire')
        check_status(authority,context['boot_id'],unowned=True)
        evidence.record('network_authority',wire_hex=wire.hex(),value=authority)
        budget();return value
    def ap():
        budget();value=observe_ap()
        require(value['interface']==observer_interface and value['scan_fresh'] is True and value['link_observed'] is True,
                'independent fresh '+observer_interface+' observation')
        require(type(value['scan_ssids']) is list,'scan record')
        evidence.record('independent_ap',**{k:(v.hex() if isinstance(v,bytes) else v) for k,v in value.items()})
        return value
    try:
        baseline=info();require(baseline['network']['link_status']==3,'station baseline required')
        down_attempted=True;fixture('station_down')
        # Start the production 60s fallback window at observed station loss,
        # not at the host command, which may precede firmware link detection.
        loss_deadline=clock()+30
        while True:
            value=info()
            if value['network']['link_status']!=3:break
            require(clock()<loss_deadline,'station loss not observed');sleeper(1)
        lost=clock();sleeper(62);info()
        require(62<=clock()-lost<=90,'fallback association window')
        joined=True;associate_ap(dict(interface=observer_interface,ssid=context['ssid'],password=context['password'],
                                    address='192.168.4.3/24',never_default=True,deadline=min(start+900,lost+90)))
        observed=ap()
        require(context['ssid'] in observed['scan_ssids'] and observed['associated_ssid']==context['ssid'] and
                observed['socket_outcome']=='reply' and isinstance(observed['http_raw'],bytes) and
                observed['http_raw'] and observed['http_device_id']==DEVICE,'actual B fallback association/HTTP')
        fallback_bssid=observed.get('associated_bssid')
        require(60<=clock()-lost<=90,'fallback proof window')
        fixture('station_up');up_deadline=clock()+180
        stable=None
        while True:
            value=info()
            ready=value['network']['link_status']==3 and value['status']['clock_state']=='synchronized'
            if ready:
                if stable is None:stable=clock()
                if clock()-stable>=30:break
            else:stable=None
            require(clock()<up_deadline,'station/SNTP recovery stability');sleeper(1)
        withdrawal_deadline=clock()+30
        while True:
            value=info();observed=ap()
            absent=(fallback_bssid not in observed.get('scan_bssids',[]) if fallback_bssid else context['ssid'] not in observed['scan_ssids'])
            lost_association=observed['associated_ssid']!=context['ssid']
            socket_gone=observed['socket_outcome'] in ('refused','network_unreachable','association_lost')
            if absent and lost_association and socket_gone:break
            require(clock()<withdrawal_deadline,'independent AP withdrawal not proven');sleeper(1)
        evidence.record('network_case_complete',station_loss_fallback=True,independent_withdrawal=True,rf_jobs=0)
        return dict(status='NETWORK_LOSS_REVIEW_REQUIRED',simulator_jobs=0,rf_jobs=0,physical_acceptance=False)
    except BaseException as error:
        primary=error
        raise
    finally:
        failures=[]
        for stage,operation in [('observer_disconnect',lambda:associate_ap(dict(interface=observer_interface,action='disconnect_owned')) if joined else None),
                                ('station_restore',lambda:fixture('station_up') if down_attempted else None)]:
            try:operation()
            except BaseException as error:
                failures.append(error)
                try:evidence.record('network_cleanup_failed',stage=stage,error_type=type(error).__name__)
                except BaseException as recording_error:
                    error.add_note('cleanup failure record failed: '+type(recording_error).__name__)
                if primary is not None:primary.add_note(stage+' failed: '+type(error).__name__)
        if failures and primary is None:raise failures[0]
