"""Water, the city's land and the land around it, in the viewer's local frame.

From Overture's base theme: coastline land (OpenStreetMap), the harbour, rivers and ponds. Three layers:
  water.bin     the harbour and every pond, canal and river in view
  land.bin      the LGAs, less their water: the white ground the buildings stand on
  context.bin   the other shores, drawn a shade darker so the harbour keeps its shape

Layout of each (little-endian):
  u32 nPoly, nRing, nVert; u32 ringStart[nPoly+1]; u32 vertStart[nRing+1]; f32 xz[2*nVert]
First ring of each polygon is its exterior, the rest are holes.
"""
import struct

import geopandas as gpd
import numpy as np
import shapely
from shapely.geometry import box

from .config import BBOX, CRS, RAW, WEB
from .s01_load import read_wkb
from .s03_tiles import to_local, write_bin

INLAND = {"pond", "reservoir", "river", "canal", "lake", "stream", "water", "physical", "ocean"}


def polygons(geom):
    return [g for g in getattr(geom, "geoms", [geom]) if g.geom_type == "Polygon" and not g.is_empty]


def pack(geoms) -> bytes:
    ring_start, vert_start, verts = [0], [0], []
    for poly in geoms:
        for ring in [poly.exterior, *poly.interiors]:
            c = shapely.get_coordinates(ring)[:-1]
            if len(c) < 3:
                continue
            verts.append(to_local(c).astype("<f4"))
            vert_start.append(vert_start[-1] + len(c))
        ring_start.append(len(vert_start) - 1)
    V = np.concatenate(verts) if verts else np.zeros((0, 2), "<f4")
    return (struct.pack("<3I", len(ring_start) - 1, len(vert_start) - 1, len(V))
            + np.array(ring_start, "<u4").tobytes() + np.array(vert_start, "<u4").tobytes() + V.tobytes())


def ground_and_water():
    """Coastline land and every water surface in the view box, in MGA metres."""
    rect = gpd.GeoSeries([box(*BBOX)], crs=4326).to_crs(CRS).iloc[0].envelope
    land = read_wkb(RAW / "overture_land.parquet").to_crs(CRS)
    land = land[land.subtype == "land"]
    ground = shapely.make_valid(land.union_all()).intersection(rect)
    w = read_wkb(RAW / "overture_water.parquet").to_crs(CRS)
    w = w[w.subtype.isin(INLAND) & ~w["class"].isin(["swimming_pool", "wastewater", "drain", "fishpond"])]
    inland = shapely.make_valid(w.union_all()).intersection(rect)
    return rect, ground, rect.difference(ground).union(inland)


def main():
    rect = gpd.GeoSeries([box(*BBOX)], crs=4326).to_crs(CRS).iloc[0].envelope
    city = gpd.read_parquet(RAW / "boundary.parquet").to_crs(CRS).union_all()

    land = read_wkb(RAW / "overture_land.parquet").to_crs(CRS)
    land = land[land.subtype == "land"]
    ground = shapely.make_valid(land.union_all()).intersection(rect)

    w = read_wkb(RAW / "overture_water.parquet").to_crs(CRS)
    w = w[w.subtype.isin(INLAND) & ~w["class"].isin(["swimming_pool", "wastewater", "drain", "fishpond"])]
    inland = shapely.make_valid(w.union_all()).intersection(rect)

    water = rect.difference(ground).union(inland)
    water = water.buffer(0.5).buffer(-0.5).simplify(1.0)
    water = [p for p in polygons(water) if p.area > 60]
    water_u = shapely.MultiPolygon(water)

    # The LGA boundaries follow the shore loosely; the coastline decides what is land.
    mine = city.intersection(ground).difference(water_u).simplify(1.0)
    mine = [p for p in polygons(mine) if p.area > 60]
    other = ground.difference(city).difference(water_u).simplify(2.0)
    other = [p for p in polygons(other) if p.area > 400]

    WEB.mkdir(parents=True, exist_ok=True)
    write_bin(WEB / "water.bin", pack(water))
    write_bin(WEB / "land.bin", pack(mine))
    write_bin(WEB / "context.bin", pack(other))
    for n in ("water", "land", "context"):
        print(f"{n}: {(WEB / f'{n}.bin').stat().st_size / 1e6:.2f} MB")
    print(f"water {sum(p.area for p in water) / 1e6:.1f} km², city land {sum(p.area for p in mine) / 1e6:.1f} km²")


if __name__ == "__main__":
    main()
