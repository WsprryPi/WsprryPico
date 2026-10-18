# WsprryPico case

The printable parts are [Bottom.stl](Bottom.stl), [Top.stl](Top.stl),
[Wall-Hanger.stl](Wall-Hanger.stl) and [Opener.stl](Opener.stl), all in this
folder. Dimensions and CAD coordinates use millimetres.

The [interactive assembly view](pico-case-assembly.html) shows these Bottom,
Top and Opener meshes with a simplified Pico 2 W board, USB socket, BOOTSEL
switch and GPIO headers. Rotate and zoom the assembled, cutaway, lifted-lid,
underside and individual stencil views. The viewer needs internet access for
its pinned Three.js library and native browser gzip decompression support.

| Part | X × Y × Z envelope (mm) | Features |
| --- | --- | --- |
| Bottom | 56.70 × 27.20 × 13.95 | Flat interior, board supports, header slots, port reliefs and snap recesses |
| Top | 56.70 × 27.20 × 5.40 | BOOTSEL actuator, LED guide, board clamps, snap ribs and WsprryPico stencil |
| Wall-Hanger | 58.40 × 33.44 × 17.95 | Flat plate, countersunk holes, spring clips and locating ears |
| Opener | 18.62 × 22.01 × 3.10 | Beveled grip, tapered ramp, working tab and WsprryPico stencil |

The assembled case envelope is 56.7 × 27.2 × 15.35 mm. The board seat accepts
a nominal 51 × 21 × 1 mm PCB envelope. Printed fit, snap force, opener strength
and clearance around actual board components require physical checks.

## Stencil

The [black-and-white artwork](wsprrypico-stencil.png) contains seven berry
openings, two leaves with single straight veins, a stem and a square-to-sine
waveform. White regions are holes; black regions are material.

The [Top aperture drawing](parametric/generated/Top-stencil.svg) measures
20.0 × 18.5013 mm. Its stem points toward USB and the waveform reads from
outside the case. The minimum material between openings is 0.6035 mm.

The [Opener aperture drawing](parametric/generated/Opener-stencil.svg)
measures 15.0 × 12.4884 mm. Its stem points toward the grip butt and the
waveform reads from the upper face. Material between openings measures at
least 0.6036 mm, with at least 0.6487 mm beyond the perimeter bevel. The holes
stop 1.7274 mm before the working tab. Along the grip axes, the opener is
20.9187 mm long and 15.0000 mm wide, with a maximum thickness of 3.1 mm.

## CAD sources

The [parametric directory](parametric/) contains the editable CAD sources:

- [model.py](parametric/model.py): CadQuery features and export commands.
- [parameters.json](parametric/parameters.json): dimensions and feature settings.
- [profiles.json](parametric/profiles.json): two-dimensional mechanical sketches.
- [stencil.json](parametric/stencil.json) and [stencil.py](parametric/stencil.py):
  aperture geometry, placement and bridge clearance.
- [trace_stencil.py](parametric/trace_stencil.py): artwork tracing.
- [verify.py](parametric/verify.py): CAD, mesh and nominal assembly checks.

[STEP solids and aperture drawings](parametric/generated/) are kept below the
CAD sources. The STLs stay in the case folder's root. STEP contains boundary
representation solids; feature definitions and parameter relationships remain
in the Python and JSON files.

Parameters cover the envelope, walls, floor, board supports, header slots,
latches, BOOTSEL actuator, LED bore, hanger clips and opener. Stencil height,
width, placement and minimum bridge width are editable. Changes to an envelope
or mounting arrangement require reviewing dependent sketches and mating parts;
arbitrary parameter combinations are not a constrained assembly solver.

## Regenerate and check

Use Python 3.12 with [requirements-lock.txt](parametric/requirements-lock.txt).
[requirements.txt](parametric/requirements.txt) lists the directly used packages.

From this folder, with that Python environment active:

```sh
python -m pip install -r parametric/requirements-lock.txt
python parametric/model.py
python parametric/verify.py --exercise-parameters
```

Regeneration writes the four root STLs and updates STEP solids, aperture SVGs
and mesh-export settings under `parametric/generated/`. `--part Top` regenerates
one part. `--output` selects a separate case folder with the same layout.

The maintained stencil outlines support size and placement changes without
retracing. After editing the artwork, run `python parametric/trace_stencil.py`
before regeneration; tracing requires eleven separate apertures. The saved
interactive view embeds a snapshot of the STL meshes and needs refreshing
after geometry changes.

[verification.json](parametric/verification.json) records mesh integrity,
STEP validity, dimensions, volumes and bidirectional distances between each
root STL and a finer tessellation of its STEP solid. Checks also cover flat
interior surfaces, stencil passages and bridge widths, opener tip clearance,
nominal assembly overlap and a header-slot parameter edit. The report records
checksums for the current CAD inputs and exports.
