"""The two structures the city is known by, which the footprint data cannot draw. Both are meshes (Mesh).

The Sydney Harbour Bridge is not a building in the data. It is modelled from the figures in its Wikipedia article
(checked by pipeline/checks.py, see CHECKS): two 28-panel arch trusses, 18 m deep at the centre and 57 m at the
ends; a span of 504 m; the summit 134 m above mean sea level; 48.8 m wide; a pair of 89-metre pylons at each end;
formally opened on 19 March 1932. It stands on the line between OpenStreetMap's two pairs of pylons (PYLONS), and
runs the length of OpenStreetMap's way for its deck. Not in the article, and so approximations: the deck 49 m
above the water between the pylons, falling gently (DECK_FALL) along the approach spans, five each side, to the
high ground at either end; the trusses 30 m apart; the sizes of the members.

The Sydney Opera House is a building in the data, but OpenStreetMap maps its shells as flat roof pieces without
heights. Its shells are modelled as a mesh (opera_house), see the notes there.
"""
import json

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon

from .config import CRS, RAW

ARTICLE = "Sydney Harbour Bridge"
OPERA = "Sydney Opera House"
LEWIS = "https://www.royalsoc.org.au/wp-content/uploads/2024/09/106_12_lewis.pdf"   # see the Opera House below
# What a landmark's card says about its shape, by the building's OSM id (or SydMap's own id): (note, source, link).
SHAPES = {
    "r9596872": ("its shells modelled on their spherical geometry", "Lewis, 1973", LEWIS),
    "sydney-harbour-bridge": ("modelled from its figures", "Wikipedia", "https://en.wikipedia.org/wiki/Sydney_Harbour_Bridge"),
}
CHECKS = [(ARTICLE, ["two 28-panel arch trusses", "span of 504 m", "134 m (440 ft) above mean sea level",
                     "18 m (59 ft) at the centre of the arch, to 57 m", "48.8 m (160 ft) wide", "89-metre-high",
                     "formally opened on Saturday, 19 March 1932"]),
          (OPERA, ["highest roof point is 67 metres above sea-level", "sections of a sphere of 75.2 metres"])]
SPAN, SUMMIT, DEPTH_MID, DEPTH_END, WIDTH, PYLON_H, PANELS = 504.0, 134.0, 18.0, 57.0, 48.8, 89.0, 28
DECK, DECK_FALL, DECK_DEPTH, TRUSS_GAP, APPROACH_SPANS = 49.0, 0.03, 4.0, 30.0, 5
# OpenStreetMap's buildings for the bridge's pylons, 89 m as the article says: they take the bridge's year and entry.
PYLONS = ["Sydney Harbour Bridge - South Pylons", "Sydney Harbour Bridge - North Pylons"]


class Mesh:
    """Triangles in a local frame: (s, c, y), s along the structure, c across it, y up."""

    def __init__(self):
        self.verts, self.tris = [], []

    def add(self, verts, tris):
        self.tris.append(np.asarray(tris) + sum(len(v) for v in self.verts))
        self.verts.append(np.asarray(verts, float))

    def beam(self, path, w, h):
        """A beam w wide and h deep along a polyline, its sides and both ends closed."""
        path = np.asarray(path, float)
        t = np.gradient(path, axis=0)
        t /= np.linalg.norm(t, axis=1)[:, None]
        side = np.cross(t, [0.0, 0.0, 1.0])
        flat = np.linalg.norm(side, axis=1) < 1e-6           # a vertical member: its sides face along and across
        side[flat] = [0.0, 1.0, 0.0]
        side /= np.linalg.norm(side, axis=1)[:, None]
        up = np.cross(side, t)
        corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
        v = np.concatenate([[p + a * w / 2 * sd + b * h / 2 * u for a, b in corners] for p, sd, u in zip(path, side, up)])
        tris = []
        for i in range(len(path) - 1):
            for k in range(4):
                a, b, c, d = 4 * i + k, 4 * i + (k + 1) % 4, 4 * (i + 1) + (k + 1) % 4, 4 * (i + 1) + k
                tris += [(a, b, c), (a, c, d)]
        n = 4 * (len(path) - 1)
        tris += [(0, 2, 1), (0, 3, 2), (n, n + 1, n + 2), (n, n + 2, n + 3)]
        self.add(v, tris)

    def block(self, s0, s1, c0, c1, y0, y1):
        """A box between two heights."""
        self.beam([((s0 + s1) / 2, (c0 + c1) / 2, y0), ((s0 + s1) / 2, (c0 + c1) / 2, y1)], abs(c1 - c0), abs(s1 - s0))

    def placed(self, origin, along):
        """The vertices in MGA metres ([x, y, height]) and the triangles, the frame put at `origin`, s along `along`."""
        across = np.array([along[1], -along[0]])
        v, t = np.concatenate(self.verts), np.concatenate(self.tris)
        return np.c_[origin + v[:, :1] * along + v[:, 1:2] * across, v[:, 2]], t


