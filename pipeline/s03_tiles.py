"""Pack buildings into 600 m binary tiles + a city config JSON.

Local frame: metres from the GPO in Martin Place, x east, z south (three.js, y up).
Tile layout (little-endian, every section 4-byte aligned):
  header  u32 magic, nB, nP, nR, nV, nMV, nMT; f32 originX, originZ
  B       u32 gid[nB]; i16 year[nB]; u8 flag[nB]; u8 period[nB]; u8 floors[nB]; u8 heritage[nB] (see HERITAGE);
          u32 lay0[nB]; u32 lay1[nB] (layer bits, see s05_layers); u32 partStart[nB+1]
  P       f32 height[nP]; f32 base[nP]; u32 ringStart[nP+1]
  R       u32 vertStart[nR+1]; u8 hole[nR]
  V       i16 xz[2*nV], decimetres from the tile origin
  M       meshes, for the shapes extrusion cannot draw (the Opera House's shells, see landmarks.py):
          u16 bld[nMV] (the building's index in this tile, plus 0x8000 for a surface drawn pale, as the Opera
          House's tiles are); i16 xyz[3*nMV], decimetres from the tile origin (y up); u16 tri[3*nMT]
"""
import json
import struct

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from .config import CRS, DATA, WEB, gpo_mga
from .landmarks import SHAPES
from .periods import PERIODS

GPO = gpo_mga()
TILE = 600.0
SIMPLIFY = 0.25
MAGIC = 0x32445953  # 'SYD2'
PALE = 0x8000
# Heritage status of a building, the fourth colouring of the map (index 0: none).
HERITAGE = ["State Heritage Register", "Local heritage item", "Contributing building",
            "Neutral building", "Detracting building"]
HERITAGE_COLORS = ["#efeee9", "#7a1f2b", "#c0462b", "#e5b13a", "#a9b8bd", "#56636b"]


def pad4(b: bytes) -> bytes:
    return b + b"\0" * (-len(b) % 4)


def to_local(coords: np.ndarray) -> np.ndarray:
    return np.c_[coords[:, 0] - GPO[0], -(coords[:, 1] - GPO[1])]


def rings_of(geom):
    polys = getattr(geom, "geoms", [geom])
    for poly in polys:
        if poly.is_empty or poly.geom_type != "Polygon":
            continue
        yield shapely.get_coordinates(poly.exterior)[:-1], 0
        for hole in poly.interiors:
            yield shapely.get_coordinates(hole)[:-1], 1


def pack_tile(origin, rows):
    gid, year, flag, period, floors, heritage, lay0, lay1, part_start = [], [], [], [], [], [], [], [], [0]
    heights, bases, ring_start, vert_start, holes, verts = [], [], [0], [0], [], []
    mesh_bld, mesh_pos, mesh_tri, n_mv = [], [], [], 0
    for i, b in enumerate(rows):
        if b.get("mesh") is not None:
            v, t, pale = b["mesh"]
            xyz = np.c_[to_local(v[:, :2]) - origin, v[:, 2]][:, [0, 2, 1]] * 10
            mesh_pos.append(np.round(xyz).astype(np.int16))
            mesh_bld.append(np.full(len(v), i | (PALE if pale else 0), np.uint16))
            mesh_tri.append(np.asarray(t, np.uint32) + n_mv)
            n_mv += len(v)
        gid.append(b["gid"]); year.append(b["year"]); flag.append(b["flag"])
        period.append(b["period"]); floors.append(min(b["floors"], 255)); heritage.append(b["heritage"])
        lay0.append(b["lay0"]); lay1.append(b["lay1"])
        for h, base, geom in b["parts"]:
            n0 = len(holes)
            for ring, hole in rings_of(geom):
                if len(ring) < 3:
                    continue
                loc = (to_local(ring) - origin) * 10
                verts.append(np.round(loc).astype(np.int16))
                holes.append(hole)
                vert_start.append(vert_start[-1] + len(ring))
            if len(holes) == n0:
                continue
            heights.append(h); bases.append(base)
            ring_start.append(len(holes))
        part_start.append(len(heights))
    nB, nP, nR = len(gid), len(heights), len(holes)
    assert nB < PALE, "the viewer keeps a building's index in a tile in 15 bits"
    V = np.concatenate(verts) if verts else np.zeros((0, 2), np.int16)
    tri = np.concatenate(mesh_tri) if mesh_tri else np.zeros((0, 3), np.uint32)
    assert n_mv <= 0x10000, "mesh vertices are indexed in 16 bits"
    out = struct.pack("<7I2f", MAGIC, nB, nP, nR, len(V), n_mv, len(tri), *origin)
    out += pad4(np.array(gid, "<u4").tobytes())
    out += pad4(np.array(year, "<i2").tobytes())
    out += pad4(np.array(flag, "u1").tobytes())
    out += pad4(np.array(period, "u1").tobytes())
    out += pad4(np.array(floors, "u1").tobytes())
    out += pad4(np.array(heritage, "u1").tobytes())
    out += np.array(lay0, "<u4").tobytes() + np.array(lay1, "<u4").tobytes()
    out += pad4(np.array(part_start, "<u4").tobytes())
    out += pad4(np.array(heights, "<f4").tobytes())
    out += pad4(np.array(bases, "<f4").tobytes())
    out += pad4(np.array(ring_start, "<u4").tobytes())
    out += pad4(np.array(vert_start, "<u4").tobytes())
    out += pad4(np.array(holes, "u1").tobytes())
    out += pad4(V.astype("<i2").tobytes())
    if n_mv:
        out += pad4(np.concatenate(mesh_bld).astype("<u2").tobytes())
        out += pad4(np.concatenate(mesh_pos).astype("<i2").tobytes())
        out += pad4(tri.astype("<u2").tobytes())
    return out


