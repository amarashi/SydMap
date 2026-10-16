"""Download every raw input into data/raw/. Each source is fetched once; delete its file to fetch it again.

    uv run python -m pipeline.s00_fetch            # everything
    uv run python -m pipeline.s00_fetch osm wiki   # some of it

Sources (all open; see README for the licences):
  boundary   NSW Spatial Services, administrative boundaries: the LGAs, and the suburbs kept of those taken in part
  suburbs    NSW Spatial Services: every suburb in the box, for the Suburbs lens
  stats      the suburbs' figures: ABS Census DataPacks by suburb (2011, 2016, 2021), BOCSAR crime by suburb, DCJ
             sale prices by postcode
  overture   Overture Maps buildings, building parts, land and water (OSM and Microsoft ML footprints)
  gba        GlobalBuildingAtlas LoD1 (TUM): a modelled height for every footprint
  osm        OpenStreetMap through Overpass: building tags, named roads and water, worship, pubs
  wiki       Wikidata: items with coordinates in the area, their dates, architects, styles and images
  cos        City of Sydney open data: heritage building contributions, Aboriginal history places,
             Developing Sydney photos
  heritage   NSW State Heritage Register curtilages and the local environmental plans' heritage maps
  cadastre   NSW cadastre: strata plan lots
"""
import json
import os
import sys
import time

import requests

from . import arcgis
from .config import BBOX, LGAS, PARTS, RAW, UA

NSW_ADMIN = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer/8"
NSW_SUBURB = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Administrative_Boundaries_Theme/FeatureServer/2"
NSW_LOT = "https://portal.spatial.nsw.gov.au/server/rest/services/NSW_Land_Parcel_Property_Theme/FeatureServer/8"
COS = "https://services1.arcgis.com/cNVyNtjGVZybOQWZ/arcgis/rest/services"
SHR = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/EDP/SHR_Curtilage/MapServer/0"
EPI_HERITAGE = "https://mapprod3.environment.nsw.gov.au/arcgis/rest/services/Planning/EPI_Primary_Planning_Layers/MapServer/0"
OVERTURE = "s3://overturemaps-us-west-2/release/2026-09-23.1"
GBA = "s3://us-west-2.opendata.source.coop/tge-labs/globalbuildingatlas-lod1/e150_s30_e155_s35.parquet"
OVERPASS = ["https://overpass-api.de/api/interpreter", "https://overpass.private.coffee/api/interpreter",
            "https://maps.mail.ru/osm/tools/overpass/api/interpreter"]
SPARQL = "https://query.wikidata.org/sparql"


def done(path) -> bool:
    if path.exists():
        print(f"  {path} (cached)")
        return True
    path.parent.mkdir(parents=True, exist_ok=True)
    return False


# ---------------------------------------------------------------- boundary

def boundary():
    p = RAW / "boundary.parquet"
    if done(p):
        return
    import pandas as pd
    import shapely
    sql = lambda names: ",".join(f"'{n}'" for n in names)
    area = arcgis.query(NSW_ADMIN, where=f"lganame IN ({sql([*LGAS, *PARTS])})", out_fields="lganame,councilname")
    # A council taken in part keeps its name, over only its kept suburbs (clipped to it, as suburbs can cross councils).
    for lga, suburbs in PARTS.items():
        s = arcgis.query(NSW_SUBURB, where=f"suburbname IN ({sql(suburbs)})", out_fields="suburbname")
        missing = set(suburbs) - set(s.suburbname)
        assert not missing, f"no such suburbs: {missing}"
        m = area.lganame == lga
        area.loc[m, "geometry"] = [shapely.make_valid(g.intersection(s.union_all())) for g in area.geometry[m]]
    arcgis.save(pd.concat([area[area.lganame.isin(LGAS)], area[area.lganame.isin(PARTS)]], ignore_index=True), p)


def suburbs():
    # Every suburb in the box, whole: the suburb statistics are for the whole suburb (s10_suburbs keeps those with
    # buildings on the map).
    p = RAW / "suburbs.parquet"
    if done(p):
        return
    arcgis.save(arcgis.query(NSW_SUBURB, bbox=BBOX, out_fields="suburbname,postcode"), p)


