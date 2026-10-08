"""Matched Hann peak-bin diagnostics; no calibrated power or emission mask."""
import math
import numpy as np


def compare(iq,rate,center,carrier,interval,fft_samples=1048576):
    if (type(fft_samples) is not int or fft_samples<8 or
        any(not math.isfinite(v) for v in (rate,center,carrier)) or rate<=0 or
        fft_samples/rate<1 or abs(carrier-center)+125>=rate/2):
        raise ValueError('usable close-in FFT span required')
    start,end=interval
    if not 0<=start<end<=len(iq)/rate:raise ValueError('complete on interval required')
    on=round((start+.1)*rate);off=round((end+.5)*rate)
    if on+fft_samples>round((end-.1)*rate) or off+fft_samples>len(iq):
        raise ValueError('complete matched on/off FFT windows required')
    window=np.hanning(fft_samples);times=np.arange(fft_samples)/rate
    def power(first):
        samples=np.asarray(iq[first:first+fft_samples])
        if not np.isfinite(samples).all():raise ValueError('nonfinite spectral samples')
        mixed=samples*np.exp(-2j*np.pi*(carrier-center)*times)
        return np.abs(np.fft.fft(mixed*window))**2/window.sum()**2
    active=power(on);quiet=power(off);bins=np.fft.fftfreq(fft_samples,1/rate)
    main=np.abs(bins)<=2
    reference=max(float(active[main].max()),1e-300)
    def peak(mask):
        positions=np.flatnonzero(mask)
        if not len(positions):raise ValueError('spectral comparison bins absent')
        at=positions[np.argmax(active[positions])]
        maximum=max(float(active[at]),1e-300)
        return dict(offset_hz=float(bins[at]),peak_dbc=float(10*np.log10(maximum/reference)),
            on_minus_off_db=float(10*np.log10(maximum/max(float(quiet[at]),1e-300))))
    return dict(schema='phase14-closein-power/1',fft_samples=fft_samples,bin_width_hz=rate/fft_samples,
        on_interval_s=[on/rate,(on+fft_samples)/rate],off_interval_s=[off/rate,(off+fft_samples)/rate],
        carrier_indicated_hz=carrier,
        carrier_on_minus_off_db=float(10*np.log10(reference/max(float(quiet[main].max()),1e-300))),
        lower_120=peak(np.abs(bins+120)<=5),upper_120=peak(np.abs(bins-120)<=5),
        nearby_2_to_50=peak((np.abs(bins)>2)&(np.abs(bins)<=50)),
        method='One full Hann window inside on RF and one equal trailing-off window; measured-carrier centering; +/-5 Hz around +/-120 Hz.',
        limitation='Relative peak-bin/on-off diagnostic; no integrated emissions, filtered-output, absolute power or UTC claim.')
