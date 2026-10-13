"""Paged queries against ArcGIS REST feature and map services, returned as GeoDataFrames."""
import json
import time

import geopandas as gpd
import pandas as pd
import requests
import shapely

from .config import UA


def esri_geometry(g):
    """An Esri JSON geometry as shapely: rings that turn clockwise are shells, the others holes."""
    if not g:
        return None
    if "x" in g:
        return shapely.Point(g["x"], g["y"])
    if "paths" in g:
        return shapely.MultiLineString(g["paths"])
    shells, holes = [], []
    for ring in g.get("rings", []):
        if len(ring) < 4:
            continue
        lr = shapely.LinearRing(ring)
        (holes if lr.is_ccw else shells).append(shapely.Polygon(lr))
    polys = []
    for s in shells:
        inner = [h.exterior for h in holes if s.contains(h.representative_point())]
        polys.append(shapely.Polygon(s.exterior, inner))
    return shapely.make_valid(shapely.MultiPolygon(polys)) if polys else None


def query(layer_url: str, where: str = "1=1", out_fields: str = "*", bbox=None, out_sr: int = 4326,
          page: int = 1000, geometry: bool = True, params: dict | None = None,
          esri_json: bool = False) -> gpd.GeoDataFrame | pd.DataFrame:
    """Every feature of `layer_url` matching `where` (and the lon/lat `bbox`), in `out_sr`.
    `esri_json` asks for Esri JSON instead of GeoJSON, for services that fail on the latter."""
    base = dict(where=where, outFields=out_fields, outSR=out_sr, f="geojson" if geometry and not esri_json else "json",
                returnGeometry=str(geometry).lower(), resultRecordCount=page)
    if bbox:
        base.update(geometry=",".join(map(str, bbox)), geometryType="esriGeometryEnvelope", inSR=4326,
                    spatialRel="esriSpatialRelIntersects")
    base.update(params or {})
    frames, offset = [], 0
    while True:
        for attempt in range(5):
            try:
                r = requests.get(f"{layer_url}/query", params=dict(base, resultOffset=offset),
                                 headers={"User-Agent": UA}, timeout=180)
                r.raise_for_status()
                d = r.json()
                if "error" in d:
                    raise RuntimeError(d["error"])
                break
            except Exception as e:  # noqa: BLE001 - network hiccups: retry with backoff
                if attempt == 4:
                    raise
                print(f"  retry {layer_url} @{offset}: {e}")
                time.sleep(2 ** attempt)
        feats = d.get("features", [])
        if geometry and esri_json:
            if feats:
                frames.append(gpd.GeoDataFrame([f["attributes"] for f in feats],
                                               geometry=[esri_geometry(f.get("geometry")) for f in feats], crs=out_sr))
        elif geometry:
            if feats:
                frames.append(gpd.GeoDataFrame.from_features(feats, crs=out_sr))
        else:
            frames.append(pd.DataFrame([f["attributes"] for f in feats]))
        exceeded = d.get("exceededTransferLimit") or d.get("properties", {}).get("exceededTransferLimit")
        if not feats or (not exceeded and len(feats) < page):
            break
        offset += len(feats)
    if not frames:
        return gpd.GeoDataFrame(geometry=[], crs=out_sr) if geometry else pd.DataFrame()
    out = pd.concat(frames, ignore_index=True)
    return gpd.GeoDataFrame(out, geometry="geometry", crs=out_sr) if geometry else out


def save(df, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    if isinstance(df, gpd.GeoDataFrame):
        df.to_parquet(path)
    else:
        df.to_parquet(path)
    print(f"  {path}: {len(df)} rows")
