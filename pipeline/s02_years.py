"""Construction years, heritage status and Wikidata links.

Sydney has no register that dates every building (Amsterdam has BAG). Each building takes the best
evidence there is, in this order, and its card says which:

  flag 0  documented: a year from Wikidata (inception, else opening) or OpenStreetMap (start_date)
  flag 1  documented, approximate: the source gives a decade, a century, a range or "c."
  flag 2  strata plan: the year its strata plan was registered. Apartment buildings are strata-titled on
          completion, so the year is close. Older buildings converted to strata later would carry their
          conversion year, so a strata year never overrides heritage evidence that the building is older.
  flag 3  heritage area: a building the City of Sydney's DCP marks as contributing to a heritage conservation
          area (or, in North Sydney, a low-rise building inside one), dated from the documented heritage
          buildings around it
  flag 4  estimated from the dated buildings around it of similar height

Estimated years (flags 2–4) are spread within the range of their evidence (yfrom–yto), seeded by the
building, so a suburb does not appear in one single year when the film plays.
"""
import json
import re
import zlib

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely
from scipy.spatial import cKDTree

from .config import CRS, DATA, RAW
from .periods import period_index

TODAY = 2026
TALL = 46.0     # metres: Sydney's 150-foot height limit held until 1957
HERITAGE = {"shr": 1, "local": 2, "Contributing": 3, "Neutral": 4, "Detracting": 5}

# Wikidata classes that name a building (an item that is only an institution keeps its founding date,
# which says nothing about the building it is in now).
BUILDING_WORDS = re.compile(
    r"building|house|terrace|church|cathedral|chapel|basilica|skyscraper|tower|hotel|\bpub\b|inn|theatre|"
    r"theater|cinema|warehouse|wool store|cottage|mansion|villa|office|bank|post office|court|station building|"
    r"observatory|lighthouse|barracks|\bhall\b|arcade|store|market|mill|factory|residence|apartment|flats|mosque|"
    r"synagogue|temple|fort|gaol|prison|structure|heritage site|historic site|monument|substation|pumping station|"
    r"bond store|customs house|exchange|townhouse|tenement|shop|bakery|brewery|stables|lodge", re.I)
INSTITUTION_WORDS = re.compile(r"organi[sz]ation|university|faculty|company|business|club|association|school\b|"
                               r"college|foundation|society|government|department|agency|council|"
                               r"suburb|locality|park|reserve|road|street|electoral|bay|point|island|wharf|sculpture|"
                               r"season|event|station$|tram stop|weather", re.I)


def seed(i: int, salt: str = "") -> float:
    return (zlib.crc32(f"{i}{salt}".encode()) % 100000) / 100000.0


# ---------------------------------------------------------------- documented years

YEAR = re.compile(r"(1[6-9]\d\d|20[0-2]\d)")


def parse_osm_date(s: str | None):
    """(year, from, to, approximate) from an OSM start_date, or None."""
    if not s or not isinstance(s, str):
        return None
    s = s.strip()
    if re.fullmatch(r"(1[6-9]\d\d|20[0-2]\d)(-\d\d(-\d\d)?)?", s):
        y = int(s[:4])
        return y, y, y, False
    m = re.fullmatch(r"C(1[6-9]|20)", s, re.I)
    if m:
        c = (int(m.group(1)) - 1) * 100
        return c + 50, c, c + 99, True
    m = re.fullmatch(r"(1[6-9]\d|20[0-2])0s", s)
    if m:
        d = int(m.group(1)) * 10
        return d + 5, d, d + 9, True
    ys = [int(y) for y in YEAR.findall(s)]
    if ys:
        a, b = min(ys), max(ys)
        if re.search(r"before|<", s, re.I):
            return a - 5, a - 20, a, True
        if re.search(r"after|>", s, re.I):
            return a + 5, a, a + 20, True
        return a, a, b, len(ys) > 1 or bool(re.search(r"~|c\.|circa|about", s, re.I))
    return None


BUILT = re.compile(
    r"\b(?:built|constructed|erected|completed|rebuilt)\b[^.;:]{0,60}?\b(?P<how>from|in|during|between|c\.|circa|around|by)"
    r"\s+(?:the\s+)?(?:early\s+|mid\s+|late\s+)?(?P<a>1[6-9]\d\d|20[0-2]\d)(?P<s>s)?"
    r"(?:\s*(?:to|and|–|-|until)\s*(?P<b>1[6-9]\d\d|20[0-2]\d))?")


