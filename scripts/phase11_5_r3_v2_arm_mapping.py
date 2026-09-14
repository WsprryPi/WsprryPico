"""Prospective acknowledged monotonic launch mapping, independent of later UTC updates."""
from phase11_5_inventory import require


def waveform_samples(job):
    """Independent integer model of waveform.cpp absolute-boundary conversion."""
    previous=0;cursor=0
    for n,event in enumerate(job['events']):
        require(int(event['offset_ns'])==cursor and int(event['duration_ns'])>0,'Sample timeline')
        cursor+=int(event['duration_ns'])
        padding=499 if n==len(job['events'])-1 and not event['rf_on'] else 250
        current=(cursor*69+padding)//500
        require(current>previous,'Collapsed sample interval');previous=current
    require(cursor==int(job['total_duration_ns']) and 0<cursor<=3600_000_000_000,'Sample duration')
    return previous
POLICY='acknowledged-monotonic-launch-v1'


def validate_mapping(request,ack,target):
    require(ack['job_id']==request['job_id'] and ack['state']=='armed' and
        ack['start_utc_ns']==request['start_utc_ns'],'ARM mapping identity')
    clock=ack['clock'];utc=int(clock['utc_now_ns']);mono=int(clock['monotonic_now_ns'])
    start=int(request['start_utc_ns']);nominal=int(ack['start_monotonic_ns'])
    require(clock['state']=='synchronized' and clock['leap']=='normal' and start>utc and
        nominal==mono+start-utc,'Acknowledged ARM clock mapping')
    adjustment=(-nominal)%1000
    require(target==nominal+adjustment and int(clock['uncertainty_ns'])+adjustment<=
        int(request['max_start_uncertainty_ns'])<=500000000,'ARM target quantization and uncertainty')
    return dict(policy=POLICY,acknowledged_start_monotonic_ns=nominal,hardware_target_ns=target,
        quantization_ns=adjustment,acknowledged_uncertainty_ns=int(clock['uncertainty_ns']))
