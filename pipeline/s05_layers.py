"""Context layers: sets of buildings, each with a story, resolved to bits of a 64-bit mask per building.

A layer has one or more groups; every group takes one bit. Each layer's source function returns
{bid: group} or {bid: (group, note)}; a note is the story behind a building ({name, story, source}).
Writes data/layers.parquet (lay0, lay1 per building) and web/data/layers.json (the catalogue).
"""
import json
import re
from collections import Counter

import geopandas as gpd
import numpy as np
import pandas as pd

from .config import CRS, DATA, RAW, WEB
from .s02_years import wikidata_items
from .s03_tiles import to_local

LAYERS = []


def layer(**meta):
    def wrap(fn):
        LAYERS.append(dict(meta, source_fn=fn))
        return fn
    return wrap


_B = None


def buildings() -> gpd.GeoDataFrame:
    global _B
    if _B is None:
        _B = gpd.read_parquet(DATA / "buildings_dated.parquet")
    return _B


def at_points(points: gpd.GeoDataFrame, radius: float = 20.0) -> pd.DataFrame:
    """For each point: the building it falls in, else the nearest within `radius` metres."""
    b = buildings()
    pts = points.to_crs(CRS)
    j = gpd.sjoin_nearest(pts, b[["bid", "geometry"]], max_distance=radius, distance_col="d")
    return j[~j.index.duplicated()]


def osm_elements(name):
    p = RAW / name
    return json.loads(p.read_text())["elements"] if p.exists() else []


def osm_points(name, test) -> gpd.GeoDataFrame:
    rows = []
    for e in osm_elements(name):
        t = e.get("tags", {})
        c = e.get("center") or ({"lat": e["lat"], "lon": e["lon"]} if "lat" in e else None)
        if c and test(t):
            rows.append(dict(t, osm=f'{e["type"][0]}{e["id"]}', lon=c["lon"], lat=c["lat"]))
    df = pd.DataFrame(rows)
    if df.empty:
        return gpd.GeoDataFrame(df, geometry=[], crs=4326)
    return gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df.lon, df.lat), crs=4326)


# ---------------------------------------------------------------- Country

@layer(id="aboriginal", section="Country", title="Aboriginal Sydney", era="1788–today",
       text=("Places with historical associations for Aboriginal and Torres Strait Islander people in Sydney, from "
             "first contact around the harbour to the fight for civil rights in Redfern. Each story is told on Barani, "
             "the City of Sydney's Aboriginal history site."),
       caveat="Only the places that stand in or beside a building today appear on the map; many others are shores, parks and streets.",
       source=("City of Sydney, Aboriginal history places (Barani), CC BY 4.0",
               "https://data.cityofsydney.nsw.gov.au/datasets/cityofsydney::aboriginal-history-places"),
       groups=[("Early Contact", "Early contact"), ("Civil Rights", "Civil rights"), ("Working Life", "Working life"),
               ("Education", "Education"), ("Sport & Leisure", "Sport and leisure"), ("Visual Arts", "Visual arts"),
               ("Performing Arts", "Performing arts")])
def aboriginal():
    a = gpd.read_parquet(RAW / "cos_aboriginal.parquet")
    a = a[a.geometry.notna() & ~a.geometry.is_empty]
    j = at_points(a, 25)
    return {r.bid: (r.Category, dict(name=r.Name, story=f"{r.Name}{', ' + r.Address.split(', NSW')[0] if r.Address else ''}.",
                                     source=r.URL)) for r in j.itertuples()}


# ---------------------------------------------------------------- Architecture

def wikidata_by_building():
    b = buildings()
    wd = wikidata_items().set_index("qid")
    q = b.set_index("bid").qid.dropna()
    q = q[q.isin(wd.index)]
    return b, wd, q


@layer(id="architects", section="Architecture", title="Architects", era="1810s–today",
       text=("The architects behind the buildings Wikidata knows, from the convict architect Francis Greenway and the "
             "colonial architects who followed him to the modernists of the high-rise city."),
       caveat="Only buildings with an architect on Wikidata; most of the city's terraces and warehouses were built by builders whose names went unrecorded.",
       source=("Wikidata (P84 architect), CC0", "https://www.wikidata.org"),
       groups="auto")
def architects():
    b, wd, q = wikidata_by_building()
    out = {}
    for bid, qid in q.items():
        it = wd.loc[qid]
        for a in sorted(it.architects):
            out.setdefault(bid, []).append((a, dict(name=it.label, story=f"Designed by {a}.",
                                                    source=f"https://www.wikidata.org/wiki/{qid}")))
    return out


