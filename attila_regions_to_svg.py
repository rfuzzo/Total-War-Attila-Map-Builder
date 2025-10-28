#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Extract clean vector province/region shapes from Total War: Attila lookup image.
-------------------------------------------------------------------------------
Usage:
    python attila_regions_to_svg.py main_attila_lookup.tga regions.csv \
        --outdir out_svg --tolerance 1 --simplify 0.3 --min-area 80 --skip-sea \
        --supersample 2
-------------------------------------------------------------------------------
Dependencies:
    pip install pillow opencv-python numpy
-------------------------------------------------------------------------------
"""

import argparse, csv, json
from pathlib import Path
import numpy as np
import cv2
from PIL import Image

# ------------------------------------------------------------
#  Input data paths
# ------------------------------------------------------------
regions_csv = "data/regions.csv"
regions_units = "data/start_pos_regions_to_unit_resources.csv"
lookup_image = "data/main_attila_lookup.tga"
units_folder = ["data/units"]

# ------------------------------------------------------------
#  Helper: load TGA/PNG via Pillow (handles alpha properly)
# ------------------------------------------------------------
def load_lookup(path: Path):
    im = Image.open(path).convert("RGBA")
    arr = np.array(im)
    h, w = arr.shape[:2]
    # Convert RGBA -> BGRA for OpenCV
    #img_bgra = arr[:, :, ::-1].copy()
    #return img_bgra, w, h
    return arr, w, h

# ------------------------------------------------------------
#  CSV mapping: 
#   start_pos_regions_to_unit_resources.csv:    region -> unit resource
# ------------------------------------------------------------
def load_auxilia_mapping(csv_path):
    mapping = {}
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=",")
        for row in reader:
            # csv with columns: Key, resource
            # one region can can have multiple resources, in a new line
            region = row.get("Key", "").strip()
            resource = row.get("Resource", "").strip()
            if region and resource:
                if region not in mapping:
                    mapping[region] = []
                mapping[region].append(resource)
    return mapping

# ------------------------------------------------------------
#  CSV mapping: 
#   _rex_other_main_units.tsv:                  unit resource -> unit
# ------------------------------------------------------------
def load_unit_mappings(folder_path):
    mapping = {}

    csv_files = []
    for folder in folder_path:
        p = Path(folder)
        csv_files.extend(p.glob("*.tsv"))
    
    for csv_path in csv_files:
        with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                # csv with columns: unit, region_unit_resource_requirement
                resource = row.get("region_unit_resource_requirement", "").strip()
                unit = row.get("unit", "").strip()
                if resource and unit:
                    if resource not in mapping:
                        mapping[resource] = []
                    mapping[resource].append(unit)
    return mapping

# ------------------------------------------------------------
#  CSV mapping: colour_group hex -> key
# ------------------------------------------------------------
def load_mapping(csv_path, skip_sea=False):
    mapping = {}
    with open(csv_path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter=",")
        for row in reader:
            # skip if not starts with "att_"
            if not row.get("key", "").startswith("att_"):
                continue
            # skip out of bound (match att_reg_terra_incognita)
            if row.get("key", "") == "att_reg_terra_incognita":
                continue

            hexcol = (row.get("colour_group") or "").strip()
            if len(hexcol) != 6:
                continue
            r, g, b = int(hexcol[0:2], 16), int(hexcol[2:4], 16), int(hexcol[4:6], 16)
            a = 255
            if skip_sea and (row.get("is_sea", "").lower() == "true"):
                continue
            mapping[(r, g, b, a)] = row["key"]
            #mapping[(b, g, r, a)] = row["key"]
    return mapping


# ------------------------------------------------------------
#  Contour extraction (anti-aliased & hole-aware)
# ------------------------------------------------------------
def find_contours(img_bgra, color_rgba, tol=1, min_area=40, use_alpha=False, alpha_min=1):
    r, g, b, a = color_rgba
    bgr = img_bgra[:, :, :3]

    lower = np.array([b - tol, g - tol, r - tol], dtype=np.int16)
    upper = np.array([b + tol, g + tol, r + tol], dtype=np.int16)
    lower = np.clip(lower, 0, 255).astype(np.uint8)
    upper = np.clip(upper, 0, 255).astype(np.uint8)
    mask = cv2.inRange(bgr, lower, upper)

    if use_alpha:
        a_chan = img_bgra[:, :, 3]
        mask_alpha = cv2.inRange(a_chan, alpha_min, 255)
        mask = cv2.bitwise_and(mask, mask_alpha)

     # Light cleanup to keep edges but remove pepper noise
    if min_area > 0:
        k = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3))
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, k, iterations=1)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, k, iterations=1)

    # Keep hierarchy so holes can be rendered with fill-rule="evenodd"
    contours, hierarchy = cv2.findContours(mask, cv2.RETR_CCOMP, cv2.CHAIN_APPROX_TC89_L1)
    if hierarchy is None:
        return [], None

    contours = [c for c in contours if cv2.contourArea(c) >= min_area]
    return contours, hierarchy


# ------------------------------------------------------------
#  Simplify & convert to SVG path
# ------------------------------------------------------------
def path_d_from_contours(contours, simplify_pct=0.3, scale_divisor=1.0):
    parts = []
    for cnt in contours:
        # TODO this crashes
        #cnt = cnt / scale_divisor

        # compute contour perimeter
        peri = cv2.arcLength(cnt, True)

        # simplify the contour using Douglas–Peucker algorithm
        eps = peri * (simplify_pct / 100.0)
        approx = cv2.approxPolyDP(cnt, eps, True).reshape(-1, 2)

        if len(approx) < 3:
            continue  # too small to form a closed area

        # start the path with Move-to
        segs = [f"M{approx[0,0]:.1f} {approx[0,1]:.1f}"]

        # add each edge as Line-to
        segs += [f"L{x:.1f} {y:.1f}" for x, y in approx[1:]]

        # close the path
        segs.append("Z")

        # join into one compact string
        parts.append(" ".join(segs))

    # return one big SVG "d" string, joining multiple disjoint polygons
    return " ".join(parts)




# ------------------------------------------------------------
#  Main
# ------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="out_svg")
    ap.add_argument("--skip-svg", action="store_true")
    ap.add_argument("--tolerance", type=int, default=1)
    ap.add_argument("--simplify", type=float, default=0.3)
    ap.add_argument("--min-area", type=int, default=80)
    ap.add_argument("--skip-sea", action="store_true")
    ap.add_argument("--supersample", type=int, default=1,
                    help="Scale mask up N× before contouring (1=off, 2=default for smooth edges)")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(exist_ok=True)

    # DATA

    # regions -> unit resources
    resource_to_region = load_auxilia_mapping(regions_units)
    print(f"Loaded {len(resource_to_region)} resource to region mappings from {regions_units}")
    
    # unit resources -> units
    unit_resource_to_unit = load_unit_mappings(units_folder)
    print(f"Loaded {len(unit_resource_to_unit)} unit resource to unit mappings from {units_folder}")

    # now we can map region -> [unit resources] -> [units]
    # each regions should have a list of resources, each resources a list of units
    region_data = {}
    for region, resources in resource_to_region.items():
        for resource in resources:
            units = unit_resource_to_unit.get(resource, [])
            if region not in region_data:
                region_data[region] = {"resources": {}}
            region_data[region]["resources"][resource] = units

    # save to json
    (outdir / "region_data.json").write_text(
        json.dumps(region_data, indent=2), encoding="utf-8")
    print(f"✓ Wrote region data mapping → {outdir/'region_data.json'}")

    # ------------------------------------------------------------

    # skip SVG generation if requested
    if args.skip_svg:
        return

    # CONTOURS
    mapping = load_mapping(regions_csv, skip_sea=args.skip_sea)
    print(f"Loaded {len(mapping)} region color mappings from {regions_csv}")

    # this is in RGBA format
    rgba, w, h = load_lookup(lookup_image)
    colors_present = {tuple(map(int, c)) for c in np.unique(rgba.reshape(-1, 4), axis=0)}
    to_process = [c for c in colors_present if c in mapping]

    print(f"Processing {len(to_process)} regions...")
    # now, opencv needs BGRA, but we have RGBA
    img = cv2.cvtColor(rgba, cv2.COLOR_RGBA2BGRA)

    paths, meta = [], []
    for i, color in enumerate(to_process, 1):
        key = mapping[color]

        # optional supersampling for smooth edges
        if args.supersample > 1:
            big = cv2.resize(img, None, fx=args.supersample, fy=args.supersample,
                             interpolation=cv2.INTER_NEAREST)
            
            
            cnts, _ = find_contours(big, color, args.tolerance, args.min_area * args.supersample)
            scale_div = args.supersample
        else:
            cnts, _ = find_contours(img, color, args.tolerance, args.min_area)
            scale_div = 1.0

        if not cnts:
            continue

        d = path_d_from_contours(cnts, args.simplify, scale_divisor=scale_div)
        if not d:
            continue

        paths.append(f'<path id="{key}" class="province" d="{d}"/>')

        # bbox + area
        xs, ys, area = [], [], 0.0
        for c in cnts:
            area += cv2.contourArea(c) / (scale_div**2)
            pts = (c / scale_div).reshape(-1, 2)
            xs.extend(pts[:, 0].tolist()); ys.extend(pts[:, 1].tolist())
        bbox = (min(xs), min(ys), max(xs), max(ys))
        meta.append({
            "id": key,
            "name": key,
            "color": {"r": color[0], "g": color[1], "b": color[2], "a": color[3]},
            "area_px": area,
            "bbox": {"x0": bbox[0], "y0": bbox[1], "x1": bbox[2], "y1": bbox[3]}
        })

        if i % 25 == 0:
            print(f"  {i}/{len(to_process)} done...")

    svg = (
        f'<?xml version="1.0" encoding="UTF-8"?>\n'
        f'<svg xmlns="http://www.w3.org/2000/svg" '
        f'viewBox="0 0 {w} {h}" preserveAspectRatio="xMidYMid meet">\n'
        f'  <g id="provinces" fill-rule="evenodd" '
        f'stroke="rgba(255,255,255,0.35)" stroke-width="1">\n'
        + "\n".join("    "+p for p in paths) +
        "\n  </g>\n</svg>\n"
    )
    (outdir / "provinces.svg").write_text(svg, encoding="utf-8")
    (outdir / "provinces.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"✓ Wrote {len(paths)} shapes → {outdir/'provinces.svg'}")


if __name__ == "__main__":
    main()
