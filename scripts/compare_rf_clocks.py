#!/usr/bin/env python3
"""Compare finite odd-harmonic alias predictions for integer-symbol bench clocks."""
import argparse
import json
import math
from pathlib import Path
from predict_rf_spurs import alias, corrected_increment, simulate


def compare():
    rows = []
    for rate in range(120000000, 150000001, 3000000):
        # All candidates are exact 12 MHz * feedback / (5*2) PLL outputs.
        # 123,129,135,141,147 MHz instead use 12 MHz * feedback / (4*2).
        divisors = (5, 2) if rate % 6000000 == 0 else (4, 2)
        feedback = rate * math.prod(divisors) // 12000000
        assert feedback * 12000000 == rate * math.prod(divisors)
        assert 750000000 <= feedback * 12000000 <= 1600000000
        increment = corrected_increment(0, rate)
        base = alias(increment, 1, rate)
        features = []
        for harmonic in range(3, 10002, 2):
            frequency = alias(increment, harmonic, rate)
            if abs(frequency-base) <= 100000:
                features.append(dict(harmonic=harmonic, frequency_hz=frequency,
                                     ideal_coefficient_dbc=-20*math.log10(harmonic)))
        rows.append(dict(sample_rate_hz=rate, feedback=feedback, postdiv=list(divisors),
                         symbol_samples=rate*8192//12000, nearest_strong_aliases=features[:3]))
    return dict(qualification=False, span_from_carrier_hz=100000, maximum_harmonic=10001,
                limitation='Finite ideal coefficient search, not a bound on total aliases or analog output',
                clocks=rows)


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('output', type=Path)
    args = p.parse_args()
    result = compare()
    result['candidate_simulation'] = simulate(2222, sample_rate=138000000, harmonics=(1, 2125, 2127))
    with args.output.open('x') as output:
        output.write(json.dumps(result, indent=2)+'\n')
    print(json.dumps(result, indent=2))