# ---------------------------------------------------------------- suburb statistics

ABS_PACKS = "https://www.abs.gov.au/census/find-census-data/datapacks/download"
DCJ = "https://dcj.nsw.gov.au"
DCJ_REPORTS = f"{DCJ}/about-us/families-and-communities-statistics/housing-rent-and-sales"


def stats():
    # The census by suburb, crime by suburb and sale prices by postcode, for s10_suburbs. Each file is fetched once.
    files = {"abs_census_2011_ssc/2011_BCP_SSC_for_NSW_short-header.zip": f"{ABS_PACKS}/2011_BCP_SSC_for_NSW_short-header.zip",
             "abs_census_2016_ssc/2016_GCP_SSC_for_NSW_short-header.zip": f"{ABS_PACKS}/2016_GCP_SSC_for_NSW_short-header.zip",
             "abs_census_gcp_2021/2021_GCP_SAL_for_NSW_short-header.zip": f"{ABS_PACKS}/2021_GCP_SAL_for_NSW_short-header.zip",
             "bocsar/SuburbData.zip": "https://bocsarblob.blob.core.windows.net/bocsar-open-data/SuburbData.zip"}
    # DCJ's Rent and Sales Report: a spreadsheet of sales by postcode each quarter since June 2017 (earlier issues are
    # PDFs), named differently from issue to issue, so read their links off the report's pages.
    import re
    for page in (f"{DCJ_REPORTS}/rent-and-sales-report.html", f"{DCJ_REPORTS}/previous-rent-and-sales-reports.html"):
        html = requests.get(page, headers={"User-Agent": "Mozilla/5.0"}, timeout=120).text
        for href in re.findall(r'href="([^"]+\.xlsx)"', html):
            name = href.rsplit("/", 1)[-1]
            if "sales" in name.lower() and "rent" not in name.lower():
                files[f"dcj_rent_sales/{name}"] = DCJ + href
    for rel, url in files.items():
        p = RAW / "stats" / rel
        if done(p):
            continue
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=600)
        r.raise_for_status()
        p.write_bytes(r.content)
        print(f"  {p}: {len(r.content) / 1e6:.1f} MB")


# ---------------------------------------------------------------- Overture and GlobalBuildingAtlas

def duck():
    import duckdb
    # The container injects placeholder AWS keys; these buckets are public, so ask anonymously.
    for k in ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN"):
        os.environ.pop(k, None)
    con = duckdb.connect()
    con.sql("INSTALL httpfs; LOAD httpfs; INSTALL spatial; LOAD spatial;")
    con.sql("CREATE SECRET anon (TYPE S3, KEY_ID '', SECRET '', REGION 'us-west-2', URL_STYLE 'path')")
    return con


def in_bbox(col="bbox"):
    x0, y0, x1, y1 = BBOX
    return f"{col}.xmin > {x0} AND {col}.xmax < {x1} AND {col}.ymin > {y0} AND {col}.ymax < {y1}"


