#!/usr/bin/env python3
"""Parametric WsprryPico case and accessories, in millimetres.

CAD features use sketches, extrusions, ruled lofts and Boolean operations.
"""
from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path

import cadquery as cq
from shapely.geometry import Polygon
import stencil

HERE = Path(__file__).resolve().parent
DEFAULTS = json.loads((HERE / "parameters.json").read_text())
PROFILE_DATA = json.loads((HERE / "profiles.json").read_text())
SKETCHES = PROFILE_DATA["profiles"]


def box(x0, y0, z0, x1, y1, z1):
    return cq.Solid.makeBox(x1 - x0, y1 - y0, z1 - z0, cq.Vector(x0, y0, z0))


def wire(points, origin=(0, 0, 0), axes=((1, 0, 0), (0, 1, 0))):
    a, b = map(cq.Vector, axes)
    o = cq.Vector(origin)
    return cq.Wire.makePolygon([o + a * x + b * y for x, y in points], close=True)


def prism(profile, z, height, axes=((1, 0, 0), (0, 1, 0)), origin=(0, 0, 0)):
    a, b = map(cq.Vector, axes)
    n = a.cross(b)
    o = cq.Vector(origin) + n * z
    outer = wire(profile["outer"], o.toTuple(), axes)
    holes = [wire(h, o.toTuple(), axes) for h in profile.get("holes", [])]
    return cq.Solid.extrudeLinear(outer, holes, n * height)


def sketches(name, z, height, axes=((1, 0, 0), (0, 1, 0)), origin=(0, 0, 0)):
    return [prism(p, z, height, axes, origin) for p in SKETCHES[name]]


def fuse(shapes):
    result = shapes[0]
    if len(shapes) > 1:
        result = result.fuse(*shapes[1:])
    return result.clean()


def cut(shape, cutters):
    return shape.cut(*cutters).clean() if cutters else shape


def cylinder(x, y, z, radius, height):
    return cq.Solid.makeCylinder(radius, height, cq.Vector(x, y, z))


def rounded_wire(length, width, inset, radius, z):
    """Rounded rectangle with invariant corner centres under offset."""
    x0, y0, x1, y1 = inset, inset, length - inset, width - inset
    r = radius - inset
    q = math.sqrt(0.5)
    return (
        cq.Workplane("XY", origin=(0, 0, z))
        .moveTo(x0 + r, y0).lineTo(x1 - r, y0)
        .threePointArc((x1 - r + r * q, y0 + r - r * q), (x1, y0 + r))
        .lineTo(x1, y1 - r)
        .threePointArc((x1 - r + r * q, y1 - r + r * q), (x1 - r, y1))
        .lineTo(x0 + r, y1)
        .threePointArc((x0 + r - r * q, y1 - r + r * q), (x0, y1 - r))
        .lineTo(x0, y0 + r)
        .threePointArc((x0 + r - r * q, y0 + r - r * q), (x0 + r, y0))
        .close().val()
    )


def round_loft(p, levels):
    return cq.Solid.makeLoft([
        rounded_wire(p["case_length"], p["case_width"], inset, p["corner_radius"], z)
        for z, inset in levels
    ], ruled=True)


def xy_loft(profiles):
    return cq.Solid.makeLoft([wire(points, (0, 0, z)) for z, points in profiles], ruled=True)


def mounting_centres(p):
    return [
        (p["case_length"] / 2 + sx * p["pcb_mount_pitch_x"] / 2,
         p["case_width"] / 2 + sy * p["pcb_mount_pitch_y"] / 2)
        for sx in (-1, 1) for sy in (-1, 1)
    ]


def end_support(x, y, p, rear=False):
    r = p["pcb_support_radius"]
    wall = p["wall_thickness"]
    end = p["case_length"] - wall if rear else wall
    nose = x - r if rear else x + r
    # D-shaped lug, with its nose supported by a 45 degree underside ramp.
    q = cq.Workplane("XY", origin=(0, 0, p["floor_thickness"]))
    if rear:
        q = q.moveTo(end, y-r).lineTo(x, y-r).threePointArc((nose, y), (x, y+r)).lineTo(end, y+r)
    else:
        q = q.moveTo(end, y+r).lineTo(x, y+r).threePointArc((nose, y), (x, y-r)).lineTo(end, y-r)
    lug = q.close().extrude(p["pcb_support_height"] - p["floor_thickness"]).val()
    intercept = p["pcb_support_root_height"] - (p["case_length"] / 2 - p["pcb_mount_pitch_x"] / 2)
    underside = {"outer": [[0, -1], [10, -1], [10, 10 + intercept], [0, intercept]], "holes": []}
    ramp = prism(underside, 0, p["case_width"] + 2, ((1,0,0),(0,0,1)), (0,p["case_width"]+1,0))
    if rear:
        ramp = ramp.mirror("YZ", (p["case_length"]/2, 0, 0))
    return cut(lug, [ramp])


