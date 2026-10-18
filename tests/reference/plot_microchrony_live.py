#!/usr/bin/env python3
# SPDX-License-Identifier: MIT
"""Plot derived live telemetry with an already installed gnuplot; no hardware IO."""
from datetime import datetime
import json
from pathlib import Path
import subprocess
import sys
import tempfile

source, destination = map(Path, sys.argv[1:])
report = json.loads(source.read_text())
destination = destination.resolve()
destination.parent.mkdir(parents=True, exist_ok=True)
experiment = report['experiment']
cross = (datetime.fromisoformat(experiment['crossover_ct'])-
         datetime.fromisoformat(experiment['start_ct'])).total_seconds()/60


def quote(value):
    return '"'+str(value).replace('\\', '\\\\').replace('"', '\\"')+'"'


with tempfile.TemporaryDirectory(prefix='microchrony-live-plot-') as temporary:
    root = Path(temporary)
    for name, data in report['conditions'].items():
        rows = []
        for point in data['curve']:
            rate = 'NaN' if point['frequency_ppm'] is None else str(point['frequency_ppm'])
            rows.append(f"{point['elapsed_minutes']} {rate} {point['skew_ppm']}")
        (root/(name+'.tsv')).write_text('\n'.join(rows)+'\n')
    commands = [
        'set terminal pngcairo size 1500,1000 font "Helvetica,12"',
        'set output '+quote(destination), 'set encoding utf8', 'set border 3',
        'set tics nomirror', 'set grid lc rgb "#dddddd"',
        'set key top right opaque font ",10"', 'set xrange [0:120]',
        'set multiplot layout 2,2 margins .075,.985,.10,.91 spacing .09,.12 '
        'title "μChrony A/B crossover — 18 October 2026 (CDT)" font ",18"',
        f'set arrow 1 from {cross}, graph 0 to {cross}, graph 1 nohead dt 2 lc rgb "#777777"',
        'set xlabel "Minutes since 11:19:32 AM CDT"',
    ]
    for column in (2, 3):
        for board in ('A', 'B'):
            if column == 2:
                commands += ['unset logscale y', 'set yrange [-105:105]',
                             'set ylabel "UTC frequency estimate (ppm)"']
            else:
                commands += ['set logscale y', 'set yrange [0.5:*]',
                             'set ylabel "Reported rate uncertainty (ppm)"', 'set format y "%g"']
            suffix = 'frequency estimate' if column == 2 else 'rate uncertainty'
            commands.append('set title '+quote(f'Board {board}: {suffix}'))
            series = []
            for phase in ('phase1', 'phase2'):
                name = phase+'_'+board
                server = report['conditions'][name]['source']
                color = '#7c3aed' if server == 'pool.ntp.org' else '#059669'
                series.append(quote(root/(name+'.tsv'))+f' using 1:{column} with lines lw 2 '
                              f'lc rgb "{color}" title '+quote(server))
            if column == 3:
                series.append('5 with lines dt 3 lc rgb "#444444" title "5 ppm statistical gate"')
            commands.append('plot '+', '.join(series))
    commands += ['unset multiplot']
    script = root/'plot.gnuplot'
    script.write_text('\n'.join(commands)+'\n')
    subprocess.run(['gnuplot', str(script)], check=True, timeout=30)
print(destination)