@layer(id="styles", section="Architecture", title="Architectural styles", era="1810s–today",
       text=("Sydney's buildings by the style Wikidata records for them: the Georgian of the convict town, the Victorian "
             "revivals of the boom years, Federation, Art Deco between the wars, and the modernism of the towers."),
       caveat="Only buildings with a style on Wikidata.",
       source=("Wikidata (P149 architectural style), CC0", "https://www.wikidata.org"),
       groups="auto")
def styles():
    b, wd, q = wikidata_by_building()
    out = {}
    for bid, qid in q.items():
        it = wd.loc[qid]
        for s in sorted(it.styles):
            out.setdefault(bid, []).append((s, dict(name=it.label, source=f"https://www.wikidata.org/wiki/{qid}")))
    return out


# ---------------------------------------------------------------- Faith and community

FAITHS = [("anglican", "Anglican"), ("catholic", "Catholic"), ("protestant", "Uniting, Presbyterian and other Protestant"),
          ("orthodox", "Orthodox"), ("jewish", "Jewish"), ("muslim", "Muslim"), ("eastern", "Buddhist, Hindu and Sikh"),
          ("other", "Other faiths")]


def faith_of(t: dict) -> str:
    txt = lambda v: v.lower() if isinstance(v, str) else ""  # noqa: E731
    rel, den = txt(t.get("religion")), txt(t.get("denomination"))
    if rel == "christian":
        if "anglican" in den or "church_of_england" in den:
            return "anglican"
        if "catholic" in den and "orthodox" not in den:
            return "catholic"
        if "orthodox" in den:
            return "orthodox"
        return "protestant"
    return {"jewish": "jewish", "muslim": "muslim", "buddhist": "eastern", "hindu": "eastern", "sikh": "eastern"}.get(rel, "other")


@layer(id="worship", section="Faith and community", title="Places of worship", era="1810s–today",
       text=("Churches, synagogues, mosques and temples. St Mary's Catholic Cathedral and the Great Synagogue look onto "
             "Hyde Park, St Andrew's Anglican Cathedral stands beside the Town Hall, and the inner suburbs keep the "
             "churches, temples and mosques of the communities that settled around them."),
       source=("OpenStreetMap (amenity=place_of_worship), ODbL", "https://www.openstreetmap.org"),
       groups=FAITHS)
def worship():
    out = {}
    b = buildings()
    for r in b[b.amenity == "place_of_worship"].itertuples():
        out[r.bid] = faith_of(dict(religion=r.religion, denomination=r.denomination))
    p = osm_points("osm_pois.json", lambda t: t.get("amenity") == "place_of_worship")
    if len(p):
        j = at_points(p, 10)
        for r in j.itertuples():
            out.setdefault(r.bid, faith_of(dict(religion=getattr(r, "religion", None), denomination=getattr(r, "denomination", None))))
    return out


# ---------------------------------------------------------------- Everyday life

@layer(id="pubs", section="Everyday life", title="The corner pub", era="1830s–today",
       text=("Sydney's pubs are often called hotels: licensing laws long required them to offer rooms. In the inner city "
             "many stand on street corners, built for the terraces and warehouses around them."),
       source=("OpenStreetMap (amenity=pub), ODbL", "https://www.openstreetmap.org"),
       groups=[("listed", "Heritage-listed"), ("pub", "Not listed")])
def pubs():
    b = buildings().set_index("bid")
    listed = b.shr.notna() | b["item"].notna()
    out = {bid: "listed" if listed[bid] else "pub" for bid in b.index[b.amenity == "pub"]}
    p = osm_points("osm_pois.json", lambda t: t.get("amenity") == "pub")
    if len(p):
        j = at_points(p, 8)
        for r in j.itertuples():
            out.setdefault(r.bid, "listed" if listed[r.bid] else "pub")
            if getattr(r, "name", None) and isinstance(r.name, str):
                out[r.bid] = (out[r.bid] if isinstance(out[r.bid], str) else out[r.bid][0],
                              dict(name=r.name, story="A pub today." if not listed[r.bid] else "A pub today, in a heritage-listed building."))
    return out


# ---------------------------------------------------------------- The changing city

@layer(id="developing", section="The changing city", title="Developing Sydney, 1900–1920", era="1900–1920",
       text=("Photographs from the City of Sydney Archives of a city being rebuilt, 1900–1920. In the Archives' words, they "
             "inadvertently capture the largely working-class neighbourhoods and people displaced by commercial and "
             "government redevelopment. These are the buildings that stand where the photographs were taken."),
       caveat="A building here stands at a place the City's photographers recorded; it is usually not the building in the photograph, which was often demolished.",
       source=("City of Sydney Archives, Developing Sydney 1900–1920, CC BY 4.0",
               "https://data.cityofsydney.nsw.gov.au/datasets/cityofsydney::developing-sydney-1900-1920"),
       groups=[("photo", "Photographed 1900–1920")])