def deck_way():
    """The OSM way for the bridge's deck: the longest tagged as the Sydney Harbour Bridge (Bradfield Highway)."""
    from pyproj import Transformer
    t = Transformer.from_crs(4326, CRS, always_xy=True)
    d = json.loads((RAW / "osm_streets.json").read_text())
    ways = [e for e in d["elements"] if e["tags"].get("bridge:name") == ARTICLE and e["tags"].get("name") == "Bradfield Highway"]
    w = max(ways, key=lambda e: len(e["geometry"]))
    xy = np.array([t.transform(p["lon"], p["lat"]) for p in w["geometry"]])
    return LineString(xy), f"w{w['id']}"


def harbour_bridge(pylons):
    """The bridge, given OSM's south and north pylon footprints (MGA).

    Returns (footprint, (vertices, triangles), OSM id of the deck, {pylon index: parts}): the pylons' parts are their
    footprints up to the deck, and the two towers either side of the roadway above it.
    """
    way, osm = deck_way()
    a, b = (np.array(p.centroid.coords[0]) for p in pylons)
    centre, along = (a + b) / 2, (b - a) / np.linalg.norm(b - a)
    ends = [float(np.dot(np.array(way.coords[k]) - centre, along)) for k in (0, -1)]
    s_south, s_north = min(ends), max(ends)
    pylon_out = max(max(abs(float(np.dot(np.array(q) - centre, along))) for q in p.exterior.coords) for p in pylons)

    def deck(s):
        """The deck's top: level between the pylons, falling along the approach spans."""
        return DECK - DECK_FALL * max(0.0, abs(s) - pylon_out)

    m = Mesh()
    k = lambda s: 1 - (2 * s / SPAN) ** 2                     # noqa: E731
    bottom = lambda s: (SUMMIT - DEPTH_MID) * k(s)            # noqa: E731  the arch, springing from its bearings
    top = lambda s: DEPTH_END + (SUMMIT - DEPTH_END) * k(s) - 1.5   # noqa: E731  the top chord's axis, its top at the summit
    nodes = np.linspace(-SPAN / 2, SPAN / 2, PANELS + 1)
    fine = np.linspace(-SPAN / 2, SPAN / 2, 2 * PANELS + 1)
    for c in (-TRUSS_GAP / 2, TRUSS_GAP / 2):
        m.beam([(s, c, bottom(s)) for s in fine], 4.0, 4.0)
        m.beam([(s, c, top(s)) for s in fine], 3.0, 3.0)
        for s in nodes:
            m.beam([(s, c, bottom(s)), (s, c, top(s))], 2.0, 2.0)
            if bottom(s) > deck(s):                            # hangers carry the deck where the arch is above it
                m.beam([(s, c, deck(s)), (s, c, bottom(s))], 1.2, 1.2)
        for s0, s1 in zip(nodes[:-1], nodes[1:]):              # diagonals, falling towards the summit
            hi, lo = (s0, s1) if s0 < 0 else (s1, s0)
            m.beam([(hi, c, top(hi)), (lo, c, bottom(lo))], 1.6, 1.6)
    for s in nodes:                                            # bracing between the trusses
        m.beam([(s, -TRUSS_GAP / 2, top(s)), (s, TRUSS_GAP / 2, top(s))], 1.5, 1.5)
        if bottom(s) > deck(s) + 8:
            m.beam([(s, -TRUSS_GAP / 2, bottom(s)), (s, TRUSS_GAP / 2, bottom(s))], 1.5, 1.5)
    # The deck, and under its approach spans the piers, the last of them the abutment on the shore.
    ss = np.r_[np.arange(s_south, s_north, 6.0), s_north]
    m.beam([(s, 0.0, deck(s) - DECK_DEPTH / 2) for s in ss], WIDTH, DECK_DEPTH)
    for end, sign in ((s_south, -1), (s_north, 1)):
        for i in range(1, APPROACH_SPANS + 1):
            s = sign * pylon_out + (end - sign * pylon_out) * i / APPROACH_SPANS
            under = deck(s) - DECK_DEPTH
            if i < APPROACH_SPANS:
                for c in (-TRUSS_GAP / 2, TRUSS_GAP / 2):
                    m.block(s - 3, s + 3, c - 5, c + 5, 0.0, under)
            else:
                m.block(s - sign * 12, s, -WIDTH / 2, WIDTH / 2, 0.0, under)
    verts, tris = m.placed(centre, along)
    across = np.array([along[1], -along[0]])
    footprint = Polygon([centre + s * along + c * WIDTH / 2 * across
                         for s, c in ((s_south, -1), (s_north, -1), (s_north, 1), (s_south, 1))])
    # The pylons: solid up to the deck; above it a tower either side of the roadway, its crown set back.
    road = shapely.buffer(LineString([centre + s_south * along, centre + s_north * along]), TRUSS_GAP / 2, cap_style="flat")
    pylon_parts = {}
    for i, p in enumerate(pylons):
        towers = shapely.make_valid(p.difference(road))
        under, crown = DECK - DECK_DEPTH, PYLON_H - 6.0
        pylon_parts[i] = [(under, 0.0, p)]
        for g in getattr(towers, "geoms", [towers]):
            if g.area > 1:
                pylon_parts[i] += [(crown, under, g), (PYLON_H, crown, g.buffer(-1.5, join_style="mitre"))]
    return footprint, (verts, tris), osm, pylon_parts