# Per-building lookup for the card, read by offset in the browser (config.attrFields says where).
ATTR_DTYPE = np.dtype([
    ("osm", "<f8"),        # OpenStreetMap id: way n → n, relation n → -n, none → 0
    ("year", "<i2"), ("yfrom", "<i2"), ("yto", "<i2"),   # the map's year and, when estimated, its range
    ("h", "<u2"),          # height, decimetres
    ("hsrc", "u1"), ("fsrc", "u1"), ("flag", "u1"), ("heritage", "u1"),
    ("lay0", "<u4"), ("lay1", "<u4"),
    ("wk", "<i4"),         # index into wiki.json, -1 none
    ("nm", "<i4"),         # index into names.json (OSM names of buildings without a wiki entry), -1 none
    ("hi", "<i4"),         # index into heritage.json (the listing that covers it), -1 none
    ("sp", "<u4"),         # strata plan number, 0 none
    ("src", "u1"),         # footprint source: 0 OpenStreetMap, 1 Microsoft (via Overture)
    ("floors", "u1"),
    ("dsrc", "u1"),        # where a year comes from: 0 Wikidata, 1 Wikipedia, 2 OpenStreetMap, 3 other, 4 its heritage listing
    ("pad", "u1"),
    ("x", "<f4"), ("z", "<f4"),
])


