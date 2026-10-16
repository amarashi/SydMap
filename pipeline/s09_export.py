"""Open data: every building, with its year and the evidence for it, to download from the page's Notes.

  web/data/download/<council>.parquet   every building as GeoParquet (EPSG:4326): its footprint, year, the evidence
                                        for it, age, heritage and sources. ODbL (it derives from OpenStreetMap).
  web/data/download/<council>.csv       the same, one row per building, with a point inside each footprint instead of
                                        the footprint, for spreadsheets.
  web/data/download/area.geojson        the boundaries of the councils on the map.

There is a pair of files for each council, because Cloudflare serves no file over 25 MiB and one file for the whole
map would pass that as the map grows. The list of them in the page's Notes (index.html, between the DOWNLOADS
comments) is written here too. Heights modelled by GlobalBuildingAtlas (CC BY-NC) are left out of all of them.
"""
import html
import json
import re

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from .config import CRS, DATA, PARTS, RAW, WEB
from .periods import PERIODS
from .s03_tiles import HERITAGE

OUT = WEB / "download"
DATING = {0: "documented", 1: "documented, approximate", 2: "strata plan", 3: "heritage area estimate",
          4: "estimated from neighbours"}
SOURCE = {"wikidata": "Wikidata", "wikipedia": "Wikipedia", "osm": "OpenStreetMap", "strata": "NSW cadastre",
          "listing": "its heritage listing (Wikipedia)",
          "heritage": "heritage area", "tall": "neighbours", "detracting": "neighbours", "low-rise": "neighbours", "untagged": "neighbours",
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
    return out.iloc[out.geometry.hilbert_distance().argsort()].reset_index(drop=True)


def slug(lga: str) -> str:
    return re.sub(r"[^a-z]+", "-", lga.lower()).strip("-")


def write_council(out: gpd.GeoDataFrame, name: str):
    """One council's buildings: GeoParquet with the footprints, and CSV for spreadsheets with every column but the
    footprint and a point inside each footprint instead."""
    out.to_parquet(OUT / f"{name}.parquet", write_covering_bbox=True, row_group_size=3000, compression="snappy",
                   index=False)
    point = out.geometry.representative_point()
    table = pd.DataFrame(out.drop(columns="geometry"))
    table["storeys"] = table.storeys.astype("Int64")
    table.insert(1, "longitude", point.x.round(6))
    table.insert(2, "latitude", point.y.round(6))
    table.to_csv(OUT / f"{name}.csv", index=False)


def mb(name: str) -> str:
    return f"{(OUT / name).stat().st_size / 1e6:.1f} MB"


def write_list(councils: list[tuple[str, str, int]]):
    """The downloads in the page's Notes: a CSV and a GeoParquet for each council, then the boundaries."""
    def where(title):  # a council taken in part names its suburbs
        suburbs = PARTS.get(title.upper())
        return f" in {', '.join(suburbs[:-1]).title()} and {suburbs[-1].title()}" if suburbs else ""

    rows = [f'      <li><b>{html.escape(title)}</b> <span>{n:,} buildings{where(title)}: '
            f'<a href="data/download/{name}.csv" download>CSV</a> {mb(name + ".csv")}, '
            f'<a href="data/download/{name}.parquet" download>GeoParquet</a> {mb(name + ".parquet")}</span></li>'
            for title, name, n in councils]
    rows.append('      <li><b>The area’s boundaries</b> <span>'
                f'<a href="data/download/area.geojson" download>GeoJSON</a>, by council, {mb("area.geojson")}</span></li>')
    page = WEB.parent / "index.html"
    t = page.read_text(encoding="utf-8")
    t, n = re.subn(r"(<!-- DOWNLOADS -->).*?(<!-- /DOWNLOADS -->)",
                   lambda m: "\n".join([m[1], *rows, "      " + m[2]]), t, flags=re.S)
    assert n == 1, "index.html has no DOWNLOADS block"
    page.write_text(t, encoding="utf-8", newline="")


def main():
    out = export_buildings()
    OUT.mkdir(parents=True, exist_ok=True)
    for old in [*OUT.glob("*.csv"), *OUT.glob("*.parquet")]:
        old.unlink()
    councils = []
    for lga, part in out.groupby("lga", sort=False):
        write_council(part.reset_index(drop=True), slug(lga))
        councils.append((lga, slug(lga), len(part)))
    councils.sort(key=lambda c: c[0])
    area = gpd.read_parquet(RAW / "boundary.parquet").to_crs(4326)
    area["name"] = area.lganame.str.title()
    for lga, suburbs in PARTS.items():  # a council taken in part says which part
        area.loc[area.lganame == lga, "name"] += f" ({', '.join(suburbs).title()} only)"
    (OUT / "area.geojson").write_text(area[["name", "geometry"]].to_json())
    write_list(councils)
    sizes = ", ".join(f"{f.name} {f.stat().st_size / 1e6:.1f} MB" for f in sorted(OUT.iterdir()))
    print(f"{len(out)} buildings; {sizes}")


if __name__ == "__main__":
    main()