def latch_profile(p, lid):
    name = "lid_latch_rib_section" if lid else "bottom_latch_recess_section"
    dz = p["lid_latch_z"] - 3.6 if lid else p["bottom_latch_z"] - 11.75
    return [{"outer": [[y, z + dz] for y, z in q["outer"]], "holes": []} for q in SKETCHES[name]]


def latches(p, lid=False):
    # Long, constant-radius snap sections are exposed as independent sketches.
    result = []
    for prof in latch_profile(p, lid):
        one = prism(prof, 0, p["latch_length"], ((0, 1, 0), (0, 0, 1)), (p["latch_start_x"], 0, 0))
        result.extend([one, one.mirror("XZ", (0, p["case_width"] / 2, 0))])
    if not lid:
        import numpy as np
        cap_wires=[]
        for section in PROFILE_DATA["bottom_latch_end_sections"]:
            points=np.array(section["profile"]["outer"])
            zmin,zmax=points[:,1].min(),points[:,1].max()
            zz=np.linspace(zmax,zmin,49)
            # The front of the recess is single-valued in Z; the back is Y=1.3.
            order=np.argsort(points[:,1]);zs=points[order,1];ys=points[order,0]
            unique=np.unique(zs);ys=np.array([max(ys[zs==z])for z in unique])
            yy=np.interp(zz,unique,ys)
            yz=np.column_stack([yy,zz+p["bottom_latch_z"]-11.75])
            x=p["latch_start_x"]+(section["x"]-13.35)*p["latch_end_extension"]
            cap_wires.append(wire(yz.tolist(),(x,0,0),((0,1,0),(0,0,1))))
        cap=cq.Solid.makeLoft(cap_wires,ruled=True)
        other=cap.mirror("YZ",(p["latch_start_x"]+p["latch_length"]/2,0,0))
        result.extend([cap,other,cap.mirror("XZ",(0,p["case_width"]/2,0)),other.mirror("XZ",(0,p["case_width"]/2,0))])
    return result


