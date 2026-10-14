"""Structures the city is known by that are not buildings in the data: the Sydney Harbour Bridge.

The bridge is drawn as a schematic model on the axis OpenStreetMap gives its deck, from the figures in its
Wikipedia article (checked by pipeline/checks.py, see CHECKS):
  span of 504 m; the summit 134 m above mean sea level; two arch trusses 18 m deep at the centre and 57 m at the
  ends; 48.8 m wide; a pair of 89-metre pylons at each end; formally opened on 19 March 1932.
The deck height is not in the article; 49 m, the deck at the pylons, is an approximation.
"""
import json

import numpy as np
import shapely
from shapely.geometry import LineString, Polygon

from .config import CRS, RAW

ARTICLE = "Sydney Harbour Bridge"
CHECKS = [(ARTICLE, ["span of 504 m", "134 m (440 ft) above mean sea level", "18 m (59 ft) at the centre of the arch, to 57 m",
                     "48.8 m (160 ft) wide", "89-metre-high", "formally opened on Saturday, 19 March 1932"]),
          ("Sydney Opera House", ["highest roof point is 67 metres above sea-level"])]
SPAN, SUMMIT, DEPTH_MID, DEPTH_END, WIDTH, PYLON_H, DECK = 504.0, 134.0, 18.0, 57.0, 48.8, 89.0, 49.0
TRUSS_GAP, TRUSS_W, PANELS = 30.0, 4.0, 40


def deck_axis():
    """The bridge's axis: the longest OSM way tagged as the Sydney Harbour Bridge (Bradfield Highway)."""
    from pyproj import Transformer
    t = Transformer.from_crs(4326, CRS, always_xy=True)
    d = json.loads((RAW / "osm_streets.json").read_text())
    ways = [e for e in d["elements"] if e["tags"].get("bridge:name") == ARTICLE and e["tags"].get("name") == "Bradfield Highway"]
    w = max(ways, key=lambda e: len(e["geometry"]))
    xy = np.array([t.transform(p["lon"], p["lat"]) for p in w["geometry"]])
    return LineString(xy), f"w{w['id']}"


def rect(c, u, v, along, across):
    """A rectangle centred on c, `along` long in direction u and `across` wide in direction v."""
    a, b = u * along / 2, v * across / 2
    return Polygon([c - a - b, c + a - b, c + a + b, c - a + b])


def harbour_bridge(water):
    """(footprint, parts, osm id): parts are (height, base, polygon) in MGA metres."""
    axis, osm = deck_axis()
    p0, p1 = np.array(axis.coords[0]), np.array(axis.coords[-1])
    u = (p1 - p0) / np.linalg.norm(p1 - p0)
    v = np.array([-u[1], u[0]])
    # The arch stands over the water: its centre is the middle of the stretch of the axis over the harbour.
    wet = axis.intersection(water)
    longest = max(getattr(wet, "geoms", [wet]), key=lambda g: g.length)
    mid = np.array(longest.interpolate(0.5, normalized=True).coords[0])
    parts = []
    # Arch: two trusses of PANELS segments; chords follow parabolas from the bearings to the summit.
    edges = np.linspace(-SPAN / 2, SPAN / 2, PANELS + 1)
    for s0, s1 in zip(edges[:-1], edges[1:]):
        s = (s0 + s1) / 2
        k = 1 - (2 * s / SPAN) ** 2
        top = DEPTH_END + (SUMMIT - DEPTH_END) * k
        bottom = max(1.0, top - (DEPTH_END + (DEPTH_MID - DEPTH_END) * k))
        for side in (-1, 1):
            c = mid + u * s + v * side * TRUSS_GAP / 2
            parts.append((top, bottom, rect(c, u, v, s1 - s0 + 0.5, TRUSS_W)))
    # Deck: level between the pylons, falling over the approach spans to the shores.
    length = axis.length
    start = float(np.dot(mid - p0, u))
    for d0 in np.arange(0, length, 20.0):
        d1 = min(d0 + 20.0, length)
        dc = (d0 + d1) / 2 - start
        out = max(0.0, abs(dc) - (SPAN / 2 + 30))
        reach = max(1.0, (start if dc < 0 else length - start) - (SPAN / 2 + 30))
        top = DECK - (DECK - 12.0) * min(1.0, out / reach)
        c = p0 + u * (d0 + d1) / 2
        parts.append((top, max(0.5, top - 4.0), rect(c, u, v, d1 - d0 + 0.3, WIDTH)))
    # Pylons: a pair at each end, either side of the deck.
    for end in (-1, 1):
        for side in (-1, 1):
            c = mid + u * end * (SPAN / 2 + 14) + v * side * (WIDTH / 2 + 10)
            parts.append((PYLON_H, 0.0, rect(c, u, v, 26.0, 18.0)))
    footprint = shapely.union_all([p for _, _, p in parts])
    return footprint, parts, osm