BUILDING_FROM = re.compile(r"\b(?:building|present building|current building|church)\s+(?:dates\s+)?from\s+(?:the\s+)?"
                           r"(?P<a>1[6-9]\d\d|20[0-2]\d)(?P<s>s)?")


def parse_wiki_built(text: str | None):
    """(year, from, to, approximate) from the first 'built from 1885 to 1887' in an article's lead.

    The leads of the NSW heritage articles come from the State Heritage Inventory and say when the place
    was built in this form ("It was designed by … and built from 1898 to 1900")."""
    if not text:
        return None
    m = BUILT.search(text)
    if not m:
        m = BUILDING_FROM.search(text)
        if not m:
            return None
        a = int(m["a"])
        return (a + 5, a, a + 9, True) if m["s"] else (a, a, a, False)
    a = int(m["a"])
    if m["s"]:
        return a + 5, a, a + 9, True
    b = int(m["b"]) if m["b"] else a
    if b < a or b - a > 80:
        b = a
    if m["how"] == "by":
        return a, a - 10, a, True
    approx = m["how"] in ("c.", "circa", "around")
    # A long build: the year it began, when the first of it stood; a short one: the year it was done.
    year = a if b - a > 5 else b
    return year, a, b, approx or b - a > 5


def wikidata_items() -> pd.DataFrame:
    rows = json.loads((RAW / "wikidata.json").read_text())
    items = {}
    for r in rows:
        q = r["item"].rsplit("/", 1)[1]
        it = items.setdefault(q, dict(qid=q, label=r.get("itemLabel"), coord=r.get("coord"), dates=[],
                                      demolished=False, shr=r.get("shr"), osmway=r.get("osmway"),
                                      osmrel=r.get("osmrel"), image=r.get("image"), article=r.get("article"),
                                      classes=set(), architects=set(), styles=set(), heritage=set()))
        for key, prec_key, kind in (("inception", "incprec", "inception"), ("opened", "openprec", "opened")):
            if r.get(key) and r[key][:1] != "-" and YEAR.match(r[key][:4]):
                it["dates"].append((kind, int(r[key][:4]), int(r.get(prec_key) or 9)))
        it["demolished"] |= bool(r.get("demolished"))
        for k, src in (("classes", "classes"), ("architects", "architects"), ("styles", "styles")):
            it[k] |= {x for x in (r.get(src) or "").split("|") if x}
        if r.get("heritageLabel"):
            it["heritage"].add(r["heritageLabel"])
    df = pd.DataFrame(items.values())
    lonlat = df.coord.str.extract(r"Point\(([-\d.]+) ([-\d.]+)\)").astype(float)
    df = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(lonlat[0], lonlat[1]), crs=4326).to_crs(CRS)
    return df


def wd_year(dates):
    """The item's earliest inception (else opening): (year, from, to, approximate)."""
    if not dates:
        return None
    kind_rank = {"inception": 0, "opened": 1}
    best = min(dates, key=lambda d: (kind_rank[d[0]], d[1]))
    if best[0] == "opened":
        inc = [d for d in dates if d[0] == "inception"]
        best = min(inc, key=lambda d: d[1]) if inc else best
    _, y, prec = best
    if prec >= 9:
        return y, y, y, False
    if prec == 8:
        d = y - y % 10
        return d + 5, d, d + 9, True
    c = y - y % 100
    return c + 50, c, c + 99, True