def make_bottom(p):
    L, W = p["case_length"], p["case_width"]
    floor, shoulder, rim = p["floor_thickness"], p["bottom_shoulder_height"], p["bottom_rim_height"]
    outside = round_loft(p, [(0, p["outer_bottom_chamfer"]), (p["outer_bottom_chamfer"], 0), (shoulder, 0)])
    crown = round_loft(p, [(shoulder, p["rim_outer_inset"]), (rim-p["rim_top_chamfer"], p["rim_outer_inset"]), (rim, p["rim_outer_inset"]+p["rim_top_chamfer"])])
    body = fuse([outside, crown])
    slope_top = p["inner_slope_start"] + p["end_pocket_inset"] - p["wall_thickness"]
    lower_cavity = round_loft(p, [(floor, p["wall_thickness"]+p["inner_floor_chamfer"]), (floor+p["inner_floor_chamfer"], p["wall_thickness"]), (p["inner_slope_start"], p["wall_thickness"]), (slope_top, p["end_pocket_inset"])])
    upper_cavity = round_loft(p, [(slope_top, p["end_pocket_inset"]), (rim+1, p["end_pocket_inset"])])
    # The long sides have an additional 0.4 mm inward bevel above the PCB seat.
    y = p["side_pocket_inset"]
    slab = prism({"outer": [[p["end_pocket_inset"], slope_top], [W-p["end_pocket_inset"], slope_top], [W-y, slope_top+y-p["end_pocket_inset"]], [W-y, rim+2], [y, rim+2], [y, slope_top+y-p["end_pocket_inset"]]], "holes": []}, 0, L+2, ((0,1,0),(0,0,1)), (-1,0,0))
    upper_cavity = upper_cavity.intersect(slab)
    body = cut(body, [lower_cavity, upper_cavity])
    for x, yy in mounting_centres(p):
        body = fuse([body, end_support(x, yy, p, rear=x>L/2)])
    for x0 in (10.75, L-13.95):
        rib = sketches("bottom_side_rib", 0, 3.2, ((0,1,0),(0,0,1)), (x0,0,0))[0]
        body=fuse([body,rib,rib.mirror("XZ", (0,W/2,0))])
    body=fuse([body,box(L-2.4,9.65,8.9,L,17.55,10.95)])
    # Header slots are centered on the two 17.78 mm separated pin rows.
    slots=[]
    for yy in (W/2-p["header_row_pitch"]/2, W/2+p["header_row_pitch"]/2):
        slots.append(box(L/2-p["header_slot_length"]/2, yy-p["header_slot_width"]/2, -.1, L/2+p["header_slot_length"]/2, yy+p["header_slot_width"]/2, floor+.01))
    body = cut(body, slots)
    # Upper USB relief leaves the front-wall step at x=1.3 mm.
    usb = {"outer": [[11.15,9.35],[16.05,9.35],[17.65,10.95],[17.65,rim+1],[9.55,rim+1],[9.55,10.95]], "holes": []}
    body = cut(body, [prism(usb, 0, p["end_pocket_inset"]-p["rim_outer_inset"]+.01, ((0,1,0),(0,0,1)), (p["rim_outer_inset"],0,0)), box(L-2.41,9.65,10.95,L+.1,17.55,rim+1)])
    # Open the front of the tall rim while retaining the outer wall shoulder.
    body = cut(body,[box(-.1,9.55,shoulder,1.31,17.65,rim+1)])
    window=sketches("bottom_rear_post_window",shoulder,rim-shoulder+.1)[0]
    body=cut(body,[window,window.mirror("XZ",(0,W/2,0))])
    # Teardrop cable opening in the opposite short wall.
    body = cut(body, sketches("bottom_cable_hole", 0, 3.0, ((0,1,0),(0,0,1)), (L-2.5,0,0)))
    # Small release recesses on both long edges.
    body = cut(body,[box(L/2-3,-.1,shoulder-1,L/2+3,1.31,shoulder+.01),box(L/2-3,W-1.31,shoulder-1,L/2+3,W+.1,shoulder+.01)])
    body = cut(body,latches(p))
    # Counterbored mounting holes in the base: 0.2 mm pilot web is retained.
    for x in (L/2-20,L/2+20):
        pilot = cut(cylinder(x,W/2,-.1,1.3,.31), [box(x-.5,W/2-1.4,-.2,x+.5,W/2+1.4,.22)])
        cutters=[pilot,cq.Solid.makeCone(1.3,2.3,1.0,cq.Vector(x,W/2,.2))]
        body=cut(body,cutters)
    if p["engraving_depth"] > 0:
        body=cut(body,sketches("bottom_engraving",floor-p["engraving_depth"],p["engraving_depth"]+.01))
    return body.clean()


def make_lid(p):
    L,W,H=p["case_length"],p["case_width"],p["lid_height"]
    outside=round_loft(p,[(0,p["outer_bottom_chamfer"]),(p["outer_bottom_chamfer"],0),(H,0)])
    cavity=round_loft(p,[(p["floor_thickness"],p["wall_thickness"]+p["inner_floor_chamfer"]),(p["floor_thickness"]+p["inner_floor_chamfer"],p["wall_thickness"]),(H+1,p["wall_thickness"])])
    body=cut(outside,[cavity])
    # Build the continuous lid skin before cutting the stencil apertures.
    body=cut(body,sketches("lid_flexure_slot",-.01,p["floor_thickness"]+.02))
    # USB aperture and far-end access notch.
    body=cut(body,[box(-.1,10.0,3.2,1.21,17.2,H+1),box(L-2.41,9.6,2.4,L+.1,17.6,H+1)])
    # The lid clamps the board at the four mounting positions.
    for x,y in mounting_centres(p):
        if x<L/2:
            post=cylinder(x,y,p["floor_thickness"],p["lid_post_radius"],H-p["floor_thickness"])
            root=cq.Solid.makeCone(p["lid_post_radius"]+.6,p["lid_post_radius"],.6,cq.Vector(x,y,p["floor_thickness"]))
            body=fuse([body,post,root])
        else:
            prof = SKETCHES["lid_rear_post"][0]
            pad = prism(prof, p["floor_thickness"], p["lid_rear_post_height"]-p["floor_thickness"])
            if y > W/2:
                pad = pad.mirror("XZ", (0,W/2,0))
            body=fuse([body,pad])
    body=fuse([body,cylinder(p["bootsel_x"],p["bootsel_y_print"],p["floor_thickness"],p["bootsel_plunger_radius"],p["bootsel_plunger_height"]-p["floor_thickness"])])
    # USB socket support, and the tapered split LED guide.
    body=fuse([body,box(2.85,9.6,p["floor_thickness"],6.85,17.6,p["usb_lid_stop_height"])])
    body=fuse([body,box(1.2,10,1.2,2.85,17.2,2.764)])
    sleeve=fuse([cylinder(7.65,19.28,1.2,1.95,p["led_guide_height"]-1.2),cq.Solid.makeCone(2.95,1.95,1,cq.Vector(7.65,19.28,1.2))])
    body=fuse([body,sleeve,box(L-2.4,9.6,1.2,L,17.6,2.4)])
    bore_top=p["led_bore_bottom_radius"]-p["led_guide_height"]*math.tan(math.radians(p["led_bore_taper_degrees"]))
    body=cut(body,[cq.Solid.makeCone(p["led_bore_bottom_radius"],bore_top,p["led_guide_height"]+.001,cq.Vector(7.65,19.28,0)),box(7.65,19.07,.4,10.781,19.49,p["led_guide_height"]+.1)])
    body=fuse([body,*latches(p,lid=True)])
    body=cut(body,[box(L/2-3,-.1,H-.2,L/2+3,1.21,H+.1),box(L/2-3,W-1.21,H-.2,L/2+3,W+.1,H+.1)])
    body=cut(body,[prism(profile,-.01,p["floor_thickness"]+.02) for profile in stencil.profiles(p)])
    return body.clean()