# ---------------------------------------------------------------- Sydney Opera House
#
# The geometry is the one the shells were built to, as Ove Arup & Partners' Michael Lewis describes it in "Roof
# cladding of the Sydney Opera House" (Journal and Proceedings of the Royal Society of New South Wales 106: 18-32,
# 1973): each hall has main shells, every one "made up of two half-shells symmetrical about the central axis of the
# hall"; each half "appears in elevation as a curvilinear triangle standing on a vertex" and is part of a sphere;
# its ribs are great circles of that sphere, all passing through its pole at the pedestal the half-shell stands on;
# at the top the shell is cut off by a vertical plane along the hall's axis; and "the height to the top of the
# largest shell from its springing point is 179 feet (54.6 m)". From Wikipedia: the sphere's radius is 75.2 m and
# the highest roof point is 67 m above sea level (CHECKS).
#
# So each half-shell here is the spherical triangle through three points (its pedestal at the side of the hall,
# its tip and its back corner on the axis) on a sphere of 75.2 m, drawn as the fan of great circles from the
# pedestal up to the axis. The points of the Concert Hall's four main shells are measured off the paper's western
# elevation (its figure 3), scaled so the largest rises 54.6 m to 67 m; their positions along the hall agree with
# OpenStreetMap's plan of the roof to within about 2 m, and their widths are taken from that plan. The Joan
# Sutherland Theatre's roof is in OpenStreetMap's plan the Concert Hall's at 0.79 of the size, and is drawn so; the
# restaurant's two shells are placed from the plan, their heights estimated from photographs. The side shells that
# close the gaps between main shells are drawn as plain triangles; the glass walls and louvres are left out.
SPHERE = 75.2
OPERA_TOP = 67.0
SPRING = OPERA_TOP - 54.6
# Main shells of the Concert Hall: (tip u, tip height), (back corner u, height), (pedestal u, half-span, height).
# u: metres along the hall's axis towards the harbour, from the hall's centre; heights above sea level.
CONCERT_HALL = [
    ((36.6, 43.0), (7.3, 40.0), (17.1, 25.0, 20.9)),
    ((12.9, 53.1), (-13.3, 45.7), (-2.5, 27.0, 15.8)),
    ((-5.0, 67.0), (-49.7, 32.7), (-24.0, 25.0, 12.6)),
    ((-86.4, 40.5), (-49.7, 32.7), (-72.1, 15.0, 13.7)),   # back to back with the largest, facing the city
]
RESTAURANT = [
    ((-23.7, 29.5), (3.4, 21.0), (-5.2, 13.0, SPRING)),
    ((18.9, 27.0), (3.4, 21.0), (7.9, 10.5, SPRING)),
]
# Each roof: its centre (MGA) and the bearing of its axis, both from the ridges in OpenStreetMap's plan, its shells,
# and the scale (in plan and in height above the springing) and shift along the axis of the Concert Hall's layout.
OPERA_ROOFS = [
    ("Concert Hall", (334871.7, 6252303.4), 1.1, CONCERT_HALL, 1.0, 0.0),
    ("Joan Sutherland Theatre", (334924.3, 6252282.8), 23.6, CONCERT_HALL, 0.79, 8.45),
    ("Bennelong restaurant", (334845.6, 6252209.6), 12.3, RESTAURANT, 1.0, 0.0),
]


def sphere_centre(p, r, outward):
    """The centre of the sphere of radius r through the three points p, on the side away from `outward`."""
    a, b = p[1] - p[0], p[2] - p[0]
    n = np.cross(a, b)
    cc = p[0] + (np.dot(a, a) * np.cross(b, n) + np.dot(b, b) * np.cross(n, a)) / (2 * np.dot(n, n))
    h = np.sqrt(r * r - np.sum((cc - p[0]) ** 2))
    n = n / np.linalg.norm(n)
    c = cc + h * n
    return c if np.dot(p.mean(0) - c, outward) > 0 else cc - h * n