def overture():
    con = None
    jobs = {
        "overture_buildings.parquet": f"""SELECT id, names.primary AS name, class, subtype, height, num_floors,
              min_height, min_floor, roof_shape, has_parts, is_underground, facade_material, roof_material,
              list_transform(sources, s -> s.dataset) AS datasets,
              list_transform(sources, s -> s.record_id) AS records,
              ST_AsWKB(geometry) AS geometry
            FROM read_parquet('{OVERTURE}/theme=buildings/type=building/*') WHERE {in_bbox()}""",
        "overture_parts.parquet": f"""SELECT id, building_id, height, num_floors, min_height, min_floor, roof_shape,
              list_transform(sources, s -> s.record_id) AS records, ST_AsWKB(geometry) AS geometry
            FROM read_parquet('{OVERTURE}/theme=buildings/type=building_part/*') WHERE {in_bbox()}""",
        "overture_water.parquet": f"""SELECT id, names.primary AS name, subtype, class, is_salt, is_intermittent,
              ST_AsWKB(geometry) AS geometry
            FROM read_parquet('{OVERTURE}/theme=base/type=water/*')
            WHERE bbox.xmax > {BBOX[0]} AND bbox.xmin < {BBOX[2]} AND bbox.ymax > {BBOX[1]} AND bbox.ymin < {BBOX[3]}
              AND ST_GeometryType(geometry) IN ('POLYGON', 'MULTIPOLYGON')""",
        "overture_land.parquet": f"""SELECT id, subtype, class, ST_AsWKB(geometry) AS geometry
            FROM read_parquet('{OVERTURE}/theme=base/type=land/*')
            WHERE bbox.xmax > {BBOX[0]} AND bbox.xmin < {BBOX[2]} AND bbox.ymax > {BBOX[1]} AND bbox.ymin < {BBOX[3]}
              AND ST_GeometryType(geometry) IN ('POLYGON', 'MULTIPOLYGON')""",
    }
    for name, sql in jobs.items():
        p = RAW / name
        if done(p):
            continue
        con = con or duck()
        t = time.time()
        con.sql(f"COPY ({sql}) TO '{p}' (FORMAT parquet)")
        print(f"  {p}: {con.sql(f'SELECT count(*) FROM read_parquet(\'{p}\')').fetchone()[0]} rows, {time.time() - t:.0f} s")


def gba():
    p = RAW / "gba.parquet"
    if done(p):
        return
    con = duck()
    con.sql(f"""COPY (SELECT source, id, height, var, ST_AsWKB(geometry) AS geometry FROM read_parquet('{GBA}')
                WHERE {in_bbox()}) TO '{p}' (FORMAT parquet)""")
    print(f"  {p}: {con.sql(f'SELECT count(*) FROM read_parquet(\'{p}\')').fetchone()[0]} rows")


# ---------------------------------------------------------------- OpenStreetMap

def overpass(q: str) -> dict:
    last = None
    for attempt in range(8):
        url = OVERPASS[attempt % len(OVERPASS)]
        try:
            r = requests.post(url, data={"data": q}, headers={"User-Agent": UA}, timeout=400)
            if r.status_code == 200 and r.text.lstrip().startswith("{"):
                return r.json()
            last = f"{r.status_code} {r.text[:200]}"
        except Exception as e:  # noqa: BLE001
            last = e
        print(f"  overpass retry ({url}): {last}")
        time.sleep(5 * (attempt + 1))
    raise RuntimeError(f"Overpass failed: {last}")


def osm():
    s, w, n, e = BBOX[1], BBOX[0], BBOX[3], BBOX[2]
    bb = f"({s},{w},{n},{e})"
    jobs = {
        # Tags of every building and building part; geometry comes from Overture, joined on the way id.
        "osm_buildings.json": f'[out:json][timeout:300];(way["building"]{bb};relation["building"]{bb};'
                              f'way["building:part"]{bb};relation["building:part"]{bb};);out tags center;',
        # Named streets and water for labels.
        "osm_streets.json": f'[out:json][timeout:300];way["highway"~"^(motorway|trunk|primary|secondary|tertiary|'
                            f'unclassified|residential|living_street|pedestrian)$"]["name"]{bb};out tags geom;',
        "osm_water.json": f'[out:json][timeout:300];(way["natural"~"^(water|bay|strait)$"]["name"]{bb};'
                          f'relation["natural"~"^(water|bay|strait)$"]["name"]{bb};node["natural"~"^(bay|strait)$"]["name"]{bb};'
                          f'way["waterway"]["name"]{bb};);out tags geom;',
        # Points of interest that make context layers: worship, pubs, and anything with a start date.
        "osm_pois.json": f'[out:json][timeout:300];(nwr["amenity"~"^(place_of_worship|pub|theatre|library|school|'
                         f'hospital|fire_station|police|townhall|courthouse|post_office)$"]{bb};'
                         f'nwr["historic"]{bb};nwr["heritage"]{bb};);out tags center;',
    }
    for name, q in jobs.items():
        p = RAW / name
        if done(p):
            continue
        d = overpass(q)
        p.write_text(json.dumps(d))
        print(f"  {p}: {len(d.get('elements', []))} elements")


