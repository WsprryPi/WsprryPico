#!/usr/bin/env python3
"""Check current STL meshes against the parametric STEP solids."""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import platform
import tempfile
from pathlib import Path

import cadquery as cq
import numpy as np
import trimesh
from shapely.geometry import Polygon

import model
import stencil

HERE = Path(__file__).resolve().parent
PARTS = tuple(model.BUILDERS)


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def integrity(mesh):
    _, counts = np.unique(mesh.edges_sorted, axis=0, return_counts=True)
    return {
        "watertight": bool(mesh.is_watertight),
        "consistent_winding": bool(mesh.is_winding_consistent),
        "connected_components": len(mesh.split(only_watertight=False)),
        "boundary_edges": int(np.count_nonzero(counts == 1)),
        "nonmanifold_edges": int(np.count_nonzero(counts > 2)),
        "degenerate_faces": int(np.count_nonzero(~mesh.nondegenerate_faces(height=1e-8))),
        "positive_volume": bool(mesh.volume > 0),
        "finite_vertices": bool(np.all(np.isfinite(mesh.vertices))),
        "vertices": len(mesh.vertices),
        "triangles": len(mesh.faces),
    }


def distances(target, points):
    out = []
    for start in range(0, len(points), 1000):
        _, distance, _ = trimesh.proximity.closest_point(target, points[start:start+1000])
        out.append(distance)
    return np.concatenate(out)


def surface_comparison(mesh, target, samples):
    points, _ = trimesh.sample.sample_surface(mesh, samples, seed=1977)
    distance = distances(target, points)
    vertex_distances = distances(target, mesh.vertices)
    return {
        "area_weighted_samples": samples,
        "seed": 1977,
        "mean_mm": float(np.mean(distance)),
        "p99_mm": float(np.percentile(distance, 99)),
        "sample_max_mm": float(np.max(distance)),
        "vertex_max_mm": float(np.max(vertex_distances)),
        "note": "Finite sampling and vertex checks against a finer STEP tessellation; not a certified Hausdorff bound.",
    }


def slot_widths(mesh, length, floor):
    origins = np.array([[length / 2, -1.0, floor / 2]])
    locations, _, _ = mesh.ray.intersects_location(origins, np.array([[0, 1, 0]]))
    yy = np.unique(np.round(locations[:, 1], 6))
    if len(yy) != 6:
        raise AssertionError(f"Expected six floor intersections; found {yy}")
    return [float(yy[2]-yy[1]), float(yy[4]-yy[3])]


def check_parameter_edit():
    parameters = dict(model.DEFAULTS)
    parameters["header_slot_width"] += 0.2
    solid = model.make_bottom(parameters)
    assert solid.isValid() and len(solid.Solids()) == 1
    with tempfile.TemporaryDirectory(prefix="pico-case-parameter-") as directory:
        target = Path(directory) / "wider-slots.stl"
        solid.exportStl(str(target), tolerance=.005, angularTolerance=.05)
        mesh = trimesh.load_mesh(target)
    widths = slot_widths(mesh, parameters["case_length"], parameters["floor_thickness"])
    assert mesh.is_watertight and np.allclose(widths, [3.14, 3.14], atol=.0001)
    return {"change": "header_slot_width: 2.94 to 3.14 mm", "measured_widths_mm": widths,
            "valid_single_cad_solid": True, "watertight_mesh": True}