def half_shell(tip, back, pedestal, r=SPHERE, ribs=12, steps=12):
    """A half-shell, in hall coordinates (u along the axis, v across, y up), as (vertices, triangles).

    The spherical triangle through the pedestal (the pole of its ribs) and the tip and back corner (on the ridge
    plane v = 0): `ribs` + 1 great circles from the pedestal, each up to where it meets the ridge plane.
    """
    side = np.sign(pedestal[1])
    c = sphere_centre(np.array([pedestal, tip, back]), r, np.array([0.0, side, 1.0]))
    pole = (pedestal - c) / r

    def heading(p):
        d = (p - c) / r - np.dot((p - c) / r, pole) * pole
        return d / np.linalg.norm(d)

    d0, d1 = heading(tip), heading(back)
    turn = np.arccos(np.clip(np.dot(d0, d1), -1, 1))
    across = np.cross(pole, d0) * np.sign(np.dot(np.cross(pole, d0), d1))
    verts = []
    for i in range(ribs + 1):
        d = np.cos(turn * i / ribs) * d0 + np.sin(turn * i / ribs) * across
        # where the great circle c + r(pole cos t + d sin t) meets the plane v = 0
        A, B = r * pole[1], r * d[1]
        phase, half = np.arctan2(B, A), np.arccos(np.clip(-c[1] / np.hypot(A, B), -1, 1))
        end = min(t % (2 * np.pi) for t in (phase - half, phase + half) if t % (2 * np.pi) > 1e-6)
        t = np.linspace(0, end, steps + 1)[:, None]
        verts.append(c + r * (pole * np.cos(t) + d * np.sin(t)))
    verts = np.concatenate(verts)
    tris = []
    for i in range(ribs):
        for j in range(steps):
            a, b = i * (steps + 1) + j, (i + 1) * (steps + 1) + j
            if j:
                tris.append((a, b, a + 1))
            tris.append((a + 1, b, b + 1))
    return verts, np.array(tris)


def roof_shells(shells):
    """The main shells of one roof and the side shells between them, in hall coordinates."""
    parts, specs = [], []
    for (tu, ty), (bu, by), (pu, w, py) in shells:
        for side in (-1, 1):
            tip, back, ped = np.array([tu, 0.0, ty]), np.array([bu, 0.0, by]), np.array([pu, side * w, py])
            parts.append(half_shell(tip, back, ped))
        specs.append((np.array([tu, ty]), np.array([bu, by]), np.array([pu, py]), w))
    # Side shells: between neighbours, from the two pedestals up to where their facing edges cross in elevation.
    specs.sort(key=lambda s: -s[2][0])
    for (t0, b0, p0, w0), (t1, b1, p1, w1) in zip(specs[:-1], specs[1:]):
        e0 = b0 if b0[0] < p0[0] else t0          # the edge of the northern shell that faces south
        e1 = t1 if t1[0] > p1[0] else b1          # and the southern shell's edge that faces north
        # p0 + k (e0 - p0) = p1 + s (e1 - p1): the crossing is s of the way up the southern shell's edge
        m = np.array([e0 - p0, p1 - e1]).T
        s = np.clip(np.linalg.solve(m, p1 - p0)[1], 0, 1) if abs(np.linalg.det(m)) > 1e-9 else 1.0
        x = p1 + s * (e1 - p1)
        for side in (-1, 1):
            v = np.array([[p0[0], side * w0, p0[1]], [p1[0], side * w1, p1[1]], [x[0], side * w1 * (1 - s), x[1]]])
            parts.append((v, np.array([[0, 1, 2]])))
    return parts


def opera_house():
    """The Opera House's shells as one mesh in MGA metres: (vertices [x, y, height], triangles)."""
    verts, tris = [], []
    for _, (cx, cy), bearing, shells, scale, shift in OPERA_ROOFS:
        b = np.radians(bearing)
        along, across = np.array([np.sin(b), np.cos(b)]), np.array([np.cos(b), -np.sin(b)])
        placed = [((shift + scale * tu, SPRING + scale * (ty - SPRING)), (shift + scale * bu, SPRING + scale * (by - SPRING)),
                   (shift + scale * pu, scale * w, SPRING + scale * (py - SPRING))) for (tu, ty), (bu, by), (pu, w, py) in shells]
        for v, t in roof_shells(placed):
            xy = np.array([cx, cy]) + v[:, :1] * along + v[:, 1:2] * across
            tris.append(t + sum(len(x) for x in verts))
            verts.append(np.c_[xy, v[:, 2]])
    return np.concatenate(verts), np.concatenate(tris)
