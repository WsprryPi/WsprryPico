"""One fixed receiver audio retune on retained IQ; no RF or waveform repair."""
import copy
import json
from pathlib import Path
import subprocess
import wave

from led_closeout.runner import require,sha256
from phase14.live import save
from phase14.plan import validate_capture
from phase14.wspr_decode import assess as decode_assess
from phase15_13.plan import FREQUENCIES


def decode(directory,offset_hz,*,nominal_label='analysis'):
    require(type(offset_hz) is int and offset_hz in (125,200),'enumerated fixed receiver offset')
    directory=Path(directory)
    physical=json.loads((directory/'physical.json').read_text())
    require(physical['mode']=='WSPR','receiver-only WSPR diagnosis')
    metadata=json.loads((directory/'capture.json').read_text())
    validate_capture(metadata,directory/'capture.cf32',physical['receiver_settings'])
    original=json.loads((directory/nominal_label/'result.json').read_text())
    receipt=json.loads((directory/nominal_label/'decode.json').read_text())
    label='receiver-plus'+str(offset_hz)+'hz'
    output=directory/label;output.mkdir(mode=0o700)
    import numpy as np
    from decode_rf_wspr import audio_from_iq
    iq=np.memmap(directory/'capture.cf32',dtype='<c8',mode='r')
    rate=metadata['actual_settings']['sample_rate_hz']
    start=receipt['window_start_s']
    selected=iq[round(start*rate):round((start+120)*rate)]
    frequency=FREQUENCIES[physical['band']]
    audio=audio_from_iq(selected,rate,metadata['actual_settings']['center_frequency_hz'],frequency+offset_hz)
    wav=output/Path(receipt['command'][-1]).name
    with wave.open(str(wav),'wb') as stream:
        stream.setnchannels(1);stream.setsampwidth(2);stream.setframerate(12000);stream.writeframes(audio.tobytes())
    command=['/usr/bin/wsprd','-d','-H','-f',str((frequency+offset_hz-1500)/1e6),str(wav)]
    run=subprocess.run(command,cwd=output,capture_output=True,text=True,timeout=90)
    (output/'wsprd.stdout').write_text(run.stdout);(output/'wsprd.stderr').write_text(run.stderr)
    matches=[line for line in run.stdout.splitlines() if len(line.split())==8 and line.split()[-3:]==['AA0NT','EM18','37']]
    value=dict(command=command,returncode=run.returncode,matches=matches,decoded=run.returncode==0 and bool(matches),
        window_start_s=start,receiver_audio_offset_hz=offset_hz,
        original_analysis_sha256=sha256(directory/nominal_label/'result.json'),original_analysis_label=nominal_label,
        capture_sha256=metadata['output']['sha256'],
        metadata_sha256=sha256(directory/'capture.json'),audio_sha256=sha256(wav),decoder_sha256=sha256('/usr/bin/wsprd'),
        method='Same original IQ and burst-relative time window; one fixed audio tuning translation for the entire frame. No drift, time warping, symbol correction, retransmission or waveform change.')
    save(output/'decode.json',value)
    revised=copy.deepcopy(original)
    revised['decoded']=value['decoded'];revised['decode']=value
    revised['wspr_decode_acceptance']=decode_assess(revised,value,run.stdout)
    revised['receiver_diagnosis']=value
    save(output/'result.json',revised)
    from phase15_13.assessment import assess
    return assess(directory,label)
