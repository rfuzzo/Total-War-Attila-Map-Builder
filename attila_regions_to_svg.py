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

lookup_image = "data/main_attila_lookup.tga"

units_folder = ["data/units"]
units_to_groupings_military_permissions_tables = ["data/units_to_groupings_military_permissions_tables"]
building_units_allowed_tables = ["data/building_units_allowed_tables"]

regions_csv = "data/regions.csv"
regions_units = "data/_rex_start_pos_regions_to_unit_resources.csv"
lookup_factions = "data/_rex_factions.tsv"
lookup_buildings = "data/building_culture_variants.tsv"

# location TSV paths and prefixes
loc_sources = {
    "units": {
        "metadata": "data/loc/__land_units.loc.tsv",
        "prefix": "land_units_onscreen_name_"
    },
    "factions": {
        "metadata": "data/loc/_factions.loc.tsv",
        "prefix": "factions_screen_name_"
    },
    "regions": {
        "metadata": "data/loc/_regions.loc.tsv",
        "prefix": "regions_onscreen_"
    }
}

# ------------------------------------------------------------
#  TSV mapping: building -> unit
# ------------------------------------------------------------
def load_building_unit_mapping(folder_path):
    mapping = {}

    files = []
    for folder in folder_path:
        p = Path(folder)
        files.extend(p.glob("*.tsv"))

    for path in files:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                # csv with columns: building, unit
                building = row.get("building", "").strip()
                unit = row.get("unit", "").strip()
                # one building can can have multiple units, in a new line
                if building and unit:
                    if building not in mapping:
                        mapping[building] = []
                    mapping[building].append(unit)

    return mapping

# ------------------------------------------------------------
#  TSV mapping:  subculture -> building
# ------------------------------------------------------------
def load_buildings_mapping(path):
    mapping = {}
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            # csv with columns: building, subculture
            building = row.get("building", "").strip()
            subculture = row.get("subculture", "").strip()
            if building and subculture:
                if subculture not in mapping:
                    mapping[subculture] = []
                mapping[subculture].append(building)
    return mapping

# ------------------------------------------------------------
#  TSV mapping: 
#  all loc tsvs:                  key -> text
# ------------------------------------------------------------
def load_loc_tsv(path, mapping, prefix):
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            # csv with columns: key, text
            key = row.get("key", "").strip()
            text = row.get("text", "").strip()
            if key and text:
                # strip prefix from key
                if key.startswith(prefix):
                    key = key[len(prefix):]
                    mapping[key] = text

    return mapping

# ------------------------------------------------------------
#  TSV mapping: 
#  _rex_factions.tsv:                  faction -> (military_group, subculture)
# ------------------------------------------------------------
def load_faction_mapping(path):
    mapping = {}
    with open(path, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, delimiter="\t")
        for row in reader:
            # csv with columns: key, military_group
            faction = row.get("key", "").strip()

            # skip if starts with "bel_fact_"
            if faction.startswith("bel_fact_"):
                continue
            # skip if starts with "cha_fact_"
            if faction.startswith("cha_fact_"):
                continue
            # skip if starts with "att_fact_separatist_"
            if faction.startswith("att_fact_separatist_"):
                continue
            # skip if starts with "att_fact_rebel_"
            if faction.startswith("att_fact_rebel_"):
                continue

            military_group = row.get("military_group", "").strip()
            subculture = row.get("subculture", "").strip()
            
            # store all
            if faction and military_group and subculture:
                mapping[faction] = (military_group, subculture)
    return mapping

# ------------------------------------------------------------
#  TSV mapping:  unit -> [military_group]
# ------------------------------------------------------------
def load_unit_military_mapping(folder_path):
    mapping = {}

    files = []
    for folder in folder_path:
        p = Path(folder)
        files.extend(p.glob("*.tsv"))

    for path in files:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                # csv with columns: unit, military_group
                unit = row.get("unit", "").strip()
                military_group = row.get("military_group", "").strip()
                if unit and military_group:
                    if unit not in mapping:
                        mapping[unit] = []
                    mapping[unit].append(military_group)
    return mapping

# ------------------------------------------------------------
#  TSV mapping:  unit resource -> [unit]
# ------------------------------------------------------------
def load_unit_mappings(folder_path):
    mapping = {}
    unit_alias = {}

    files = []
    for folder in folder_path:
        p = Path(folder)
        files.extend(p.glob("*.tsv"))
    
    for path in files:
        with open(path, newline="", encoding="utf-8", errors="replace") as f:
            reader = csv.DictReader(f, delimiter="\t")
            for row in reader:
                # csv with columns: unit, region_unit_resource_requirement
                resource = row.get("region_unit_resource_requirement", "").strip()
                unit = row.get("unit", "").strip()
                alias = row.get("land_unit", "").strip()

                if resource and alias:
                    if resource not in mapping:
                        mapping[resource] = []
                    mapping[resource].append(unit)

                if resource and unit and alias:
                    if alias != unit:
                        unit_alias[unit] = alias

    return mapping, unit_alias

