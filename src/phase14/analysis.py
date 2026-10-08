"""Phase 14 evidence binding around retained independent IQ analysis tools."""
import json
from pathlib import Path
from analyze_rf_bench import load_capture
from campaign import analysis as established
from measure_rf_bench import measure
from phase14.plan import GOLDEN37, BANDS, validate_capture, validate_physical, resources
from phase14.live import save
from led_closeout.runner import sha256, require


def analyze(directory, output_label="analysis"):
    directory=Path(directory).resolve()
    physical=validate_physical(json.loads((directory/'physical.json').read_text()))
    require(physical['result']=='CONTROL_COMPLETE','physical execution incomplete')
    meta=json.loads((directory/'capture.json').read_text())
    validate_capture(meta,directory/'capture.cf32',physical['receiver_settings'])
    require(physical['capture_sha256']==sha256(directory/'capture.cf32') and
            physical['metadata_sha256']==sha256(directory/'capture.json'),'physical capture binding')
    iq,metadata,capture_sha=load_capture(directory/'capture.cf32',directory/'capture.json')
    settings=metadata['actual_settings'];rate=settings['sample_rate_hz'];center=settings['center_frequency_hz']
    frequency=BANDS[physical['band']];mode=physical['mode'];job=physical['accepted_job']
    import re
    require(re.fullmatch('[a-z][a-z0-9-]{0,63}',output_label),'safe analysis label')
    output=directory/output_label;output.mkdir(mode=0o700)
    if mode=='TONE':
        reference=physical.get('reference')
        report=measure(iq,rate,center,duration_s=int(job['total_duration_ns'])/1e9,base_hz=frequency,
                       reference_hz=reference['f1'] if reference else None)
        result=dict(passed=report['relative_checks_passed'],measurement=report)
    elif mode=='WSPR':
        # Existing decoder and waveform are independent. Do not correct RF drift,
        # timing, or tune error to manufacture a successful decode.
        result=established.wspr(iq,rate,center,frequency,output,Path('/usr/bin/wsprd'),0)
        require((output/'decode.json').exists(),'independent decoder result absent')
        result['decode']=json.loads((output/'decode.json').read_text())
        result['decoder_sha256']=sha256('/usr/bin/wsprd')
    else:
        result=established.keyed(iq,rate,center,frequency,job)
    intervals=result.get('measurement',{}).get('intervals_s',result.get('observed_intervals_s',[]))
    frequencies=[m['indicated_hz'] for m in result.get('measurement',result).get('measurements',[])]
    excluded=[physical['reference']['f1']] if physical.get('reference') else []
    result['spectrum']=established.spectrum(iq,rate,center,frequencies,intervals,excluded_frequencies=excluded)
    if physical.get('reference'):
        result['spectrum']['reference_excluded_hz']=physical['reference']['f1']
        result['spectrum']['limitation']+='; excludes the known reference; normalization uses only the Pico carrier'
    result.update(schema='phase14-analysis/1',physical_sha256=sha256(directory/'physical.json'),
        capture_sha256=capture_sha,metadata_sha256=sha256(directory/'capture.json'),
        board=physical['board'],boot_id=physical['boot_id'],job_id=job['job_id'],clock_hz=physical['clock_hz'],
        source_revision=physical['source_revision'],firmware_sha256=physical['firmware_sha256'],
        band=physical['band'],mode=mode,release_qualified=False,
        disposition='OPERATIONAL_SCREEN_PASS' if result['passed'] else 'OPERATIONAL_SCREEN_FAIL',
        tools={str(p.relative_to(Path(__file__).resolve().parents[2])):sha256(p) for p in
            (Path(__file__),Path(__file__).resolve().parents[2]/'scripts/measure_rf_bench.py',
             Path(__file__).resolve().parents[1]/'campaign/analysis.py')},
        limitations=['Nominal SDR sample/time scale; no calibrated absolute UTC claim.',
                     'No measured output filter, insertion loss or calibrated source power.',
                     'Screening is not final repeated release acceptance.'])
    infos=[physical['before']]
    for line in (directory.parent/'events.jsonl').read_text().splitlines():
        entry=json.loads(line)
        if entry['kind']=='info' and entry['value']['board']==physical['board']:
            info=entry['value']['info']
            if (info['status']['boot_id']==physical['boot_id'] and
                info['status']['job_id']==job['job_id']):infos.append(info)
    infos.append(physical['after'])
    result['resources']=resources(infos,physical['clock_hz'])
    if not result['resources']['passed']:
        result['passed']=False;result['disposition']='OPERATIONAL_SCREEN_FAIL'
    # A sampled low tail is mandatory even when an analyzer reports success.
    require(intervals and intervals[-1][1]+.5<len(iq)/rate,'RF-off capture tail absent')
    save(output/'result.json',result)
    return {k:result[k] for k in ('board','clock_hz','band','mode','disposition')}
