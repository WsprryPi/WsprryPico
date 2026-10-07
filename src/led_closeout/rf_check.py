"""Uncalibrated RF presence relative to each capture's inactive ends."""
from pathlib import Path

from led_closeout.runner import require


def check_capture(path, emitting, *, sample_rate=250000, center=3550000, frequency=3570100):
    import numpy as np
    size = 8192
    bins = np.fft.fftfreq(size, 1/sample_rate)
    offsets = np.abs(bins-(frequency-center))
    selected = offsets <= 500
    reference = (offsets >= 750) & (offsets <= 2500)
    require(selected.any() and reference.any(), 'RF test band outside receiver')
    window = np.hanning(size)
    powers, contrasts = [], []
    with Path(path).open('rb') as stream:
        while True:
            chunk = np.fromfile(stream, dtype='<c8', count=size*64)
            usable = len(chunk)//size
            if not usable:
                break
            chunk = chunk[:usable*size].reshape(usable, size)
            require(np.isfinite(chunk).all(), 'nonfinite SDR samples')
            transformed = np.fft.fft(chunk*window, axis=1)
            spectrum = np.abs(transformed)**2
            band = np.mean(spectrum[:,selected], axis=1)
            noise = np.mean(spectrum[:,reference], axis=1)
            require((noise > 0).all(), 'zero/no usable receiver noise reference')
            powers.extend(band.tolist())
            contrasts.extend((band/noise).tolist())
    require(len(powers) >= int(6*sample_rate/size), 'RF capture too short for inactive reference')
    ends = max(1,int(3*sample_rate/size))
    # The job may start at the next UTC boundary. The final three seconds are
    # inactive; choosing the lower end also tolerates a near-boundary start.
    baseline = min(float(np.median(powers[:ends])),float(np.median(powers[-ends:])))
    require(baseline > 0, 'zero/no usable receiver noise reference')
    ratio = max(powers)/baseline
    detected = max(contrasts) >= 10
    inactive_tail = float(np.median(contrasts[-ends:])) < 10
    passed = inactive_tail and (detected == bool(emitting)) and (not emitting or ratio >= 10)
    result = dict(schema='phase13.1-rf-presence/1', expected_emission=emitting,
                  detected=bool(detected), peak_to_inactive_ratio=ratio,
                  threshold_ratio=10, peak_band_to_neighbor_ratio=max(contrasts),
                  tail_band_to_neighbor_ratio=float(np.median(contrasts[-ends:])),
                  inactive_tail=inactive_tail, passed=passed,
                  blocks=len(powers), sample_rate_hz=sample_rate,
                  band_hz=[frequency-500,frequency+500], scope='uncalibrated RF presence only')
    return result
