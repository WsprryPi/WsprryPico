"""Phase 14 evidence binding around retained independent IQ analysis tools."""
import json
from pathlib import Path
from analyze_rf_bench import load_capture
from campaign import analysis as established
from measure_rf_bench import measure
from phase14.plan import GOLDEN37, BANDS, validate_capture
from phase14.live import save
from led_closeout.runner import sha256, require


def analyze(directory):
    directory=Path(directory).resolve()
    physical=json.loads((directory/'physical.json').read_text())
    require(physical['result']=='CONTROL_COMPLETE','physical execution incomplete')
    meta=json.loads((directory/'capture.json').read_text())
    validate_capture(meta,directory/'capture.cf32',physical['receiver_settings'])
    require(physical['capture_sha256']==sha256(directory/'capture.cf32') and
            physical['metadata_sha256']==sha256(directory/'capture.json'),'physical capture binding')
    iq,metadata,capture_sha=load_capture(directory/'capture.cf32',directory/'capture.json')
    settings=metadata['actual_settings'];rate=settings['sample_rate_hz'];center=settings['center_frequency_hz']
    frequency=BANDS[physical['band']];mode=physical['mode'];job=physical['accepted_job']
    output=directory/'analysis';output.mkdir(mode=0o700)
    if mode=='TONE':
        report=measure(iq,rate,center,duration_s=int(job['total_duration_ns'])/1e9,base_hz=frequency)
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
    result['spectrum']=established.spectrum(iq,rate,center,frequencies,intervals)
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
    # A sampled low tail is mandatory even when an analyzer reports success.
    require(intervals and intervals[-1][1]+.5<len(iq)/rate,'RF-off capture tail absent')
    save(output/'result.json',result)
    return {k:result[k] for k in ('board','clock_hz','band','mode','disposition')}
