"""Buildings: Overture footprints in the two LGAs, OpenStreetMap tags, heights and storeys.

Footprints come from Overture Maps, which merges OpenStreetMap with Microsoft's machine-learned footprints
where OSM has none. A footprint's height, in order of preference:
  0  measured: the OSM `height` tag (via Overture), or its parts' heights
  1  storeys: the OSM `building:levels` tag × 3.2 m
  2  modelled: GlobalBuildingAtlas (TUM), estimated from satellite imagery, matched by overlap
  3  assumed: 7 m, two storeys, when nothing else covers the footprint
Storeys are the OSM levels where tagged, otherwise the height divided by 3.2 m.

Output: data/buildings.parquet (one row per building) and data/parts.parquet (the 3D parts of the
buildings that OSM maps in detail; every other building is extruded from its footprint).
"""
import json

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from .config import CRS, DATA, RAW

STOREY = 3.2
MIN_AREA = 12.0          # m²; smaller footprints are sheds and slivers
OSM_KEYS = ["name", "building", "building:levels", "height", "start_date", "construction_date",
            "building:start_date", "wikidata", "wikipedia", "heritage", "heritage:operator", "amenity",
            "religion", "denomination", "architect", "building:architecture", "historic", "tourism",
            "addr:housenumber", "addr:street", "old_name", "operator", "shop", "office", "brand"]


def read_wkb(path, crs=4326) -> gpd.GeoDataFrame:
    df = pd.read_parquet(path)
    return gpd.GeoDataFrame(df, geometry=shapely.from_wkb(df.pop("geometry")), crs=crs)


def osm_tags() -> pd.DataFrame:
    d = json.loads((RAW / "osm_buildings.json").read_text())
    rows = []
    for e in d["elements"]:
        t = e.get("tags", {})
        rows.append(dict(osm=f'{e["type"][0]}{e["id"]}', **{k: t.get(k) for k in OSM_KEYS}))
    return pd.DataFrame(rows).drop_duplicates("osm").set_index("osm")


def osm_ref(records) -> str | None:
    """Overture's OSM record id ('w123@4') as 'w123'."""
    for r in records if records is not None else []:
        if r and r[0] in "wr" and r[1:2].isdigit():
            return r.split("@")[0]
    return None


def main():
    area = gpd.read_parquet(RAW / "boundary.parquet").to_crs(CRS)
    city = area.union_all()

    b = read_wkb(RAW / "overture_buildings.parquet").to_crs(CRS)
    b = b[~b.is_underground.fillna(False)]
    b = b[b.geometry.geom_type.isin(["Polygon", "MultiPolygon"])]
    b = b[b.representative_point().within(city)]
    b["geometry"] = shapely.make_valid(b.geometry.values)
    b = b[b.area >= MIN_AREA].copy()
    b["source"] = b.datasets.map(lambda d: "osm" if d is not None and "OpenStreetMap" in list(d) else "ml")
    b["osm"] = b.records.map(osm_ref)
    lga = gpd.sjoin(gpd.GeoDataFrame(geometry=b.representative_point(), index=b.index, crs=CRS),
                    area[["lganame", "geometry"]], predicate="within")
    b["lga"] = lga.lganame[~lga.index.duplicated()]

    tags = osm_tags()
    b = b.join(tags, on="osm")

    # Parts: Overture keeps OSM's building:part pieces with their own heights.
    q = read_wkb(RAW / "overture_parts.parquet").to_crs(CRS)
    q = q[q.building_id.isin(b.id) & q.geometry.geom_type.isin(["Polygon", "MultiPolygon"])].copy()
    q["geometry"] = shapely.make_valid(q.geometry.values)
    q["height"] = q.height.fillna(q.num_floors * STOREY)
    q["base"] = q.min_height.fillna(q.min_floor * STOREY).fillna(0.0)
    q = q[q.height.notna() & (q.height > q.base)]

    # Heights.
    b["height_src"] = np.where(b.height.notna(), 0, np.where(b.num_floors.notna(), 1, -1))
    b["height"] = b.height.fillna(b.num_floors * STOREY)
    part_top = q.groupby("building_id").height.max()
    has = b.id.isin(part_top.index)
    b.loc[has, "height"] = np.fmax(b.loc[has, "height"].fillna(0), b.loc[has, "id"].map(part_top))
    b.loc[has & (b.height_src < 0), "height_src"] = 0

    # GlobalBuildingAtlas: the modelled footprint that overlaps each remaining building most.
    need = b[b.height.isna()]
    g = read_wkb(RAW / "gba.parquet").to_crs(CRS)
    g = g[g.height > 0]
    j = gpd.sjoin(need[["geometry"]], g[["height", "geometry"]].rename(columns={"height": "gba_h"}), predicate="intersects")
    inter = shapely.area(shapely.intersection(need.geometry.loc[j.index].values, g.geometry.loc[j.index_right].values))
    j["share"] = inter / need.area.loc[j.index].values
    j = j[j.share > 0.3].sort_values("share").groupby(level=0).last()
    b.loc[j.index, "height"] = j.gba_h.clip(2.5, 80)  # the model is not trusted for towers it has no OSM for
    b.loc[j.index, "height_src"] = 2
    b.loc[b.height.isna(), "height_src"] = 3
    b["height"] = b.height.fillna(2 * STOREY + 0.6).clip(2.5, 320)

    b["floors_src"] = np.where(b.num_floors.notna(), 0, 1)
    b["floors"] = b.num_floors.fillna(np.round(b.height / STOREY)).clip(1, 99).astype(int)

    b = b.reset_index(drop=True)
    b["bid"] = np.arange(len(b))
    keep = ["bid", "id", "osm", "source", "lga", "height", "height_src", "floors", "floors_src", "name",
            "class", "subtype", "roof_shape", "has_parts", *[k for k in OSM_KEYS if k != "name" and k in b], "geometry"]
    b = b[[c for c in dict.fromkeys(keep) if c in b.columns]]
    b.columns = [c.replace(":", "_") for c in b.columns]
    b.to_parquet(DATA / "buildings.parquet")
    q = q.merge(b[["id", "bid"]], left_on="building_id", right_on="id")[["bid", "height", "base", "geometry"]]
    q.to_parquet(DATA / "parts.parquet")
    print(f"{len(b)} buildings ({(b.source == 'osm').sum()} OSM, {(b.source == 'ml').sum()} ML); {len(q)} parts")
    print("height sources:", b.height_src.value_counts().sort_index().to_dict())
    print("by LGA:", b.lga.value_counts().to_dict())


if __name__ == "__main__":
    main()
