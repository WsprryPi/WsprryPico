"""Independent windowed FIR and keyed-carrier phase diagnostics."""
import numpy as np

def narrow_fir(samples,rate,cutoff):
    # Independent windowed-sinc FIR and linear FFT convolution using the
    # retained NumPy runtime. The halo excludes convolution boundary effects.
    taps=4097;index=np.arange(taps)-(taps-1)/2
    kernel=2*cutoff/rate*np.sinc(2*cutoff/rate*index)*np.kaiser(taps,8.6);kernel/=kernel.sum()
    count=len(samples)+taps-1;size=1<<(count-1).bit_length()
    full=np.fft.ifft(np.fft.fft(samples,size)*np.fft.fft(kernel,size))[:count]
    return full[taps//2:taps//2+len(samples)]

def polynomial(samples,rate):
    t=np.arange(len(samples))/rate;t-=t.mean();phase=np.unwrap(np.angle(samples))
    line=np.polyfit(t,phase,1);curve=np.polyfit(t,phase,2)
    return dict(linear_phase_rms_rad=float(np.sqrt(np.mean((phase-np.polyval(line,t))**2))),
        quadratic_phase_rms_rad=float(np.sqrt(np.mean((phase-np.polyval(curve,t))**2))),
        fitted_frequency_drift_hz_per_s=float(curve[0]/np.pi),
        fitted_drift_across_interval_hz=float(curve[0]/np.pi*(len(samples)-1)/rate))
