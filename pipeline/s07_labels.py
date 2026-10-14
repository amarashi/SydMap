"""Street and water names, laid flat along their own lines.

Streets: OpenStreetMap highways with a name. Each street's lines are merged and cut into stretches of about
300 m; every stretch long enough gets one label at its middle, turned along it. Tier 1 (main roads and the
best-known streets) shows from afar, tier 2 only up close. Water: the harbour and its bays (tier 0), placed
at a point inside the water and turned along its longest side.
"""
import json
import math

import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import LineString, Point
from shapely.ops import linemerge, substring

from .config import CRS, RAW, WEB
from .s03_tiles import to_local

STRETCH = 300.0
WIDTH = {"motorway": 24, "trunk": 22, "primary": 20, "secondary": 16, "tertiary": 13, "unclassified": 10,
         "residential": 10, "living_street": 7, "pedestrian": 9}
TIER1_ROADS = {"motorway", "trunk", "primary", "secondary"}
TIER1 = {"George Street", "Pitt Street", "Macquarie Street", "Elizabeth Street", "Castlereagh Street", "York Street",
         "Clarence Street", "Kent Street", "Sussex Street", "Market Street", "King Street", "Hunter Street",
         "Bridge Street", "Martin Place", "Park Street", "Druitt Street", "Bathurst Street", "Liverpool Street",
         "Oxford Street", "William Street", "Crown Street", "Bourke Street", "Cleveland Street", "Harris Street",
         "Glebe Point Road", "Parramatta Road", "Broadway", "Darlinghurst Road", "Macleay Street", "Victoria Street",
         "Miller Street", "Walker Street", "Pacific Highway", "Military Road", "Alfred Street", "Kirribilli Avenue",
         "Hickson Road", "Cumberland Street", "Circular Quay West", "Circular Quay East", "Alfred Street South",
         "Botany Road", "Regent Street", "Redfern Street", "Abercrombie Street", "City Road", "King Street"}
HARBOUR = {"Port Jackson", "Sydney Harbour", "Darling Harbour", "Sydney Cove", "Farm Cove", "Woolloomooloo Bay",
           "Elizabeth Bay", "Rushcutters Bay", "Neutral Bay", "Lavender Bay", "Berrys Bay", "Blackwattle Bay",
           "Johnstons Bay", "Cockle Bay", "Mosman Bay", "Careening Cove", "Shell Cove", "Double Bay", "Waverton Bay",
           "Ball's Head Bay", "Balls Head Bay", "Rozelle Bay", "White Bay", "Snails Bay", "Alexandra Canal",
           "Iron Cove", "Mort Bay", "Glebe Island"}


def to_xy(coords):
    from pyproj import Transformer
    t = Transformer.from_crs(4326, CRS, always_xy=True)
    lon, lat = zip(*coords)
    return np.c_[t.transform(lon, lat)]


def angle(dx, dy):
    ang = math.degrees(math.atan2(-dy, dx))  # local z points south
    return (ang + 90) % 180 - 90             # keep text upright


def street_labels(city):
    d = json.loads((RAW / "osm_streets.json").read_text())
    by_name = {}
    for e in d["elements"]:
        g = e.get("geometry")
        if not g or len(g) < 2:
            continue
        t = e["tags"]
        line = LineString(to_xy([(p["lon"], p["lat"]) for p in g]))
        s = by_name.setdefault(t["name"], dict(lines=[], kinds=set()))
        s["lines"].append(line)
        s["kinds"].add(t.get("highway"))
    labels = []
    area = city.buffer(30)
    for name, s in by_name.items():
        merged = linemerge(shapely.MultiLineString(s["lines"]))
        merged = merged.intersection(area)
        parts = [m for m in getattr(merged, "geoms", [merged]) if m.geom_type == "LineString" and m.length > 40]
        width = max(WIDTH.get(k, 10) for k in s["kinds"])
        pts = []
        for line in parts:
            n = max(1, round(line.length / STRETCH))
            step = line.length / n
            for i in range(n):
                piece = substring(line, i * step, (i + 1) * step)
                if piece.length < 60:
                    continue
                mid = piece.interpolate(0.5, normalized=True)
                a = piece.interpolate(0.35, normalized=True)
                b = piece.interpolate(0.65, normalized=True)
                # Only fairly straight stretches: a name along a bend would leave the street.
                straight = Point(piece.coords[0]).distance(Point(piece.coords[-1])) / piece.length
                if straight < 0.85:
                    continue
                x, z = to_local(np.array([[mid.x, mid.y]]))[0]
                pts.append([round(float(x), 1), round(float(z), 1), round(angle(b.x - a.x, b.y - a.y), 1),
                            round(piece.length), width])
        # Keep placements at least 350 m apart, longest stretches first.
        kept = []
        for p in sorted(pts, key=lambda p: -p[3]):
            if all((p[0] - q[0]) ** 2 + (p[1] - q[1]) ** 2 > 350 ** 2 for q in kept):
                kept.append(p)
        if kept:
            tier = 1 if (s["kinds"] & TIER1_ROADS or name in TIER1) else 2
            labels.append(dict(name=name, water=False, tier=tier, pts=kept))
    return labels


def water_labels():
    """Named bays and the harbour, from OSM (bays as points or areas) and Overture (Port Jackson)."""
    from .s01_load import read_wkb
    found = {}
    d = json.loads((RAW / "osm_water.json").read_text()) if (RAW / "osm_water.json").exists() else {"elements": []}
    for e in d["elements"]:
        name = e.get("tags", {}).get("name")
        if name not in HARBOUR:
            continue
        if e["type"] == "node":
            found.setdefault(name, Point(to_xy([(e["lon"], e["lat"])])[0]))
        elif e.get("geometry"):
            xy = to_xy([(p["lon"], p["lat"]) for p in e["geometry"]])
            if len(xy) >= 4 and np.allclose(xy[0], xy[-1]):
                found.setdefault(name, shapely.Polygon(xy))
    w = read_wkb(RAW / "overture_water.parquet").to_crs(CRS)
    for r in w[w.name.isin(HARBOUR)].itertuples():
        found.setdefault(r.name, r.geometry)
    labels = []
    for name, geom in found.items():
        if geom.geom_type == "Point":
            p, ang, length = geom, 0.0, 600
        else:
            r = geom.minimum_rotated_rectangle
            c = np.array(r.exterior.coords)[:4]
            e1, e2 = c[1] - c[0], c[2] - c[1]
            long = e1 if np.hypot(*e1) >= np.hypot(*e2) else e2
            p = geom.representative_point() if not geom.contains(geom.centroid) else geom.centroid
            ang, length = angle(*long), float(np.hypot(*long))
            if name == "Port Jackson":
                name = "Sydney Harbour"
        x, z = to_local(np.array([[p.x, p.y]]))[0]
        labels.append(dict(name=name, water=True, tier=0 if name == "Sydney Harbour" else 1,
                           pts=[[round(float(x), 1), round(float(z), 1), round(ang, 1), round(min(length, 4000)), 400]]))
    return labels


def main():
    city = gpd.read_parquet(RAW / "boundary.parquet").to_crs(CRS).union_all()
    labels = water_labels() + street_labels(city)
    (WEB / "labels.json").write_text(json.dumps(labels, ensure_ascii=False, separators=(",", ":")))
    print(len(labels), "names,", sum(len(l["pts"]) for l in labels), "placements,",
          sum(l["tier"] <= 1 for l in labels), "tier 0–1;", (WEB / "labels.json").stat().st_size // 1024, "KB")


if __name__ == "__main__":
    main()