def check_flat_surfaces(name, shape, mesh):
    """Check CAD material coverage and STL heights in the interior regions."""
    if model.DEFAULTS["engraving_depth"] != 0 or name not in ("Bottom", "Wall-Hanger"):
        return None
    profile_name, level = ("bottom_engraving", model.DEFAULTS["floor_thickness"]) if name == "Bottom" else ("hanger_engraving", model.DEFAULTS["hanger_plate_thickness"])
    profiles = model.SKETCHES[profile_name]
    polygons = [Polygon(p["outer"], p.get("holes", [])) for p in profiles]
    depth = .3
    probes = [model.prism(p, level-depth, depth) for p in profiles]
    missing_volume = sum(max(0.0, probe.Volume()-shape.intersect(probe).Volume()) for probe in probes)
    origins = np.array([[p.representative_point().x, p.representative_point().y, level+.1] for p in polygons])
    locations, rays, _ = mesh.ray.intersects_location(origins, np.tile([0, 0, -1], (len(origins), 1)), multiple_hits=False)
    height_error = float(np.max(np.abs(locations[:, 2]-level))) if len(locations) else None
    passed = len(np.unique(rays)) == len(profiles) and height_error is not None and height_error < 1e-5 and missing_volume < 1e-5
    return {"description": "Flat, continuous interior surface", "flat_surface_z_mm": level,
            "probe_regions": len(profiles), "missing_cad_volume_mm3": missing_volume,
            "mesh_surface_height_max_error_mm": height_error, "pass": bool(passed)}


def check_stencil(name, shape, mesh):
    """Verify eleven clear apertures and their intervening material."""
    if name not in ("Top", "Opener"):
        return None
    items = stencil.geometry(model.DEFAULTS, name)
    polygons = [item["shape"] for item in items]
    profiles = stencil.profiles(model.DEFAULTS, name)
    placement = stencil.frame(model.DEFAULTS, name)
    edge_clearance = tip_clearance = None
    if name == "Top":
        thickness = model.DEFAULTS["floor_thickness"]
        mechanical_clearance = True
    else:
        thickness = model.DEFAULTS["opener_thickness"]
        boundary = Polygon(model.opener_outline(model.DEFAULTS)["outer"])
        edge_clearance = min(p.distance(boundary.boundary) for p in polygons)
        tip_clearance = 15.6587348548-max(x*placement["down"][0]+y*placement["down"][1] for p in polygons for x, y in p.exterior.coords)
        mechanical_clearance = all(boundary.contains(p) for p in polygons) and edge_clearance >= model.DEFAULTS["opener_edge_chamfer"]+placement["web"] and tip_clearance >= placement["web"]
    obstructed_volume = sum(shape.intersect(model.prism(p, 0, thickness)).Volume() for p in profiles)
    origins = np.array([[p.representative_point().x, p.representative_point().y, -.1] for p in polygons])
    locations, rays, _ = mesh.ray.intersects_location(origins, np.tile([0, 0, 1], (len(origins), 1)), multiple_hits=False)
    minimum_gap = min(a.distance(b) for i, a in enumerate(polygons) for b in polygons[i+1:])
    data = json.loads((HERE / "stencil.json").read_text())
    artwork_matches = sha256(HERE / data["artwork"]) == data["artwork_sha256"]
    roles = {role: sum(item["role"] == role for item in items) for role in ["berry", "leaf", "stem", "waveform"]}
    passed = artwork_matches and roles == {"berry": 7, "leaf": 2, "stem": 1, "waveform": 1} and len(locations) == 0 and obstructed_volume < 1e-5 and minimum_gap >= placement["web"]-1e-6 and mechanical_clearance
    return {"description": "WsprryPico through-stencil", "artwork_sha256": data["artwork_sha256"],
            "artwork_matches": artwork_matches, "opening_regions": len(profiles), "roles": roles,
            "height_mm": placement["height"], "width_mm": placement["width"], "cut_depth_mm": thickness,
            "minimum_gap_between_apertures_mm": minimum_gap, "minimum_requested_gap_mm": placement["web"],
            "opener_raw_outline_clearance_mm": edge_clearance, "opener_working_tip_clearance_mm": tip_clearance,
            "orientation": "Stem toward USB; waveform readable from outside" if name == "Top" else "Stem toward grip butt; waveform readable from upper face",
            "obstructed_aperture_cad_volume_mm3": obstructed_volume,
            "mesh_rays_blocked": len(np.unique(rays)), "pass": bool(passed)}