def main():
    b = gpd.read_parquet(DATA / "buildings_dated.parquet")
    lay = pd.read_parquet(DATA / "layers.parquet")
    b = b.merge(lay, on="bid", how="left").merge(pd.read_parquet(DATA / "cards.parquet"), on="bid", how="left")
    assert (b.bid.to_numpy() == np.arange(len(b))).all(), "buildings must stay in bid order: the gid is the bid"
    b[["lay0", "lay1"]] = b[["lay0", "lay1"]].fillna(0).astype(np.uint32)
    q = gpd.read_parquet(DATA / "parts.parquet")
    q["geometry"] = shapely.simplify(q.geometry.values, SIMPLIFY, preserve_topology=True)
    parts = q.groupby("bid")[["height", "base", "geometry"]].apply(
        lambda d: list(zip(d.height, d.base, d.geometry))).to_dict()
    m = np.load(DATA / "meshes.npz")
    meshes = {int(bid): (m["verts"][m["vstart"][k]:m["vstart"][k + 1]], m["tris"][m["tstart"][k]:m["tstart"][k + 1]],
                         bool(m["pale"][k])) for k, bid in enumerate(m["bid"])}
    b["geometry"] = shapely.simplify(b.geometry.values, SIMPLIFY, preserve_topology=True)

    b = b.reset_index(drop=True)
    b["gid"] = np.arange(len(b))
    c = to_local(np.c_[b.geometry.centroid.x, b.geometry.centroid.y])
    b["tx"] = np.floor(c[:, 0] / TILE).astype(int)
    b["tz"] = np.floor(c[:, 1] / TILE).astype(int)

    (WEB / "tiles").mkdir(parents=True, exist_ok=True)
    index = []
    for (tx, tz), grp in b.groupby(["tx", "tz"]):
        origin = np.array([tx * TILE, tz * TILE])
        rows = [dict(gid=int(r.gid), year=int(r.year), flag=int(r.date_flag), period=int(r.period),
                     floors=int(r.floors), heritage=int(r.heritage), lay0=int(r.lay0), lay1=int(r.lay1),
                     parts=parts.get(r.bid) or ([] if r.bid in meshes else [(float(r.height), 0.0, r.geometry)]),
                     mesh=meshes.get(r.bid))
                for r in grp.itertuples()]
        data = pack_tile(origin, rows)
        name = f"{tx}_{tz}.bin"
        (WEB / "tiles" / name).write_bytes(data)
        cx, cz = origin + TILE / 2
        index.append(dict(file=name, tx=int(tx), tz=int(tz), n=len(rows), bytes=len(data),
                          dist=round(float(np.hypot(cx, cz)))))
    index.sort(key=lambda t: t["dist"])

    # Bundle tiles into a few packs, nearest the GPO first, so the city loads centre-out in few requests.
    packs, n_packs = [], 6
    per = -(-len(index) // n_packs)
    for k in range(n_packs):
        chunk = index[k * per:(k + 1) * per]
        if not chunk:
            break
        name, offset, blob = f"pack{k}.bin", 0, bytearray()
        for t in chunk:
            data = (WEB / "tiles" / t["file"]).read_bytes()
            t.update(pack=name, offset=offset, length=len(data))
            blob += data
            offset += len(data)
        (WEB / name).write_bytes(blob)
        packs.append(name)
    for f in (WEB / "tiles").glob("*.bin"):
        f.unlink()
    (WEB / "tiles").rmdir()

    attrs = np.zeros(len(b), dtype=ATTR_DTYPE)
    osm = b.osm.fillna("")
    attrs["osm"] = [float(s[1:]) if s.startswith("w") else -float(s[1:]) if s.startswith("r") else 0 for s in osm]
    attrs["year"] = b.year
    attrs["yfrom"] = b.yfrom
    attrs["yto"] = b.yto
    attrs["h"] = np.round(b.height * 10).clip(0, 65535)
    attrs["hsrc"] = b.height_src
    attrs["fsrc"] = b.floors_src
    attrs["flag"] = b.date_flag
    attrs["heritage"] = b.heritage
    attrs["lay0"] = b.lay0
    attrs["lay1"] = b.lay1
    attrs["wk"] = b.wk
    attrs["nm"] = b.nm
    attrs["hi"] = b.hi
    attrs["sp"] = b.sp.fillna(0).astype(np.uint32)
    attrs["src"] = (b.source != "osm").astype(np.uint8)
    attrs["floors"] = b.floors.clip(0, 255)
    attrs["dsrc"] = b.dsrc
    attrs["x"], attrs["z"] = c[:, 0], c[:, 1]
    (WEB / "attrs.bin").write_bytes(attrs.tobytes())
    b[["bid", "gid"]].to_parquet(DATA / "gid.parquet")

    hist = {}
    for p, y in zip(b.period, b.year):
        hist.setdefault(int(y), [0] * len(PERIODS))[p] += 1
    config = dict(
        city="sydney", label="Sydney", tileSize=TILE, origin=list(GPO), crs=f"EPSG:{CRS}",
        home=dict(x=-350, z=-500, azimuth=18, elevation=32, span=7200),
        periods=[dict(key=k, label=l, from_=a, to=bb, color=col) for k, l, a, bb, col in PERIODS],
        yearMin=int(b.year.min()), yearMax=int(b.year.max()),
        histogram={str(k): v for k, v in sorted(hist.items())},
        attrStride=ATTR_DTYPE.itemsize,
        attrFields={n: [ATTR_DTYPE.fields[n][1], ATTR_DTYPE.fields[n][0].str] for n in ATTR_DTYPE.names if n != "pad"},
        heritage=dict(labels=HERITAGE, colors=HERITAGE_COLORS,
                      counts=[int((b.heritage == i).sum()) for i in range(len(HERITAGE) + 1)]),
        tiles=index,
        packs=packs,
        shapes={str(int(g)): SHAPES.get(o) or SHAPES[i] for g, o, i in zip(b.gid, b.osm, b.id) if o in SHAPES or i in SHAPES},
        stats=dict(buildings=len(b),
                   flags={int(k): int(v) for k, v in b.date_flag.value_counts().sort_index().items()},
                   heightSrc={int(k): int(v) for k, v in b.height_src.value_counts().sort_index().items()},
                   floorsTagged=int((b.floors_src == 0).sum()), floorsHeight=int((b.floors_src == 1).sum()),
                   osm=int((b.source == "osm").sum()), ml=int((b.source != "osm").sum()),
                   byLga={k: int(v) for k, v in b.lga.value_counts().items()}),
    )
    (WEB / "sydney.json").write_text(json.dumps(config, ensure_ascii=False, separators=(",", ":")).replace('"from_"', '"from"'))
    total = sum(t["bytes"] for t in index)
    print(f"{len(index)} tiles, {total / 1e6:.1f} MB, attrs {attrs.nbytes / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