def developing():
    d = gpd.read_parquet(RAW / "cos_developing.parquet")
    d = d[d.geometry.notna() & ~d.geometry.is_empty]
    j = at_points(d, 30)
    out = {}
    for r in j.itertuples():
        story = re.sub(r"\s+", " ", r.Special_citation or "").strip()
        out[r.bid] = ("photo", dict(name=r.NODE_TITLE, story=story[:400], source=r.Archives_Catalogue_URL))
    return out


# ---------------------------------------------------------------- The modern city

@layer(id="strata", section="The modern city", title="The apartment city", era="1961–today",
       text=("New South Wales introduced strata title in 1961, letting the flats of one building be owned one by one. "
             "It made inner Sydney a city of apartments, from the walk-up blocks of the 1960s and 70s to the towers of "
             "Pyrmont, the city centre and Green Square. Coloured by the decade each strata plan was registered."),
       caveat="Older buildings converted to strata show their conversion decade.",
       source=("NSW Spatial Services, cadastre, CC BY 4.0", "https://portal.spatial.nsw.gov.au"),
       groups=[("1960s", "1960s"), ("1970s", "1970s"), ("1980s", "1980s"), ("1990s", "1990s"), ("2000s", "2000s"),
               ("2010s", "2010s"), ("2020s", "2020s")])
def strata():
    b = buildings()
    s = b[b.sp_year.notna()]
    return {r.bid: f"{int(r.sp_year) // 10 * 10}s" for r in s.itertuples() if r.sp_year >= 1961}


@layer(id="towers", section="The modern city", title="The skyline", era="1957–today",
       text=("For most of the twentieth century no building in Sydney could rise above 150 feet, 46 metres. The limit "
             "was lifted in 1957, and the towers came: the AMP Building at Circular Quay first, then Australia Square, "
             "and a skyline that has kept growing on both sides of the harbour."),
       source=("Heights: OpenStreetMap, ODbL; GlobalBuildingAtlas, CC BY-NC 4.0", "https://www.openstreetmap.org"),
       groups=[("46", "46–100 m"), ("100", "100–200 m"), ("200", "Over 200 m")])
def towers():
    b = buildings()
    t = b[(b.height >= 46) & (b.building != "bridge")]
    return {r.bid: "200" if r.height >= 200 else "100" if r.height >= 100 else "46" for r in t.itertuples()}


def main():
    b = buildings()
    c = b.geometry.centroid
    loc = to_local(np.c_[c.x, c.y])
    where = {bid: [round(float(x), 1), round(float(z), 1)] for bid, (x, z) in zip(b.bid, loc)}
    mask = np.zeros(len(b), dtype=np.uint64)
    catalogue, bit = [], 0
    for L in LAYERS:
        members = L["source_fn"]()
        notes, groups_of = {}, {}
        for p, v in members.items():
            for item in (v if isinstance(v, list) else [v]):
                g, n = item if isinstance(item, tuple) else (item, None)
                groups_of.setdefault(p, set()).add(g)
                if n and p not in notes:
                    notes[p] = n
        spec = L["groups"]
        if spec == "auto":   # the eight largest groups, named as the data names them
            count = Counter(g for gs in groups_of.values() for g in gs)
            spec = [(g, g) for g, _ in count.most_common(8)]
        groups = []
        for key, label in spec:
            hit = b.bid.map(lambda k: key in groups_of.get(k, ())).to_numpy(bool)
            if not hit.any():
                continue
            mask[hit] |= np.uint64(1) << np.uint64(bit)
            years = b.year[hit].value_counts().sort_index()
            groups.append(dict(key=key, label=label, bit=bit, count=int(hit.sum()),
                               years={str(int(y)): int(n) for y, n in years.items()}))
            bit += 1
        assert bit <= 64, "out of layer bits"
        in_groups = {p for p, gs in groups_of.items() if gs & {g["key"] for g in groups}}
        meta = {k: v for k, v in L.items() if k not in ("source_fn", "groups", "source")}
        meta.update(source=dict(label=L["source"][0], url=L["source"][1]), groups=groups,
                    count=len(in_groups),
                    notes={str(p): dict({k: v for k, v in n.items() if isinstance(v, str) and v}, at=where[p])
                           for p, n in notes.items() if p in in_groups})
        if groups:
            catalogue.append(meta)
        print(f'{L["id"]:12s}', {g["label"]: g["count"] for g in groups})
    out = pd.DataFrame({"bid": b.bid,
                        "lay0": (mask & np.uint64(0xFFFFFFFF)).astype(np.uint32),
                        "lay1": (mask >> np.uint64(32)).astype(np.uint32)})
    out.to_parquet(DATA / "layers.parquet")
    WEB.mkdir(parents=True, exist_ok=True)
    (WEB / "layers.json").write_text(json.dumps(catalogue, ensure_ascii=False, separators=(",", ":")))


if __name__ == "__main__":
    main()