# ---------------------------------------------------------------- Wikidata

WD_QUERY = """
SELECT ?item ?itemLabel ?coord ?inception ?incprec ?opened ?openprec ?demolished ?shr ?osmway ?osmrel ?image ?article ?heritage ?heritageLabel
       (GROUP_CONCAT(DISTINCT ?classLabel; separator="|") AS ?classes)
       (GROUP_CONCAT(DISTINCT ?architectLabel; separator="|") AS ?architects)
       (GROUP_CONCAT(DISTINCT ?styleLabel; separator="|") AS ?styles)
WHERE {
  SERVICE wikibase:box {
    ?item wdt:P625 ?coord .
    bd:serviceParam wikibase:cornerWest "Point(%(w)s %(n)s)"^^geo:wktLiteral .
    bd:serviceParam wikibase:cornerEast "Point(%(e)s %(s)s)"^^geo:wktLiteral .
  }
  OPTIONAL { ?item p:P571/psv:P571 [ wikibase:timeValue ?inception ; wikibase:timePrecision ?incprec ] . }
  OPTIONAL { ?item p:P1619/psv:P1619 [ wikibase:timeValue ?opened ; wikibase:timePrecision ?openprec ] . }
  OPTIONAL { ?item wdt:P576 ?demolished . }
  OPTIONAL { ?item wdt:P3449 ?shr . }
  OPTIONAL { ?item wdt:P10689 ?osmway . }
  OPTIONAL { ?item wdt:P402 ?osmrel . }
  OPTIONAL { ?item wdt:P18 ?image . }
  OPTIONAL { ?item wdt:P1435 ?heritage . }
  OPTIONAL { ?item wdt:P31 ?class . ?class rdfs:label ?classLabel . FILTER(LANG(?classLabel) = "en") }
  OPTIONAL { ?item wdt:P84 ?architect . ?architect rdfs:label ?architectLabel . FILTER(LANG(?architectLabel) = "en") }
  OPTIONAL { ?item wdt:P149 ?style . ?style rdfs:label ?styleLabel . FILTER(LANG(?styleLabel) = "en") }
  OPTIONAL { ?article schema:about ?item ; schema:isPartOf <https://en.wikipedia.org/> . }
  SERVICE wikibase:label { bd:serviceParam wikibase:language "en". }
}
GROUP BY ?item ?itemLabel ?coord ?inception ?incprec ?opened ?openprec ?demolished ?shr ?osmway ?osmrel ?image ?article ?heritage ?heritageLabel
"""


def sparql(q: str) -> list[dict]:
    for attempt in range(5):
        try:
            r = requests.post(SPARQL, data={"query": q}, headers={"User-Agent": UA,
                              "Accept": "application/sparql-results+json"}, timeout=300)
            r.raise_for_status()
            return r.json()["results"]["bindings"]
        except Exception as e:  # noqa: BLE001
            print(f"  sparql retry: {e}")
            time.sleep(10 * (attempt + 1))
    raise RuntimeError("Wikidata query failed")


def wiki():
    p = RAW / "wikidata.json"
    if done(p):
        return
    rows = []
    # Ten strips keep each query well inside the endpoint's time limit.
    x0, y0, x1, y1 = BBOX
    n = 10
    step = (x1 - x0) / n
    for i in range(n):
        q = WD_QUERY % dict(w=x0 + i * step, e=x0 + (i + 1) * step, s=y0, n=y1)
        part = sparql(q)
        print(f"  strip {i}: {len(part)} rows")
        rows += part
    flat = [{k: v["value"] for k, v in r.items()} for r in rows]
    p.write_text(json.dumps(flat, ensure_ascii=False))
    print(f"  {p}: {len(flat)} rows, {len({r['item'] for r in flat})} items")


WIKI_API = "https://en.wikipedia.org/w/api.php"


