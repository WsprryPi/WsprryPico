#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Plot saved clock-loop truth errors with the installed standard gnuplot."""
import json
import argparse
from pathlib import Path
import subprocess
import sys

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('before',type=Path)
parser.add_argument('after',type=Path)
parser.add_argument('destination',type=Path)
parser.add_argument('--adaptive',action='store_true')
args=parser.parse_args()
before,after,destination=args.before,args.after,args.destination
b,a = json.loads(before.read_text()),json.loads(after.read_text())
destination.mkdir(parents=True,exist_ok=True)
for name in ['noisy_frequency_step','jitter_500us','heldout_pool','heldout_ramp']:
    case = a['cases'][name]
    streams = [case['reference_rows'],case['microchrony_rows'],b['cases'][name]['microchrony_rows']]
    maps = [{r[0]:r for r in rows if r[1]==0 and r[2]>-10**18} for rows in streams]
    lines=[]
    for t in sorted(set(maps[0])&set(maps[1])&set(maps[2])):
        plant=case['plant'];seconds=t/1e9
        ppm=plant.get('after_ppm',plant['ppm']) if seconds>=plant.get('switch_s',float('inf')) else plant['ppm']
        ppm+=plant.get('ramp_ppm_per_hour',0)*seconds/3600
        rows=[m[t] for m in maps]
        values=[seconds/60,*[(r[2]-t)/1e6 for r in rows],
                *[((1+ppm/1e6)*(1+r[3]/1e6)-1)*1e6 for r in rows]]
        lines.append('\t'.join(f'{v:.12g}' for v in values))
    (destination/(name+'.tsv')).write_text('\n'.join(lines)+'\n')

script='''set terminal pngcairo size 1500,1000 font "Helvetica,12"
set output "convergence.png"
set encoding utf8
set border 3
set tics nomirror
set grid lc rgb "#dddddd"
set key opaque box samplen 2 font ",10"
set style line 1 lc rgb "#059669" lw 2
set style line 2 lc rgb "#2563eb" lw 2
set style line 3 lc rgb "#d97706" lw 1.5 dt 2
floorerror(x) = abs(x)<.001 ? .001 : abs(x)
set multiplot layout 2,2 margins .075,.98,.08,.92 spacing .09,.12 title "Known-truth clock-loop comparison — identical oscillator and network events" font ",17"
set title "40 ppm oscillator change, with ±0.5 ms path jitter"
set xlabel "Minutes since oscillator change"
set ylabel "UTC error (ms)"
set xrange [-2:16]
set yrange [*:*]
plot "noisy_frequency_step.tsv" using ($1-60):4 w l ls 3 title "μChrony before", "" using ($1-60):2 w l ls 1 title "Chrony 4.9", "" using ($1-60):3 w l ls 2 title "μChrony fixed", 0 w l lc rgb "#777777" dt 3 notitle
set title "Frequency recovery for the same oscillator change"
set ylabel "Pure frequency error (ppm)"
plot "noisy_frequency_step.tsv" using ($1-60):7 w l ls 3 title "μChrony before", "" using ($1-60):5 w l ls 1 title "Chrony 4.9", "" using ($1-60):6 w l ls 2 title "μChrony fixed", 0 w l lc rgb "#777777" dt 3 notitle
set title "Single source: frequency learns before two hours"
set xlabel "Minutes since start"
set ylabel "Absolute pure frequency error (ppm)"
set xrange [0:120]
set yrange [0.001:200]
set logscale y
plot "jitter_500us.tsv" using 1:(floorerror($7)) w l ls 3 title "μChrony before", "" using 1:(floorerror($5)) w l ls 1 title "Chrony 4.9", "" using 1:(floorerror($6)) w l ls 2 title "μChrony fixed", 1 w l lc rgb "#777777" dt 3 title "1 ppm reference line"
unset logscale y
set title "Four sources: ±5 ms path jitter (new noise seed)"
set ylabel "UTC error (ms)"
set xrange [0:240]
set yrange [*:*]
plot "heldout_pool.tsv" using 1:4 w l ls 3 title "μChrony before", "" using 1:2 w l ls 1 title "Chrony 4.9", "" using 1:3 w l ls 2 title "μChrony fixed", 0 w l lc rgb "#777777" dt 3 notitle
unset multiplot
'''
if args.adaptive:
    common=script[:script.index('set multiplot')]
    script=common+'''set multiplot layout 2,2 margins .075,.98,.08,.92 spacing .09,.12 title "Adaptive history and source combination — known-truth clock loops" font ",17"
set title "Four sources: UTC convergence, ±5 ms path jitter"
set xlabel "Minutes since start"
set ylabel "UTC error (ms)"
set xrange [0:240]
plot "heldout_pool.tsv" using 1:4 w l ls 3 title "μChrony previous", "" using 1:2 w l ls 1 title "Chrony 4.9", "" using 1:3 w l ls 2 title "μChrony corrected", 0 w l lc rgb "#777777" dt 3 notitle
set title "Four sources: frequency acquisition"
set ylabel "Absolute pure frequency error (ppm)"
set xrange [0:60]
set yrange [0.001:200]
set logscale y
plot "heldout_pool.tsv" using 1:(floorerror($7)) w l ls 3 title "μChrony previous", "" using 1:(floorerror($5)) w l ls 1 title "Chrony 4.9", "" using 1:(floorerror($6)) w l ls 2 title "μChrony corrected", 1 w l lc rgb "#777777" dt 3 title "1 ppm reference line"
unset logscale y
set title "Four sources: final hour (RMS scoring interval)"
set ylabel "UTC error (ms)"
set xrange [180:240]
set yrange [*:*]
plot "heldout_pool.tsv" using 1:4 w l ls 3 title "μChrony previous", "" using 1:2 w l ls 1 title "Chrony 4.9", "" using 1:3 w l ls 2 title "μChrony corrected", 0 w l lc rgb "#777777" dt 3 notitle
set title "Oscillator ramp: 18 ppm/hour, ±0.1 ms jitter"
set xrange [0:240]
plot "heldout_ramp.tsv" using 1:4 w l ls 3 title "μChrony previous", "" using 1:2 w l ls 1 title "Chrony 4.9", "" using 1:3 w l ls 2 title "μChrony corrected", 0 w l lc rgb "#777777" dt 3 notitle
unset multiplot
'''
(destination/'plot.gp').write_text(script)
subprocess.run(['gnuplot','plot.gp'],cwd=destination,check=True)
print(destination/'convergence.png')