def make_hanger(p):
    # Plate outline is an editable sketch. Circular mounting holes are separate.
    outline={"outer":SKETCHES["hanger_plate_outline"][0]["outer"],"holes":[]}
    body=prism(outline,0,p["hanger_plate_thickness"])
    for x in (29.55-p["hanger_screw_pitch"]/2,29.55+p["hanger_screw_pitch"]/2):
        body=cut(body,[cylinder(x,16.718094,-.01,p["hanger_screw_radius"],.62),cq.Solid.makeCone(p["hanger_screw_radius"],p["hanger_countersink_radius"],1.5,cq.Vector(x,16.718094,.6)),cylinder(x,16.718094,2.1,p["hanger_countersink_radius"],.6)])
    height_delta=p["hanger_clip_height"]-17.95
    profile={"outer":[[y,z+height_delta if z>=16.45 else z]for y,z in SKETCHES["hanger_side_clip_section"][0]["outer"]],"holes":[]}
    clip=prism(profile,0,p["hanger_clip_width"],((0,1,0),(0,0,1)),(29.55-p["hanger_clip_width"]/2,0,0))
    for m in PROFILE_DATA["hanger_clip_mitres"]:
        normal=cq.Vector(m["normal"]).normalized()
        offset=m["offset"]+normal.z*height_delta+abs(normal.x)*(p["hanger_clip_width"]-12)/2
        plane=cq.Plane(origin=(normal*offset).toTuple(), normal=normal.toTuple())
        cutter=cq.Workplane(plane).box(200,200,200,centered=(True,True,False)).val()
        clip=cut(clip,[cutter])
    def tetrahedron(points):
        vv=[cq.Vector(v)for v in points];centre=sum(vv,cq.Vector())*.25;faces=[]
        for ids in [(0,1,2),(0,1,3),(0,2,3),(1,2,3)]:
            v=[vv[i]for i in ids]
            if (v[1]-v[0]).cross(v[2]-v[0]).dot(sum(v,cq.Vector())/3-centre)<0:v.reverse()
            faces.append(cq.Face.makeFromWires(cq.Wire.makePolygon(v,close=True)))
        return cq.Solid.makeSolid(cq.Shell.makeShell(faces))
    foot=tetrahedron([(22.05,4.6181,2.6),(23.55,3.1181,2.6),(23.55,4.6181,2.6),(23.55,3.1181,4.1)])
    foot2=foot.mirror("YZ",(29.55,0,0))
    body=fuse([body,clip,foot,foot2,clip.mirror("XZ",(0,16.7181,0)),foot.mirror("XZ",(0,16.7181,0)),foot2.mirror("XZ",(0,16.7181,0))])
    # Quarter-circle ears: a conical inner root flare and an outer top bevel.
    def ear_wire(inner,z):
        cx,cy,outer=4.2,6.1181,4.2
        q=math.sqrt(.5);extension=outer-inner
        return (cq.Workplane("XY",origin=(0,0,z)).moveTo(0,cy)
            .threePointArc((cx-outer*q,cy-outer*q),(cx,cy-outer))
            .lineTo(cx+extension,cy-inner).lineTo(cx,cy-inner)
            .threePointArc((cx-inner*q,cy-inner*q),(cx-inner,cy))
            .lineTo(cx-inner,cy+extension).close().val())
    ear=fuse([cq.Solid.makeLoft([ear_wire(1.5,2.6),ear_wire(3.0,4.1)],ruled=True),cq.Solid.extrudeLinear(ear_wire(3,4.1),[],cq.Vector(0,0,2))])
    outer_cap=fuse([cylinder(4.2,6.1181,2.5,4.2,3.0),cq.Solid.makeCone(4.2,3.6,.6,cq.Vector(4.2,6.1181,5.5))])
    ear=ear.intersect(outer_cap)
    stop=prism(SKETCHES["hanger_stop_xz"][0],0,10,((1,0,0),(0,0,1)),(0,21.7181,0))
    for n,d in [((0,-1,1),-9.1181),((0,1,1),24.3181),((1,-1,0),44.6819),((1,1,0),78.1181)]:
        normal=cq.Vector(n);offset=d/normal.Length;normal=normal.normalized()
        plane=cq.Plane(origin=(normal*offset).toTuple(),normal=normal.toTuple())
        stop=cut(stop,[cq.Workplane(plane).box(200,200,200,centered=(True,True,False)).val()])
    ear_foot=cq.Solid.extrudeLinear(ear_wire(1.5,0),[],cq.Vector(0,0,2.6))
    body=fuse([body,ear_foot,ear_foot.mirror("XZ",(0,16.7181,0)),ear,ear.mirror("XZ",(0,16.7181,0)),stop])
    if p["engraving_depth"] > 0:
        body=cut(body,sketches("hanger_engraving",p["hanger_plate_thickness"]-p["engraving_depth"],p["engraving_depth"]+.01))
    return body.clean()


