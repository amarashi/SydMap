"""Open data: every building, with its year and the evidence for it, to download from the page's Notes.

  web/data/download/buildings.parquet   every building as GeoParquet (EPSG:4326): its footprint, year, the evidence
                                        for it, age, heritage and sources. ODbL (it derives from OpenStreetMap).
  web/data/download/buildings.csv       the same, one row per building, with a point inside each footprint instead of
                                        the footprint, for spreadsheets.
  web/data/download/area.geojson        the boundaries of the City of Sydney and North Sydney.

Heights modelled by GlobalBuildingAtlas (CC BY-NC) are left out of all three.
"""
import json

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from .config import CRS, DATA, RAW, WEB
from .periods import PERIODS
from .s03_tiles import HERITAGE

OUT = WEB / "download"
DATING = {0: "documented", 1: "documented, approximate", 2: "strata plan", 3: "heritage area estimate",
          4: "estimated from neighbours"}
SOURCE = {"wikidata": "Wikidata", "wikipedia": "Wikipedia", "osm": "OpenStreetMap", "strata": "NSW cadastre",
          "listing": "its heritage listing (Wikipedia)",
          "heritage": "heritage area", "tall": "neighbours", "detracting": "neighbours", "low-rise": "neighbours",
          "other": "neighbours"}
HEIGHT_SRC = {0: "OpenStreetMap", 1: "OpenStreetMap storeys", 4: "Wikipedia"}


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
    # Spatially ordered row groups, so a reader can fetch an area's buildings by range. Snappy, which every Parquet
    # reader can read.
    out = out.iloc[out.geometry.hilbert_distance().argsort()].reset_index(drop=True)
    OUT.mkdir(parents=True, exist_ok=True)
    out.to_parquet(OUT / "buildings.parquet", write_covering_bbox=True, row_group_size=3000, compression="snappy", index=False)
    return out


def write_csv(out: gpd.GeoDataFrame):
    """The buildings for spreadsheets: every column but the footprint, and a point inside each footprint."""
    point = out.geometry.representative_point()
    table = pd.DataFrame(out.drop(columns="geometry"))
    table["storeys"] = table.storeys.astype("Int64")
    table.insert(1, "longitude", point.x.round(6))
    table.insert(2, "latitude", point.y.round(6))
    table.to_csv(OUT / "buildings.csv", index=False)


def main():
    out = export_buildings()
    write_csv(out)
    area = gpd.read_parquet(RAW / "boundary.parquet").to_crs(4326)
    area["name"] = area.lganame.str.title()
    (OUT / "area.geojson").write_text(area[["name", "geometry"]].to_json())
    sizes = ", ".join(f"{f.name} {f.stat().st_size / 1e6:.1f} MB" for f in sorted(OUT.iterdir()))
    print(f"{len(out)} buildings; {sizes}")


if __name__ == "__main__":
    main()
