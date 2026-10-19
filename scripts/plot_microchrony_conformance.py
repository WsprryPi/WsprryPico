#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Render the public conformance summary with an installed gnuplot."""
import argparse
import json
import math
from pathlib import Path
import subprocess
import tempfile

SCRIPT = r"""set terminal pngcairo size 1800,1100 enhanced font 'Arial,17' background rgb '#ffffff'
set output 'figure.png'
set multiplot layout 2,3 title 'μChrony and Chrony 4.9 • identical four-source inputs, known oscillator error' font ',23' margins .065,.98,.10,.89 spacing .07,.13
set grid ytics lc rgb '#dddddd'
set border 3 lw 1.2 lc rgb '#555555'
set tics nomirror
set key top right font ',14'
set xlabel 'Simulated minutes'
set ylabel 'UTC RMS, 5-minute bins (ms)'
set xrange [0:240]
set yrange [0:7]
set xtics 60
set ytics 1
set title 'Weak queue asymmetry • +0.8 ppm'
plot 'internet_weak_queue.dat' using 1:2 with lines lw 3 lc rgb '#245b83' title 'μChrony', '' using 1:3 with lines dt 2 lw 2.5 lc rgb '#d0782d' title 'Chrony 4.9'
set title 'Forward queue • +0.8 ppm'
plot 'internet_forward_queue.dat' using 1:2 with lines lw 3 lc rgb '#245b83' title 'μChrony', '' using 1:3 with lines dt 2 lw 2.5 lc rgb '#d0782d' title 'Chrony 4.9'
set title 'Reverse queue • −0.65 ppm'
plot 'internet_reverse_queue.dat' using 1:2 with lines lw 3 lc rgb '#245b83' title 'μChrony', '' using 1:3 with lines dt 2 lw 2.5 lc rgb '#d0782d' title 'Chrony 4.9'
set xlabel 'Measurement window (minutes)'
set ylabel 'RMS benefit from learned rate (μs)'
set xrange [-.2:3.2]
set yrange [-750:400]
set ytics 250
set xtics ('0–10' 0,'10–60' 1,'60–120' 2,'180–240' 3)
set key bottom right
set arrow 1 from graph 0,first 0 to graph 1,first 0 nohead lw 1.5 lc rgb '#333333'
set title 'Weak queue • positive helps, negative harms'
plot 'internet_weak_queue-gain.dat' using 1:2 with linespoints pt 7 ps 1.2 lw 2.5 lc rgb '#245b83' title 'μChrony', '' using 1:3 with linespoints dt 2 pt 6 ps 1.2 lw 2.5 lc rgb '#d0782d' title 'Chrony 4.9'
set title 'Forward queue • early harm retained'
plot 'internet_forward_queue-gain.dat' using 1:2 with linespoints pt 7 ps 1.2 lw 2.5 lc rgb '#245b83' title 'μChrony', '' using 1:3 with linespoints dt 2 pt 6 ps 1.2 lw 2.5 lc rgb '#d0782d' title 'Chrony 4.9'
set title 'Reverse queue • early harm retained'
plot 'internet_reverse_queue-gain.dat' using 1:2 with linespoints pt 7 ps 1.2 lw 2.5 lc rgb '#245b83' title 'μChrony', '' using 1:3 with linespoints dt 2 pt 6 ps 1.2 lw 2.5 lc rgb '#d0782d' title 'Chrony 4.9'
unset multiplot
"""
CASES = ('internet_weak_queue', 'internet_forward_queue', 'internet_reverse_queue')


def number(value):
    if type(value) not in (int, float) or not math.isfinite(value):
        raise ValueError('Finite numeric chart value required')
    return value


def render(summary, output):
    curves = summary['known_truth_loops']['five_minute_rms']
    if set(curves) != set(CASES):
        raise ValueError('The figure requires its three declared Internet cases')
    top, gains = [], []
    with tempfile.TemporaryDirectory(prefix='microchrony-figure-') as directory:
        root = Path(directory)
        for case in CASES:
            curve = curves[case]
            if [r['end_minute'] for r in curve] != list(range(5, 241, 5)):
                raise ValueError('Complete ordered five-minute bins required')
            for row in curve:
                for who in ('microchrony', 'chrony49'):
                    value = number(row[who]['utc_rms_ms'])
                    if value < 0 or row[who]['samples'] <= 0:
                        raise ValueError('Invalid RMS or sample count')
                    top.append(value)
            (root/(case+'.dat')).write_text(''.join(
                str(row['end_minute'])+' '+ ' '.join(str(row[who]['utc_rms_ms'])
                    for who in ['microchrony','chrony49'])+'\n' for row in curve))
            controllers = summary['rate_benefit']['cases'][case]['controllers']
            windows = ['0_600_seconds','600_3600_seconds','3600_7200_seconds','10800_14400_seconds']
            gains.extend(number(controllers[who]['periods'][window]['rms_gain_us'])
                         for who in ('microchrony', 'chrony49') for window in windows)
            (root/(case+'-gain.dat')).write_text(''.join(str(i)+' '+ ' '.join(
                str(controllers[who]['periods'][window]['rms_gain_us'])
                for who in ['microchrony','chrony49'])+'\n' for i,window in enumerate(windows)))
        script = SCRIPT.replace('set yrange [0:7]',
                                'set yrange [0:'+str(max(1, math.ceil(max(top))))+']')
        low = min(-250, math.floor(min(gains)/250)*250)
        high = max(250, math.ceil(max(gains)/250)*250)
        script = script.replace('set yrange [-750:400]', f'set yrange [{low}:{high}]')
        subprocess.run(['gnuplot'],input=script,text=True,cwd=root,check=True,timeout=30)
        output.write_bytes((root/'figure.png').read_bytes())


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('summary',type=Path)
    parser.add_argument('output',type=Path)
    args = parser.parse_args()
    render(json.loads(args.summary.read_text()),args.output)