def link_wikidata(b: gpd.GeoDataFrame, wd: gpd.GeoDataFrame) -> pd.Series:
    """Wikidata item per building: the OSM wikidata tag, OSM ids recorded on Wikidata, or a building-like
    item whose coordinate falls inside exactly one footprint."""
    qid = pd.Series(b.wikidata.where(b.wikidata.fillna("").str.match(r"^Q\d+$")), index=b.index)
    by_way = {f"w{w}": q for q, w in zip(wd.qid, wd.osmway) if isinstance(w, str)}
    by_rel = {f"r{r}": q for q, r in zip(wd.qid, wd.osmrel) if isinstance(r, str)}
    from_osm = b.osm.map(lambda o: by_way.get(o) or by_rel.get(o) if isinstance(o, str) else None)
    qid = qid.fillna(from_osm)
    how = pd.Series(np.where(qid.notna(), "osm", None), index=b.index, dtype=object)
    taken = set(qid.dropna())
    ok = wd[~wd.qid.isin(taken) & ~wd.demolished].copy()
    cls = ok.classes.map(lambda c: " | ".join(c))
    building_like = cls.str.contains(BUILDING_WORDS) & ~cls.str.contains(INSTITUTION_WORDS)
    ok = ok[building_like | (ok.shr.notna() & ~cls.str.contains(INSTITUTION_WORDS))]
    j = gpd.sjoin(ok[["qid", "geometry"]], b[["geometry"]], predicate="within")
    j = j[~j.qid.duplicated(keep=False)]               # an item on one footprint only
    j = j[~j.index_right.duplicated(keep=False)]       # one item per footprint
    new = pd.Series(j.qid.values, index=j.index_right.values)
    new = new[qid.loc[new.index].isna()]
    qid.loc[new.index] = new
    how.loc[new.index] = "coordinate"
    return qid, how


# ---------------------------------------------------------------- strata plans

def strata(b: gpd.GeoDataFrame) -> pd.DataFrame:
    """Strata plan number per building (the plan whose lots cover most of its footprint), and a year for it.

    The NSW cadastre went digital in 1993. Every lot created since carries its creation date, which is the
    plan's registration; older plans were loaded in bulk and carry the load date. Plan numbers rise with
    time, so plans since 1994 calibrate a monotone number → year curve, and older ones are placed on it
    between SP 1 (the Strata Titles Act took effect in 1961) and the first dated plans."""
    lots = gpd.read_parquet(RAW / "strata_lots.parquet").to_crs(CRS)
    lots = lots[lots.plannumber.notna() & lots.planlabel.str.startswith("SP")]
    lots["created"] = pd.to_datetime(lots.createdate, unit="ms")
    plans = lots.groupby("plannumber").created.min().reset_index()
    plans["year"] = plans.created.dt.year + plans.created.dt.dayofyear / 366
    # Bulk loads: the days on which the older plans were loaded at once.
    bulk = plans.created.dt.date.value_counts()
    plans["bulk"] = plans.created.dt.date.isin(set(bulk[bulk > 30].index)).to_numpy()
    plans = plans.sort_values("plannumber").reset_index(drop=True)
    # Where the dated plans begin: from the first plan number after which (almost) every plan has its own date.
    # Below it the few dated plans are lots re-created later, which would date their plans decades too late.
    share = (~plans.bulk).rolling(60, min_periods=20).mean().shift(-59).fillna(1.0)
    start = plans.plannumber[(share > 0.9).to_numpy() & ~plans.bulk.to_numpy()].iloc[0]
    good = plans[(plans.plannumber >= start) & ~plans.bulk]
    from scipy.optimize import isotonic_regression  # SciPy ≥ 1.12
    fit = isotonic_regression(good.year.to_numpy(), increasing=True).x
    # Drop what the fit had to flatten (re-created lots, late corrections), then fit again.
    keep = np.abs(good.year.to_numpy() - fit) < 1.0
    good = good[keep]
    fit = isotonic_regression(good.year.to_numpy(), increasing=True).x
    first_n, first_y = good.plannumber.iloc[0], fit[:10].mean()
    anchors_n = np.r_[1, good.plannumber.to_numpy()]
    anchors_y = np.r_[1961.5, fit]
    plans["fitted"] = np.interp(plans.plannumber, anchors_n, anchors_y)
    plans["calibrated"] = plans.plannumber >= first_n
    print(f"  strata: {len(plans)} plans, {len(good)} dated by the cadastre from SP{int(first_n)} ({first_y:.1f}); "
          f"older plans placed between SP1 (1961) and that")

    j = gpd.sjoin(b[["geometry"]], lots[["plannumber", "geometry"]], predicate="intersects")
    inter = shapely.area(shapely.intersection(b.geometry.loc[j.index].values, lots.geometry.loc[j.index_right].values))
    j["share"] = inter / b.area.loc[j.index].values
    j = j[j.share > 0.5].sort_values("share").groupby(level=0).last()
    out = j[["plannumber"]].join(plans.set_index("plannumber")[["fitted", "calibrated"]], on="plannumber")
    return out