def wiki_get(params: dict) -> dict:
    """One Wikipedia API call, patient with rate limits (the shared egress gets 429s)."""
    for attempt in range(12):
        r = requests.get(WIKI_API, params=dict(params, format="json", formatversion=2, maxlag=5),
                         headers={"User-Agent": UA}, timeout=60)
        if r.status_code == 200:
            return r.json()
        wait = float(r.headers.get("retry-after") or 5 * (attempt + 1))
        print(f"  wikipedia {r.status_code}, waiting {wait:.0f} s")
        time.sleep(wait + 1)
    r.raise_for_status()
    return {}


def wikipedia():
    """Lead sections of the English Wikipedia articles of every Wikidata item in the box."""
    p = RAW / "wikipedia.json"
    if done(p):
        return
    from urllib.parse import unquote
    items = json.loads((RAW / "wikidata.json").read_text())
    titles = sorted({unquote(r["article"].rsplit("/wiki/", 1)[1]).replace("_", " ")
                     for r in items if r.get("article")})
    out = {}
    for k in range(0, len(titles), 20):
        batch = titles[k:k + 20]
        d = wiki_get(dict(action="query", prop="extracts|info", exintro=1, explaintext=1, inprop="url",
                          titles="|".join(batch), redirects=1))
        back = {n["to"]: n["from"] for n in d.get("query", {}).get("redirects", [])}
        back.update({n["to"]: n["from"] for n in d.get("query", {}).get("normalized", [])})
        for page in d.get("query", {}).get("pages", []):
            t = page.get("title")
            out[back.get(t, t)] = dict(title=t, extract=page.get("extract", ""), url=page.get("fullurl"))
        print(f"  {min(k + 20, len(titles))}/{len(titles)}")
        time.sleep(1.0)
    p.write_text(json.dumps(out, ensure_ascii=False))
    print(f"  {p}: {len(out)} articles")


# ---------------------------------------------------------------- City of Sydney, heritage, cadastre

def cos():
    jobs = {
        "cos_contributions.parquet": (f"{COS}/Sydney_Development_Control_Plan_2012/FeatureServer/2", True),
        "cos_localities.parquet": (f"{COS}/Sydney_Development_Control_Plan_2012/FeatureServer/11", True),
        "cos_aboriginal.parquet": (f"{COS}/Aboriginal_history_places/FeatureServer/0", True),
        "cos_developing.parquet": (f"{COS}/Developing_Sydney/FeatureServer/0", True),
    }
    for name, (url, geom) in jobs.items():
        p = RAW / name
        if not done(p):
            arcgis.save(arcgis.query(url, geometry=geom, page=2000), p)


def heritage():
    p = RAW / "shr.parquet"
    if not done(p):
        arcgis.save(arcgis.query(SHR, bbox=BBOX, page=1000), p)
    p = RAW / "epi_heritage.parquet"
    if not done(p):
        arcgis.save(arcgis.query(EPI_HERITAGE, bbox=BBOX, page=1000), p)


def cadastre():
    p = RAW / "strata_lots.parquet"
    if done(p):
        return
    # Strata plans (SP) only. The service gives up on the whole box at once, so ask for it in cells.
    import pandas as pd
    import geopandas as gpd
    x0, y0, x1, y1 = BBOX
    n = 12
    frames = []
    for i in range(n):
        for k in range(n):
            cell = (x0 + (x1 - x0) * i / n, y0 + (y1 - y0) * k / n, x0 + (x1 - x0) * (i + 1) / n, y0 + (y1 - y0) * (k + 1) / n)
            part = arcgis.query(NSW_LOT, where="planlabel LIKE 'SP%'", out_fields="cadid,planlabel,plannumber,lotnumber,createdate",
                                bbox=cell, page=1000, esri_json=True)
            frames.append(part)
            print(f"  cell {i},{k}: {len(part)}")
    lots = gpd.GeoDataFrame(pd.concat([f for f in frames if len(f)], ignore_index=True), crs=4326)
    arcgis.save(lots.drop_duplicates("cadid"), p)


STEPS = dict(boundary=boundary, suburbs=suburbs, stats=stats, overture=overture, gba=gba, osm=osm, wiki=wiki, wikipedia=wikipedia, cos=cos, heritage=heritage,
             cadastre=cadastre)

if __name__ == "__main__":
    for name in sys.argv[1:] or STEPS:
        print(name)
        STEPS[name]()