def opener_outline(p):
    """Shorten the rear grip while retaining the forward envelope."""
    outline = SKETCHES["opener_blank_outline"][0]
    dx, dy = -.44099376195, .89751016814
    rear = min(x*dx+y*dy for x, y in outline["outer"])
    shortening = p["opener_grip_shortening"]
    if not 0 <= shortening < -rear:
        raise ValueError("Opener grip shortening must leave the rear outline behind T=0")
    points = []
    for x, y in outline["outer"]:
        along = x*dx+y*dy
        shift = shortening*min(along, 0)/rear
        points.append([x+dx*shift, y+dy*shift])
    # Intersect with the reference outline so moving the rear vertices cannot
    # widen the adjacent sloping edges. The edit only removes grip material.
    trimmed = Polygon(points).intersection(Polygon(outline["outer"]))
    if trimmed.geom_type != "Polygon" or not trimmed.is_valid or trimmed.interiors:
        raise ValueError("Opener shortening must retain one continuous grip outline")
    return {"outer": list(trimmed.exterior.coords)[:-1], "holes": []}


def make_opener_blank(p):
    """Unperforated grip, bevels, ramp and working tab."""
    profile=opener_outline(p)
    raw=prism(profile,0,p["opener_thickness"])
    # Leave the thin working tab's perimeter square; bevel the main grip only.
    direction=cq.Vector(-.44099376195,.89751016814,0)
    raw=cq.Workplane(obj=raw).faces(">Z or <Z").edges().chamfer(p["opener_edge_chamfer"]).val()
    normal=cq.Vector(-.15985963630,.32534620993,.93198430264).normalized()
    distance=6.84774254102
    plane=cq.Plane(origin=(normal*distance).toTuple(),normal=normal.toTuple())
    wedge=cq.Workplane(plane).box(200,200,200,centered=(True,True,False)).val()
    tip_plane=cq.Plane(origin=(direction*15.6587348548).toTuple(),normal=direction.toTuple())
    front=cq.Workplane(tip_plane).box(200,200,200,centered=(True,True,False)).val()
    tab=prism(profile,0,p["opener_tip_height"]).intersect(front)
    raw=fuse([cut(raw,[wedge]),tab])
    return raw.clean()


