"""Place the approved stencil and provide clearance between its apertures."""
import json
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent


def frame(parameters, part="Top"):
    if part == "Top":
        prefix, right, down = "stencil_", (0, -1), (1, 0)
    elif part == "Opener":
        prefix, right, down = "opener_stencil_", (-.89751016814, -.44099376195), (-.44099376195, .89751016814)
    else:
        raise ValueError("Stencil placement is defined only for Top and Opener")
    height = parameters[prefix+"height"]
    aspect = json.loads((HERE / "stencil.json").read_text())["aspect_width_over_height"]
    width = parameters["opener_stencil_width"] if part == "Opener" else aspect*height
    return {"height": height, "width": width,
            "center": (parameters[prefix+"center_x"], parameters[prefix+"center_y"]),
            "right": right, "down": down, "web": parameters[prefix+"min_web"]}


def geometry(parameters, part="Top"):
    data = json.loads((HERE / "stencil.json").read_text())
    placement = frame(parameters, part)
    height, size_x = placement["height"], placement["width"]/data["aspect_width_over_height"]
    cx, cy = placement["center"]
    right, down = placement["right"], placement["down"]
    width = data["aspect_width_over_height"]
    raw = [{"role": p["role"], "shape": Polygon([(cx+right[0]*(u-width/2)*size_x+down[0]*(v-.5)*height,
                                                  cy+right[1]*(u-width/2)*size_x+down[1]*(v-.5)*height)
                                                for u, v in p["outer"]])} for p in data["profiles"]]
    # Printed inside face points +Z. Reversing image U keeps the outside face
    # readable after the lid's 180-degree assembly flip; stem faces the USB end.
    priority = {"waveform": 0, "stem": 1, "leaf": 2, "berry": 3}
    def order(item):
        x, y = item["shape"].centroid.x-cx, item["shape"].centroid.y-cy
        return priority[item["role"]], x*down[0]+y*down[1], -(x*right[0]+y*right[1])
    raw.sort(key=order)
    placed = []
    for item in raw:
        polygon = item["shape"]
        if placed:
            clearance = unary_union([p["shape"] for p in placed]).buffer(placement["web"]+.005)
            polygon = polygon.difference(clearance).simplify(.001, preserve_topology=True)
        if polygon.geom_type != "Polygon" or polygon.is_empty or polygon.interiors or not polygon.is_valid:
            raise ValueError("Stencil clearance split or enclosed an aperture; reduce its size or web requirement")
        if polygon.area < item["shape"].area*.65:
            raise ValueError("Stencil clearance would remove too much of an aperture")
        placed.append({"role": item["role"], "shape": polygon,
                       "raw_area_mm2": item["shape"].area})
    minimum_gap = min(a["shape"].distance(b["shape"]) for i, a in enumerate(placed) for b in placed[i+1:])
    if minimum_gap < placement["web"]-1e-6:
        raise ValueError("Stencil apertures do not preserve the requested black web")
    return placed


def profiles(parameters, part="Top"):
    return [{"outer": list(item["shape"].exterior.coords)[:-1], "holes": []} for item in geometry(parameters, part)]


def export_svg(parameters, destination, part="Top"):
    """Export the actual CAD apertures, upright with black material/white holes."""
    placed = geometry(parameters, part)
    placement = frame(parameters, part)
    height = placement["height"]
    width = placement["width"]
    cx, cy = placement["center"]
    right, down = placement["right"], placement["down"]
    paths = []
    for item in placed:
        points = [((x-cx)*right[0]+(y-cy)*right[1]+width/2+1,
                   (x-cx)*down[0]+(y-cy)*down[1]+height/2+1) for x, y in item["shape"].exterior.coords]
        commands = "M"+" L".join(f"{x:.5f},{y:.5f}" for x, y in points)+" Z"
        paths.append(f'<path fill="white" d="{commands}"/>')
    document = (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width+2:.5f} {height+2:.5f}" '
                f'width="{width+2:.5f}mm" height="{height+2:.5f}mm">\n'
                '<title>WsprryPico stencil: white apertures, black material</title>\n'
                '<rect width="100%" height="100%" fill="black"/>\n'+"\n".join(paths)+"\n</svg>\n")
    Path(destination).write_text(document)