# ------------------------------------------------------------
#  CSV mapping:  region -> [unit resource]
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

    # TODO MB: check
    # if use_alpha:
    #     a_chan = img_bgra[:, :, 3]
    #     mask_alpha = cv2.inRange(a_chan, alpha_min, 255)
    #     mask = cv2.bitwise_and(mask, mask_alpha)

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
#  Main
# ------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--outdir", default="docs")
    ap.add_argument("--skip-svg", action="store_true")
    ap.add_argument("--tolerance", type=int, default=1)
    ap.add_argument("--simplify", type=float, default=0.3)
    ap.add_argument("--min-area", type=int, default=80)
    ap.add_argument("--skip-sea", action="store_true")
    ap.add_argument("--supersample", type=int, default=1,
                    help="Scale mask up N* before contouring (1=off, 2=default for smooth edges)")
    args = ap.parse_args()

    outdir = Path(args.outdir); outdir.mkdir(exist_ok=True)

    # ------------------------------------------------------------
    # DATA
    # ------------------------------------------------------------

    # military_group -> faction
    faction_to_military_group = load_faction_mapping(lookup_factions)
    print(f"Loaded {len(faction_to_military_group)} faction to military_group mappings from {lookup_factions}")

    # regions -> auxilia
    region_to_resource = load_auxilia_mapping(regions_units)
    print(f"Loaded {len(region_to_resource)} resource to region mappings from {regions_units}")

    # auxilia -> units (these may be aliased)
    resource_to_unit, unit_alias = load_unit_mappings(units_folder)
    print(f"Loaded {len(resource_to_unit)} auxilia to unit mappings from {units_folder}")
       
    # unit -> military_group
    unit_to_military_group = load_unit_military_mapping(units_to_groupings_military_permissions_tables)
    print(f"Loaded {len(unit_to_military_group)} unit to military_group mappings from {units_to_groupings_military_permissions_tables}")

    # subculture -> buildings
    subculture_to_building = load_buildings_mapping(lookup_buildings)
    print(f"Loaded {len(subculture_to_building)} subculture to building mappings from {lookup_buildings}")
    # building -> units
    building_to_unit = load_building_unit_mapping(building_units_allowed_tables)
    print(f"Loaded {len(building_to_unit)} building to unit mappings from {building_units_allowed_tables}")


    # ------------------------------------------------------------
    # REGION DATA MAPPING
    # ------------------------------------------------------------
   
    # militarty group -> faction lookup
    mg_to_faction = {}
    for faction, (mg, _) in faction_to_military_group.items():
        if mg not in mg_to_faction:
            mg_to_faction[mg] = []
        mg_to_faction[mg].append(faction)


    # unit -> subculture via building
    # unit_to_subculture = {}
    # for subculture, buildings in subculture_to_building.items():
    #     for building in buildings:
    #         units = building_to_unit.get(building, [])
    #         for unit in units:
    #             if unit not in unit_to_subculture:
    #                 unit_to_subculture[unit] = []
    #             if subculture not in unit_to_subculture[unit]:
    #                 unit_to_subculture[unit].append(subculture)
    #             # also check alias
                

    # # check that we have a subculture for each unit
    # missing_subculture_units = []
    # for unit in unit_to_military_group:
    #     if unit not in unit_to_subculture:
    #         missing_subculture_units.append(unit)
    # if missing_subculture_units:
    #     print(f"Warning: Missing subculture for {len(missing_subculture_units)} units:")
    #     for mu in missing_subculture_units:
    #         print(f"  - {mu}")


    region_data = {}
    for region, resources in region_to_resource.items():
        region_data[region] = {}
        # go through all unit auxilia in the region
        for resource in resources:
            # for each auxilia, get the units
            units = resource_to_unit.get(resource, [])
            # now go through each unit and get its military group
            for unit in units:
                # get the subculture for this unit
                # subcultures = unit_to_subculture.get(unit, [])

                factions = []
                # get the military groups for this unit
                military_groups = unit_to_military_group.get(unit, [])
                for military_group in military_groups:
                    # get the factions for this military group
                    fcts = mg_to_faction.get(military_group, [])
                    for fct in fcts:
                        if fct not in factions:
                            factions.append(fct)
                
                # go through subcultures
                final_factions = []
                final_factions = factions
                # for subculture in subcultures:
                #     for faction in factions:
                #         # check if faction matches subculture
                #         _, fct_subculture = faction_to_military_group.get(faction, (None, None))
                #         if fct_subculture != subculture:
                #             continue
                #         final_factions.append(faction)

                # add to region data
                for faction in final_factions:
                    if faction not in region_data[region]:
                        region_data[region][faction] = []
                    if unit not in region_data[region][faction]:
                        # use the alias if available
                        # if unit in unit_alias:
                        #     unit = unit_alias[unit]
                        region_data[region][faction].append(unit)

    # save to json
    (outdir / "region_data.json").write_text(
        json.dumps(region_data, indent=2), encoding="utf-8")
    print(f"✓ Wrote region data mapping → {outdir/'region_data.json'}")


    # get all unique cultures
    cultures_list = {}
    for region in region_data:
        for faction in region_data[region]:
            if faction not in cultures_list:
                cultures_list[faction] = True
    cultures_list = list(cultures_list.keys())

    # save to json
    (outdir / "cultures_list.json").write_text(
        json.dumps(cultures_list, indent=2), encoding="utf-8")

    # ------------------------------------------------------------
    # LOCALIZATION
    # ------------------------------------------------------------

    # create metadata struct and json
    # unit metadata: { key, english name, icon }
    loc_data = {}
    for key in loc_sources:
        loc_data[key] = {}
        load_loc_tsv(
            loc_sources[key]["metadata"],
            loc_data[key],
            loc_sources[key]["prefix"]
        )
        print(f"Loaded {len(loc_data[key])} localization entries from {loc_sources[key]['metadata']}")

    # save to json
    (outdir / "loc_data.json").write_text(
        json.dumps(loc_data, indent=2), encoding="utf-8")
    print(f"✓ Wrote localization data mapping → {outdir/'loc_data.json'}")

    # ------------------------------------------------------------
    # CONTOURS
    # -----------------------------------------------------------

    # skip SVG generation if requested
    if args.skip_svg:
        return
    
    mapping = load_mapping(regions_csv, skip_sea=args.skip_sea)
    print(f"Loaded {len(mapping)} region color mappings from {regions_csv}")

    # this is in RGBA format
    rgba, w, h = load_lookup(Path(lookup_image))
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
