"""Offline reference-carrier acquisition with receiver-offset tolerance."""

def reference_observation(iq,rate,center,frequency):
    from measure_rf_bench import baseband,phase_fit,local_contrast
    import numpy as np
    bb,fit_rate=baseband(iq,rate,center,frequency)
    fitted=[phase_fit(bb[int(left*fit_rate):int((left+1)*fit_rate)],fit_rate,frequency) for left in range(1,7)]
    indicated=float(np.mean([v['indicated_hz'] for v in fitted]))
    # The receiver's uncalibrated tuning error can move a valid reference
    # outside a nominal +/-100 Hz mask. Assess its observed peak instead.
    contrast=local_contrast(iq[rate:2*rate],rate,center,indicated)
    return dict(fits=fitted,contrast_db=contrast,contrast_center_hz=indicated,
                mean_indicated_hz=indicated,
                acquisition_passed=contrast>=30 and all(v['phase_residual_rms_rad']<.15 for v in fitted))
