"""The 2D GIS: a RustGIS project of the same buildings, built with RustGIS's own Python engine.

  web/data/gis/buildings.parquet   every building as GeoParquet (EPSG:4326) with its year, the evidence for it,
                                   period, heritage and sources; ODbL (it derives from OpenStreetMap). Heights
                                   modelled by GlobalBuildingAtlas (CC BY-NC) are left out.
  web/data/gis/sydney.rgis         a RustGIS project: the buildings coloured by period as on the 3D map, the
                                   harbour, the area's boundary and an OpenFreeMap basemap. The GeoParquet is
                                   carried inside the project, so the file opens as it is in RustGIS on the
                                   desktop, and the page sends it to the RustGIS web app it embeds.
  docs/rustgis-period-map.png      the same map, rendered by RustGIS, for the README

RustGIS: https://github.com/opengeos/RustGIS (`pip install rustgis`).
"""
import base64
import json
import struct

import geopandas as gpd
import numpy as np
import pandas as pd
import rustgis
import shapely

from .config import CRS, DATA, RAW, WEB, gpo_mga
from .periods import PERIODS
from .s03_tiles import HERITAGE

GIS = WEB / "gis"
DOCS = WEB.parent.parent / "docs"
DATING = {0: "documented", 1: "documented, approximate", 2: "strata plan", 3: "heritage area estimate",
          4: "estimated from neighbours"}
SOURCE = {"wikidata": "Wikidata", "wikipedia": "Wikipedia", "osm": "OpenStreetMap", "strata": "NSW cadastre",
          "heritage": "heritage area", "tall": "neighbours", "detracting": "neighbours", "low-rise": "neighbours",
          "other": "neighbours"}
HEIGHT_SRC = {0: "OpenStreetMap", 1: "OpenStreetMap storeys", 4: "Wikipedia"}
WATER = (181, 199, 198)
BASEMAP = "https://tiles.openfreemap.org/styles/positron"


def rgb(hex_):
    return [int(hex_[i:i + 2], 16) for i in (1, 3, 5)]


def export_buildings() -> gpd.GeoDataFrame:
    b = gpd.read_parquet(DATA / "buildings_dated.parquet")
    cards = pd.read_parquet(DATA / "cards.parquet")
    b = b.merge(cards[["bid", "wk"]], on="bid", how="left")
    wiki = json.loads((WEB / "wiki.json").read_text())
    names = b.osm_name.fillna(b["name"])
    label = [wiki[w]["label"] if w >= 0 and wiki[w].get("label") else n for w, n in zip(b.wk, names)]
    article = [((wiki[w].get("wiki") or {}).get("url") if w >= 0 else None) for w in b.wk]
    own_height = b.height_src.isin(list(HEIGHT_SRC))
    out = gpd.GeoDataFrame(dict(
        name=label,
        year=b.year, year_from=b.yfrom, year_to=b.yto,
        period=[PERIODS[p][1] for p in b.period],
        dating=b.date_flag.map(DATING), dating_source=b.date_src.map(SOURCE),
        heritage=[HERITAGE[h - 1] if h else None for h in b.heritage],
        listing=b.shr.fillna(b["item"]), conservation_area=b.hca,
        storeys=b.floors.where(b.floors_src == 0),
        height_m=b.height.where(own_height).round(1), height_source=b.height_src.map(HEIGHT_SRC),
        strata_plan=b.sp.map(lambda v: f"SP{int(v)}" if pd.notna(v) else None),
        lga=b.lga.str.title(), osm=b.osm, wikidata=b.qid, wikipedia=article,
        footprint=np.where(b.source == "osm", "OpenStreetMap", "Microsoft ML (via Overture)"),
    ), geometry=b.geometry, crs=CRS).to_crs(4326)
    out["geometry"] = shapely.set_precision(shapely.simplify(out.geometry.values, 0.000002), 1e-7)
    # Spatially ordered row groups, so a reader can fetch a view's buildings by range. Snappy, not zstd: the
    # RustGIS web app cannot read zstd-compressed Parquet.
    out = out.iloc[out.geometry.hilbert_distance().argsort()].reset_index(drop=True)
    GIS.mkdir(parents=True, exist_ok=True)
    out.to_parquet(GIS / "buildings.parquet", write_covering_bbox=True, row_group_size=3000, compression="snappy", index=False)
    return out