# ---------------------------------------------------------------- heritage

def heritage(b: gpd.GeoDataFrame) -> pd.DataFrame:
    pts = gpd.GeoDataFrame(geometry=b.representative_point(), index=b.index, crs=CRS)
    out = pd.DataFrame(index=b.index)
    out["heritage"] = 0
    out["hca"] = None
    out["contrib"] = None
    out["item"] = None
    out["item_sig"] = None

    con = gpd.read_parquet(RAW / "cos_contributions.parquet").to_crs(CRS)
    j = gpd.sjoin(pts, con[["ContributionType", "ConservationArea", "geometry"]], predicate="within")
    j = j[~j.index.duplicated()]
    out.loc[j.index, "contrib"] = j.ContributionType
    out.loc[j.index, "hca"] = j.ConservationArea

    epi = gpd.read_parquet(RAW / "epi_heritage.parquet").to_crs(CRS)
    areas = epi[epi.LAY_CLASS.str.startswith("Conservation Area")]
    j = gpd.sjoin(pts, areas[["H_NAME", "geometry"]], predicate="within")
    j = j[~j.index.duplicated()]
    out.loc[j.index, "hca"] = out.loc[j.index, "hca"].fillna(j.H_NAME)

    items = epi[epi.LAY_CLASS.str.startswith("Item")]
    j = gpd.sjoin(pts, items[["H_ID", "H_NAME", "SIG", "geometry"]], predicate="within")
    j = j.sort_values("SIG", ascending=False)          # 'State' before 'Local'
    j = j[~j.index.duplicated()]
    out.loc[j.index, "item"] = j.H_NAME
    out.loc[j.index, "item_sig"] = j.SIG

    shr = gpd.read_parquet(RAW / "shr.parquet").to_crs(CRS)
    j = gpd.sjoin(pts, shr[["ITEMNAME", "LISTINGNO", "HOITEMID", "geometry"]], predicate="within")
    j = j[~j.index.duplicated()]
    out["shr"] = None
    out["shr_no"] = None
    out["shr_id"] = np.nan
    out.loc[j.index, "shr"] = j.ITEMNAME
    out.loc[j.index, "shr_no"] = j.LISTINGNO
    out.loc[j.index, "shr_id"] = j.HOITEMID

    out.loc[out.contrib.notna(), "heritage"] = out.contrib.map(HERITAGE)
    out.loc[out["item"].notna(), "heritage"] = HERITAGE["local"]
    out.loc[out.get("shr").notna(), "heritage"] = HERITAGE["shr"]
    return out


# ---------------------------------------------------------------- estimates

def knn_years(src_xyz, src_years, dst_xyz, k=12, max_d=1500.0):
    """For each destination: the weighted 25th, 50th and 75th percentile of its k nearest dated sources."""
    tree = cKDTree(src_xyz)
    d, i = tree.query(dst_xyz, k=min(k, len(src_xyz)))
    d = np.atleast_2d(d); i = np.atleast_2d(i)
    w = 1.0 / np.maximum(d, 25.0)
    w[d > max_d] *= 0.05
    ys = src_years[i]
    order = np.argsort(ys, axis=1)
    ys = np.take_along_axis(ys, order, axis=1)
    w = np.take_along_axis(w, order, axis=1)
    cw = np.cumsum(w, axis=1) / w.sum(axis=1, keepdims=True)
    q = lambda p: ys[np.arange(len(ys)), np.argmax(cw >= p, axis=1)]
    return q(0.25), q(0.5), q(0.75)


def features(b, idx, scale=180.0):
    c = b.geometry.loc[idx].centroid
    return np.c_[c.x, c.y, scale * np.log(b.height.loc[idx].clip(3, 300) / 3)]