def make_opener(p):
    raw=make_opener_blank(p)
    raw=cut(raw,[prism(q,-.01,p["opener_thickness"]+.02)for q in stencil.profiles(p,"Opener")])
    return raw.clean()


BUILDERS={"Bottom":make_bottom,"Top":make_lid,"Wall-Hanger":make_hanger,"Opener":make_opener}


def export_step(shape, destination):
    """Write a STEP solid with blank optional author and authorization fields."""
    cq.exporters.export(shape,str(destination))
    document=destination.read_text()
    pattern=r"(FILE_NAME\('[^']*','[^']*',)\([^)]*\),\([^)]*\),('[^']*','[^']*'\s*,)'[^']*'(\);)"
    document,count=re.subn(pattern,lambda m:m[1]+"(''),(''),"+m[2]+"''"+m[3],document,count=1)
    if count!=1:
        raise RuntimeError("Unexpected STEP header structure")
    destination.write_text(document)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parameters",type=Path,default=HERE/"parameters.json")
    parser.add_argument("--output",type=Path,default=HERE.parent,
                        help="Case output folder: root STLs, with CAD exports under parametric/generated")
    parser.add_argument("--part",choices=BUILDERS)
    args=parser.parse_args()
    supplied=json.loads(args.parameters.read_text())
    unknown=set(supplied)-set(DEFAULTS)
    if unknown:
        raise ValueError("Unknown parameter names: "+", ".join(sorted(unknown)))
    p=DEFAULTS | supplied
    if any(not isinstance(v,(int,float)) or not math.isfinite(v) or v<0 or (v==0 and k not in ("engraving_depth","opener_grip_shortening")) for k,v in p.items()):
        raise ValueError("Parameters must be finite and positive; engraving_depth and opener_grip_shortening may also be zero")
    if not 0<p["wall_thickness"]<p["end_pocket_inset"]<p["corner_radius"]:
        raise ValueError("Require 0 < wall thickness < end pocket inset < corner radius")
    args.output.mkdir(parents=True,exist_ok=True)
    cad_output=args.output/"parametric"/"generated"
    cad_output.mkdir(parents=True,exist_ok=True)
    notes_path=cad_output/"mesh-export.json"
    export_notes=json.loads(notes_path.read_text()) if notes_path.exists() else {}
    for name,build in BUILDERS.items():
        if args.part and args.part!=name:continue
        print(f"Building {name}",flush=True)
        shape=build(p)
        if not shape.isValid() or len(shape.Solids())!=1:
            raise RuntimeError(f"{name}: invalid CAD shape or {len(shape.Solids())} separate solids")
        export_step(shape,cad_output/f"{name}.step")
        shape.exportStl(str(args.output/f"{name}.stl"),tolerance=p["mesh_linear_tolerance"],angularTolerance=p["mesh_angular_tolerance"],ascii=False)
        # Very thin analytic-versus-traced curve seams can survive STEP meshing.
        # Weld only failed meshes, at a 0.0001 mm coordinate-key precision;
        # never fill holes.
        import trimesh
        mesh=trimesh.load_mesh(args.output/f"{name}.stl")
        before=len(mesh.faces)
        before_vertices=mesh.vertices.copy()
        weld_movement=0.0
        welded=False
        if not mesh.is_watertight:
            mesh.merge_vertices(digits_vertex=4)
            mesh.update_faces(mesh.nondegenerate_faces())
            mesh.remove_unreferenced_vertices()
            from scipy.spatial import cKDTree
            weld_movement=float(cKDTree(mesh.vertices).query(before_vertices)[0].max())
            if weld_movement>.0002:
                raise RuntimeError(f"{name}: mesh welding moved a vertex too far")
            welded=True
        if not mesh.is_watertight or not mesh.is_winding_consistent or len(mesh.split(only_watertight=False))!=1:
            raise RuntimeError(f"{name}: exported STL failed integrity checks")
        if welded:
            mesh.export(args.output/f"{name}.stl")
        if name in ("Top","Opener"):
            stencil.export_svg(p,cad_output/f"{name}-stencil.svg",name)
        export_notes[name]={"vertex_key_precision_mm":.0001 if welded else None,"welded":welded,"raw_triangles":before,"final_triangles":len(mesh.faces),"max_weld_vertex_movement_mm":weld_movement}
        print(f"{name}: valid CAD solid and watertight mesh, {shape.Volume():.6f} mm^3",flush=True)
    notes_path.write_text(json.dumps(export_notes,indent=2)+"\n")


if __name__=="__main__":
    main()
