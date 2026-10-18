#!/usr/bin/env python3
"""Trace the approved PNG's white apertures into normalized CAD sketch data."""
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image
from scipy import ndimage
from shapely.geometry import Polygon

HERE = Path(__file__).resolve().parent


def main():
    source = HERE.parent / "wsprrypico-stencil.png"
    pixels = np.asarray(Image.open(source).convert("RGB"))
    white = pixels.mean(axis=2) >= 128
    _, black_components = ndimage.label(~white, structure=np.ones((3, 3)))
    _, white_components = ndimage.label(white, structure=np.ones((3, 3)))
    if black_components != 1 or white_components != 11:
        raise ValueError("Expected connected black material and eleven white apertures")
    figure, axes = plt.subplots()
    contours = axes.contour(white.astype(float), levels=[.5]).allsegs[0]
    plt.close(figure)
    raw = [Polygon(points).simplify(.75, preserve_topology=True) for points in contours]
    if len(raw) != 11 or any(not p.is_valid or p.interiors for p in raw):
        raise ValueError("Stencil contours must be eleven simple polygons")
    x0, y0 = np.min([p.bounds[:2] for p in raw], axis=0)
    x1, y1 = np.max([p.bounds[2:] for p in raw], axis=0)
    height = y1-y0
    wave = max(raw, key=lambda p: p.bounds[2]-p.bounds[0])
    profiles = []
    for polygon in raw:
        bounds = polygon.bounds
        if polygon is wave:
            role = "waveform"
        elif bounds[3] < y0+.32*height:
            role = "stem" if bounds[2]-bounds[0] < .15*(x1-x0) else "leaf"
        else:
            role = "berry"
        profiles.append({"role": role, "outer": [[round((x-x0)/height, 8), round((y-y0)/height, 8)]
                                                 for x, y in list(polygon.exterior.coords)[:-1]]})
    result = {
        "artwork": "../wsprrypico-stencil.png",
        "artwork_sha256": hashlib.sha256(source.read_bytes()).hexdigest(),
        "description": "WsprryPico stencil; white apertures pass through the part.",
        "trace": {"threshold": 128, "simplification_pixels": .75,
                  "normalization": "image U right, V down; image aperture height is 1",
                  "aperture_bounds_pixels": [x0, y0, x1, y1]},
        "aspect_width_over_height": (x1-x0)/height,
        "profiles": profiles,
    }
    (HERE / "stencil.json").write_text(json.dumps(result, indent=2)+"\n")
    print("Traced", {role: sum(p["role"] == role for p in profiles) for role in ["berry", "leaf", "stem", "waveform"]})


if __name__ == "__main__":
    main()