def main():
    b = gpd.read_parquet(DATA / "buildings.parquet")
    b = b.rename(columns={"heritage": "osm_heritage", "heritage_operator": "osm_heritage_operator"})
    b["year"] = np.nan
    b["yfrom"] = np.nan
    b["yto"] = np.nan
    b["date_flag"] = -1
    b["date_src"] = None

    # Documented: Wikidata, then the Wikipedia article's lead, then OpenStreetMap.
    wd = wikidata_items()
    h = heritage(b)
    b = b.join(h)
    b["qid"], b["qid_how"] = link_wikidata(b, wd)
    # Buildings in a State Heritage Register curtilage take the register item's Wikidata entry
    # (Wikidata P3449 is the register's item id): all of them when the curtilage holds a few buildings,
    # otherwise only its largest.
    by_shr = {s_: q for q, s_ in zip(wd.qid, wd.shr) if isinstance(s_, str)}
    shr_q = b.shr_id.map(lambda v: by_shr.get(str(int(v))) if pd.notna(v) else None)
    n_in = b.groupby("shr_id").bid.transform("count")
    largest = b.area == b.assign(a=b.area).groupby("shr_id").a.transform("max")
    main = shr_q.notna() & ((n_in <= 3) | largest)
    b["qid_area"] = shr_q                                  # the register entry the building is part of
    b.loc[main & b.qid.isna(), "qid_how"] = "shr"
    b.loc[main, "qid"] = b.loc[main, "qid"].fillna(shr_q[main])

    articles = json.loads((RAW / "wikipedia.json").read_text()) if (RAW / "wikipedia.json").exists() else {}
    wdi = wd.set_index("qid")
    wdy = wdi.dates.map(wd_year)
    from urllib.parse import unquote
    title_of = wdi.article.map(lambda u: unquote(u.rsplit("/wiki/", 1)[1]).replace("_", " ") if isinstance(u, str) else None)
    wpy = title_of.map(lambda t: parse_wiki_built(articles.get(t, {}).get("extract")) if t else None)
    # Landmarks with a year checked against their article (pipeline/landmarks.py) keep it.
    fixed = b.fixed_year.notna() if "fixed_year" in b else pd.Series(False, index=b.index)
    for col in ("year", "yfrom", "yto"):
        b.loc[fixed, col] = b.fixed_year[fixed]
    b.loc[fixed, "date_flag"] = 0
    b.loc[fixed, "date_src"] = "wikipedia"
    for i, q in b.qid[~fixed].dropna().items():
        if q not in wdi.index or wdi.demolished.get(q, False):
            continue
        # The article's lead first: for heritage places it is written from the State Heritage Inventory, while a
        # Wikidata inception sometimes dates the institution, a restoration or a renaming.
        for src, y in (("wikipedia", wpy.get(q)), ("wikidata", wdy.get(q))):
            if y:
                b.loc[i, ["year", "yfrom", "yto"]] = y[:3]
                b.loc[i, "date_flag"] = 1 if y[3] else 0
                b.loc[i, "date_src"] = src
                break
    # A tower matched to an old place by a coordinate or a heritage curtilage is a later building on or beside
    # that place (an old school kept at the foot of an office tower): it keeps neither the place's year nor its name.
    wrong = b.qid_how.isin(["coordinate", "shr"]) & (b.height >= TALL) & (b.year < 1957)
    b.loc[wrong, ["year", "yfrom", "yto"]] = np.nan
    b.loc[wrong, "date_flag"] = -1
    b.loc[wrong, "date_src"] = None
    b.loc[wrong, ["qid", "qid_how"]] = None
    for col in ("start_date", "construction_date", "building_start_date"):
        if col not in b:
            continue
        need = b.date_flag < 0
        parsed = b.loc[need, col].map(parse_osm_date).dropna()
        for i, y in parsed.items():
            b.loc[i, ["year", "yfrom", "yto"]] = y[:3]
            b.loc[i, "date_flag"] = 1 if y[3] else 0
            b.loc[i, "date_src"] = "osm"
    print(f"  documented: {(b.date_flag == 0).sum()} exact, {(b.date_flag == 1).sum()} approximate; "
          + ", ".join(f"{k} {v}" for k, v in b.date_src.value_counts().items()))

    sp = strata(b)
    b["sp"] = sp.plannumber
    b["sp_year"] = sp.fitted
    b["sp_calibrated"] = sp.calibrated

    old_evidence = (b.contrib == "Contributing") | b["item"].notna() | b.shr.notna()
    tall = b.height >= TALL
    documented = b.date_flag >= 0

    # Strata: apartments dated by their plan, unless heritage evidence says the building is older.
    use_sp = ~documented & b.sp_year.notna() & ~old_evidence
    spread = np.where(b.sp_calibrated.fillna(False), 1.0, 3.0)
    b.loc[use_sp, "year"] = np.floor(b.sp_year[use_sp]).clip(1961, TODAY)
    b.loc[use_sp, "yfrom"] = np.floor(b.sp_year[use_sp] - 1 - spread[use_sp]).clip(1961, TODAY)
    b.loc[use_sp, "yto"] = np.floor(b.sp_year[use_sp] + spread[use_sp]).clip(1961, TODAY)
    b.loc[use_sp, "date_flag"] = 2
    b.loc[use_sp, "date_src"] = "strata"
    print(f"  strata: {use_sp.sum()} buildings")

    dated = b.date_flag >= 0
    # Heritage-area estimates: from documented buildings that are themselves heritage (older than 1946).
    pool_old = documented & (b.year < 1946)
    nsyd_low = (b.lga == "NORTH SYDNEY") & b.hca.notna() & (b.floors <= 3) & b.sp_year.isna()
    her_target = ~dated & ~tall & ((b.contrib == "Contributing") | b["item"].notna() | b.shr.notna() | nsyd_low)
    if her_target.any():
        lo, mid, hi = knn_years(features(b, b.index[pool_old]), b.year[pool_old].to_numpy(),
                                features(b, b.index[her_target]), k=10)
        b.loc[her_target, ["yfrom", "year", "yto"]] = np.c_[lo, mid, hi]
        b.loc[her_target, "date_flag"] = 3
        b.loc[her_target, "date_src"] = "heritage"
    print(f"  heritage-area estimates: {her_target.sum()} from {pool_old.sum()} documented heritage buildings")

    # Everything else: the dated buildings around it, of similar height. Tall buildings take only years from 1958,
    # detracting buildings in heritage areas only years from 1946. Low-rise houses and other buildings that are not
    # strata-titled take documented years only: the strata-dated apartments around them say nothing about them.
    dated = b.date_flag >= 0
    rest = ~dated
    pool_doc = dated & b.date_flag.isin([0, 1])
    pool = dated & b.date_flag.isin([0, 1, 2])
    house = b.building.isin(["house", "terrace", "detached", "semidetached_house", "residential", "bungalow",
                             "industrial", "warehouse", "garage", "shed", "roof", "church", "school"]) & (b.floors <= 3)
    everywhere = pd.Series(True, index=b.index)
    for name, target, src in [("tall", rest & tall, pool & (b.year >= 1958)),
                              ("detracting", rest & ~tall & (b.contrib == "Detracting"), pool & (b.year >= 1946)),
                              ("low-rise", rest & ~tall & (b.contrib != "Detracting") & house, pool_doc),
                              ("other", rest & ~tall & (b.contrib != "Detracting") & ~house, pool & everywhere)]:
        if not target.any():
            continue
        lo, mid, hi = knn_years(features(b, b.index[src]), b.year[src].to_numpy(), features(b, b.index[target]))
        b.loc[target, ["yfrom", "year", "yto"]] = np.c_[lo, mid, hi]
        b.loc[target, "date_flag"] = 4
        b.loc[target, "date_src"] = name
        print(f"  neighbour estimates ({name}): {target.sum()} from {src.sum()}")

    # Spread estimates across their range, seeded by the building.
    est = b.date_flag >= 2
    s = np.array([seed(i) for i in b.bid[est]])
    lo, hi = b.yfrom[est].to_numpy(), b.yto[est].to_numpy()
    b.loc[est, "year"] = np.round(lo + (hi - lo) * s)
    for col in ("year", "yfrom", "yto"):
        b[col] = b[col].clip(1788, TODAY).round().astype(int)
    b["yfrom"] = np.minimum(b.yfrom, b.year)
    b["yto"] = np.maximum(b.yto, b.year)
    b["period"] = b.year.map(period_index)
    b.to_parquet(DATA / "buildings_dated.parquet")
    print("flags:", b.date_flag.value_counts().sort_index().to_dict())
    print("periods:", b.period.value_counts().sort_index().to_dict())
    print("heritage:", b.heritage.value_counts().sort_index().to_dict())


if __name__ == "__main__":
    main()