def polygons_geojson(name):
    """A land/water binary of the viewer (s04) back in lon/lat, as a GeoJSON FeatureCollection."""
    from pyproj import Transformer
    buf = (WEB / f"{name}.bin").read_bytes()
    n_poly, n_ring, n_vert = struct.unpack("<3I", buf[:12])
    o = 12
    ring_start = np.frombuffer(buf, "<u4", n_poly + 1, o); o += 4 * (n_poly + 1)
    vert_start = np.frombuffer(buf, "<u4", n_ring + 1, o); o += 4 * (n_ring + 1)
    xz = np.frombuffer(buf, "<f4", 2 * n_vert, o).reshape(-1, 2)
    gx, gy = gpo_mga()
    t = Transformer.from_crs(CRS, 4326, always_xy=True)
    feats = []
    for p in range(n_poly):
        rings = []
        for r in range(ring_start[p], ring_start[p + 1]):
            c = xz[vert_start[r]:vert_start[r + 1]]
            lon, lat = t.transform(c[:, 0] + gx, gy - c[:, 1])
            ring = [[round(x, 6), round(y, 6)] for x, y in zip(lon, lat)]
            rings.append(ring + ring[:1])
        feats.append(dict(type="Feature", properties={}, geometry=dict(type="Polygon", coordinates=rings)))
    return dict(type="FeatureCollection", features=feats)


def style(project: dict):
    """Colours as on the 3D map: the period ramp for the buildings, the harbour's grey-green."""
    for layer in project["maps"][0]["layers"]:
        r = layer.get("renderer", {})
        if "Unique" in r:
            colours = {label: rgb(c) for _, label, _, _, c in PERIODS}
            r["Unique"]["classes"] = [[label, dict(fill=colours[label] + [235], stroke=[int(v * 0.7) for v in colours[label]] + [255],
                                                   stroke_width=0.3, size=0.0, marker="Circle")]
                                      for _, label, _, _, _ in PERIODS]
        elif "Single" in r and layer["name"] == "Harbour":
            r["Single"].update(fill=list(WATER) + [255], stroke=list(WATER) + [255], stroke_width=0.0)
        elif "Single" in r and layer["name"] == "Area":
            r["Single"].update(fill=[0, 0, 0, 0], stroke=[30, 30, 30, 200], stroke_width=1.2)


def main():
    out = export_buildings()
    area = gpd.read_parquet(RAW / "boundary.parquet").to_crs(4326)
    area["name"] = area.lganame.str.title()
    (GIS / "area.geojson").write_text(area[["name", "geometry"]].to_json())
    (GIS / "harbour.geojson").write_text(json.dumps(polygons_geojson("water")))

    s = rustgis.Session(data=[GIS / "buildings.parquet"])
    s.run("project.rename", name="SydMap: Sydney, building by building")
    s.add_data(GIS / "harbour.geojson", name="Harbour")
    s.add_data(GIS / "area.geojson", name="Area")
    s.run("layer.symbology", layer="buildings", type="unique", field="period")
    s.run("map.basemap", name="blank")
    minx, miny, maxx, maxy = out.total_bounds
    s.run("map.zoomToExtent", extent=[minx, miny, maxx, maxy])
    project = json.loads(s.project_json())
    for layer in project["maps"][0]["layers"]:
        if layer["name"] == "buildings":
            layer["name"] = "Buildings by period"
    style(project)

    # The README's picture: rendered from the project as styled, features inline.
    r = rustgis.Session()
    r.run("project.openText", text=json.dumps(project))
    DOCS.mkdir(exist_ok=True)
    r.run("map.zoomToExtent", extent=[minx, miny, maxx, maxy])
    r.to_png(DOCS / "rustgis-period-map.png", width=1000, height=1500)

    # The page's project: the GeoParquet inside the project instead of 30,000 features as JSON, and the
    # OpenFreeMap basemap (the web app fetches its tiles; the offline renderer above does not need them).
    for layer in project["maps"][0]["layers"]:
        if layer["name"] == "Buildings by period":
            layer["dataset"]["features"] = []
            layer["source"] = dict(file_name="buildings.parquet",
                                   embedded=base64.b64encode((GIS / "buildings.parquet").read_bytes()).decode())
    p = rustgis.Session()
    p.run("project.openText", text=json.dumps(project))
    p.run("map.addTiles", url=BASEMAP, kind="style", name="OpenFreeMap Positron",
          attribution="OpenFreeMap © OpenMapTiles Data from OpenStreetMap")
    text = p.project_json()
    final = json.loads(text)
    for layer in final["maps"][0]["layers"]:
        if layer["name"] == "Buildings by period" and layer["dataset"].get("features"):
            layer["dataset"]["features"] = []   # read from the embedded file when the project opens
    (GIS / "sydney.rgis").write_text(json.dumps(final, separators=(",", ":")))
    print(f"{len(out)} buildings; buildings.parquet {(GIS / 'buildings.parquet').stat().st_size / 1e6:.1f} MB, "
          f"sydney.rgis {(GIS / 'sydney.rgis').stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