def check_opener_outline(shape):
    """Check the grip trim preserves the forward ramp envelope and tab."""
    p = model.DEFAULTS
    base = model.make_opener_blank(p | {"opener_grip_shortening": 0})
    trimmed = model.make_opener_blank(p)
    down = cq.Vector(-.44099376195, .89751016814, 0)
    def forward_region(start):
        plane = cq.Plane(origin=(down*start).toTuple(), normal=down.toTuple())
        return cq.Workplane(plane).box(200, 200, 200, centered=(True, True, False)).val()
    ramp = forward_region(10.92029075645)
    base_ramp, trimmed_ramp = base.intersect(ramp), trimmed.intersect(ramp)
    ramp_difference = base_ramp.cut(trimmed_ramp).Volume()+trimmed_ramp.cut(base_ramp).Volume()
    tip = forward_region(15.6587348548)
    base_tip, actual_tip = base.intersect(tip), shape.intersect(tip)
    tip_difference = base_tip.cut(actual_tip).Volume()+actual_tip.cut(base_tip).Volume()
    points = np.array(model.opener_outline(p)["outer"])
    coordinates = points @ np.array([[-.89751016814, -.44099376195], [-.44099376195, .89751016814]])
    added_outside_base = trimmed.cut(base).Volume()
    return {"rear_shortening_mm": p["opener_grip_shortening"],
            "grip_aligned_width_length_mm": np.ptp(coordinates, axis=0).tolist(),
            "added_outside_base_blank_mm3": added_outside_base,
            "blank_ramp_symmetric_difference_mm3": ramp_difference,
            "working_tip_symmetric_difference_mm3": tip_difference,
            "pass": bool(ramp_difference < 1e-5 and tip_difference < 1e-5 and added_outside_base < 1e-5)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=HERE.parent, help="Folder containing root STLs and parametric/generated STEP files")
    parser.add_argument("--report", type=Path, default=HERE / "verification.json")
    parser.add_argument("--samples", type=int, default=10000)
    parser.add_argument("--exercise-parameters", action="store_true")
    args = parser.parse_args()
    if args.samples < 1000:
        parser.error("Use at least 1000 samples per direction")
    cad_directory = args.directory / "parametric" / "generated"
    report = {
        "units": "millimetres", "alignment": "STL and STEP coordinates compared without registration or scaling.",
        "dependencies": {name: importlib.metadata.version(name) for name in
                         ["cadquery", "cadquery-ocp", "trimesh", "numpy", "shapely", "rtree", "networkx"]},
        "python": platform.python_version(),
        "inputs": {name: sha256(HERE / name) for name in ["model.py", "verify.py", "parameters.json", "profiles.json", "stencil.py", "stencil.json", "../wsprrypico-stencil.png"]},
        "mesh_export": json.loads((cad_directory/"mesh-export.json").read_text()), "parts": {},
    }
    failures, shapes = [], {}
    with tempfile.TemporaryDirectory(prefix="pico-case-step-check-") as directory:
        for name in PARTS:
            print(f"Checking {name}", flush=True)
            stl_path, step_path = args.directory/f"{name}.stl", cad_directory/f"{name}.step"
            mesh = trimesh.load_mesh(stl_path)
            shape = cq.importers.importStep(str(step_path)).val()
            shapes[name] = shape
            topology = integrity(mesh)
            bounds = shape.BoundingBox()
            cad_bounds = np.array([[bounds.xmin, bounds.ymin, bounds.zmin], [bounds.xmax, bounds.ymax, bounds.zmax]])
            extent_error = mesh.extents-np.ptp(cad_bounds, axis=0)
            bounds_error = float(np.max(np.abs(mesh.bounds-cad_bounds)))
            volume_error = float(100*(mesh.volume/shape.Volume()-1))
            fine_path = Path(directory)/f"{name}.stl"
            shape.exportStl(str(fine_path), tolerance=.002, angularTolerance=.025)
            fine_mesh = trimesh.load_mesh(fine_path)
            forward = surface_comparison(mesh, fine_mesh, args.samples)
            reverse = surface_comparison(fine_mesh, mesh, args.samples)
            surface_max = max(forward["sample_max_mm"], forward["vertex_max_mm"], reverse["sample_max_mm"], reverse["vertex_max_mm"])
            flat_check, logo_check = check_flat_surfaces(name, shape, mesh), check_stencil(name, shape, mesh)
            outline_check = check_opener_outline(shape) if name == "Opener" else None
            part = {"stl_file": f"{name}.stl", "step_file": f"parametric/generated/{name}.step",
                    "stl_sha256": sha256(stl_path), "step_sha256": sha256(step_path),
                    "mesh_integrity": topology, "cad_valid": bool(shape.isValid()), "cad_solids": len(shape.Solids()),
                    "stl_extents_mm": mesh.extents.tolist(), "step_extents_mm": np.ptp(cad_bounds, axis=0).tolist(),
                    "extent_difference_mm": extent_error.tolist(), "max_coordinate_bounds_difference_mm": bounds_error,
                    "stl_volume_mm3": float(mesh.volume), "step_volume_mm3": shape.Volume(), "volume_difference_percent": volume_error,
                    "stl_to_step_mesh": forward, "step_mesh_to_stl": reverse,
                    "flat_surfaces": flat_check, "wsprrypico_stencil": logo_check, "opener_outline": outline_check}
            checks = [topology["watertight"], topology["consistent_winding"], topology["connected_components"] == 1,
                      topology["boundary_edges"] == 0, topology["nonmanifold_edges"] == 0, topology["degenerate_faces"] == 0,
                      topology["positive_volume"], topology["finite_vertices"], part["cad_valid"], part["cad_solids"] == 1,
                      bounds_error < .01, abs(volume_error) < .1, surface_max < .02,
                      flat_check is None or flat_check["pass"], logo_check is None or logo_check["pass"],
                      outline_check is None or outline_check["pass"]]
            if name == "Bottom":
                widths = slot_widths(mesh, model.DEFAULTS["case_length"], model.DEFAULTS["floor_thickness"])
                part["header_slot_widths_mm"] = widths
                checks.append(bool(np.allclose(widths, model.DEFAULTS["header_slot_width"], atol=.0001)))
            part["pass"] = bool(all(checks))
            report["parts"][name] = part
            if not part["pass"]:
                failures.append(name)
            print(f"{name}: pass={part['pass']}, bounds error={bounds_error:.6f} mm, volume error={volume_error:+.5f}%", flush=True)
    pcb = model.box(2.85, 3.1, 8.9, 53.85, 24.1, 9.9)
    lid = shapes["Top"].rotate((0, 0, 0), (1, 0, 0), 180).translate((0, 27.2, 15.35))
    report["nominal_assembly"] = {
        "outer_extents_mm": [56.7, 27.2, 15.35], "pcb_envelope_mm": [51, 21, 1],
        "bottom_overlap_with_pcb_mm3": shapes["Bottom"].intersect(pcb).Volume(),
        "lid_overlap_with_pcb_mm3": lid.intersect(pcb).Volume(),
        "case_halves_overlap_mm3": lid.intersect(shapes["Bottom"]).Volume(),
        "scope": "Static nominal CAD. Printed fit, snap force, opener strength and actual component tolerances require physical checks.",
    }
    if args.exercise_parameters:
        report["parameter_edit_check"] = check_parameter_edit()
    if max(report["nominal_assembly"][key] for key in ["bottom_overlap_with_pcb_mm3", "lid_overlap_with_pcb_mm3", "case_halves_overlap_mm3"]) > 1e-6:
        failures.append("Nominal assembly interference")
    report["limits"] = {"max_coordinate_bounds_difference_mm": .01, "max_volume_difference_percent": .1,
                        "max_observed_bidirectional_surface_difference_mm": .02}
    report["pass"] = not failures
    args.report.write_text(json.dumps(report, indent=2)+"\n")
    if failures:
        raise SystemExit("CAD/mesh checks failed: "+", ".join(failures))
    print(f"Saved {args.report}", flush=True)


if __name__ == "__main__":
    main()
