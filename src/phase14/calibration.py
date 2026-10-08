"""Derived measurement axes; never change original screens or Pico correction."""
import math


def quantities(measurement,reference):
    scale=reference['scale_nominal_to_true_time'];bound=reference['repeatability_bound_ppm']
    if (type(scale) not in (int,float) or not math.isfinite(scale) or abs(scale-1)>=100e-6 or
        type(bound) not in (int,float) or not math.isfinite(bound) or not 0<=bound<100 or
        reference['schema']!='phase14-reference/1' or reference['traceable_calibration'] is not False):
        raise ValueError('receiver reference comparison is not usable')
    result=dict(schema='phase14-derived-axes/1',sampling_scale=scale,repeatability_bound_ppm=bound,
        reference_accuracy_assumption_ppb=reference['reference_accuracy_assumption_ppb'],
        traceable_calibration=False,transmitter_frequency_correction_ppb=0,original_screen_unchanged=True,
        limitations=['Receiver scale comparison does not discipline the Pico oscillator or calibrate absolute UTC onset.',
            'Repeatability and engineering reference assumption exclude phase-fit bias and absolute reference certification.'])
    for key in ('observed_duration_s','max_transition_error_s'):
        if key in measurement:result[key+'_true_axis']=measurement[key]*scale
    for key in ('tone_spacing_hz','fitted_spacing_hz','max_symbol_residual_hz'):
        if key in measurement:result[key+'_true_axis']=measurement[key]/scale
    if 'linear_drift_hz_per_s' in measurement:
        result['linear_drift_hz_per_s_true_axes']=measurement['linear_drift_hz_per_s']/scale**2
    points=[]
    for fit in measurement.get('measurements',[]):
        if 'reference_compared_hz' not in fit:continue
        anchor=measurement['reference_hz'];value=anchor+(fit['reference_compared_hz']-anchor)/scale
        points.append(dict(index=fit.get('index'),frequency_hz_true_axis=value,
            sampling_repeatability_bound_hz=abs(value-anchor)*bound/1e6,
            reference_assumption_bound_hz=abs(anchor)*reference['reference_accuracy_assumption_ppb']/1e9))
    if points:result['reference_subtracted_frequencies']=points
    return result
