"""Suburbs and their statistics, for the Suburbs lens: each suburb painted by a measure, year by year.

  web/data/suburbs.bin    u8 per building (by gid): the index of its suburb in suburbs.json, 255 none
  web/data/suburbs-land.bin  each suburb's land on the map, in the layout of land.bin (s04_water); suburbs.json's
                          `poly` names the suburb of each polygon
  web/data/suburbs.json   the suburbs (name, postcode, area, centre) and the measures: for each, its years and a value
                          per suburb and year (null where there is none), its unit and its source

Suburbs are NSW Spatial Services' gazetted suburbs, the localities the ABS's Suburbs and Localities (SAL), BOCSAR's
crime figures and the Valuer General's sales are all named by. A suburb's figures are for the whole suburb, even
where the map shows only part of it.
"""
import json
import re

import geopandas as gpd
import numpy as np
import pandas as pd
import shapely

from .config import CRS, DATA, RAW, WEB
from .s04_water import ground_and_water, pack, polygons
from .s03_tiles import to_local, write_bin

NONE = 255
MIN_SALES = 20  # a year's median price needs this many sales: a handful of houses in the city centre says little
STATS = RAW / "stats"
# Offences against people and property, which residents and visitors report. Left out: what police find by looking
# (drugs, weapons, liquor, transport, disorderly conduct, receiving stolen goods, assaulting police), which counts
# where police patrol more than where crime happens, and fraud, which is recorded where the victim lives or banks.
CRIME = {"Homicide", "Assault", "Sexual offences", "Abduction and kidnapping", "Robbery", "Blackmail and extortion",
         "Coercive Control", "Intimidation, stalking and harassment", "Other offences against the person", "Theft",
         "Arson", "Malicious damage to property"}
CRIME_OUT = {"Assault Police", "Fraud", "Receiving or handling stolen goods"}
# The councils a suburb on the map can be in, as sources write them to tell suburbs of one name apart.
COUNCILS = {"SYDNEY", "NORTH SYDNEY", "MOSMAN", "WOOLLAHRA", "LANE COVE", "HUNTERS HILL", "WAVERLEY", "INNER WEST",
            "CANADA BAY", "WILLOUGHBY", "NORTHERN BEACHES", "RYDE", "RANDWICK", "BURWOOD",
            "CANTERBURY-BANKSTOWN", "CANTERBURY", "BAYSIDE", "ROCKDALE", "BOTANY BAY", "KU-RING-GAI", "NSW",
            "MARRICKVILLE", "LEICHHARDT", "ASHFIELD", "MANLY", "CITY OF CANADA BAY"}  # the councils before the 2016 mergers


def matcher(source_names):
    """A function from our suburb name (upper case) to the source's name for it: the same name, or the same name
    followed by one of our councils in brackets ("DARLINGTON (SYDNEY)", "Darlington (Sydney - NSW)", "Manly (NSW)")."""
    by_base = {}
    for n in source_names:
        base, _, rest = str(n).upper().partition(" (")
        rest = f' {rest.rstrip(")").replace(" - ", " ")} '
        # Ours when the brackets name one of our councils; perhaps ours with no brackets, or only the state's.
        score = 2 if any(f" {c} " in rest for c in COUNCILS - {"NSW"}) else 1 if rest.strip() in ("", "NSW") else 0
        by_base.setdefault(base.strip(), []).append((score, n))
    def match(name):
        c = by_base.get(name, [])
        top = max((sc for sc, _ in c), default=0)
        best = [n for sc, n in c if sc == top and sc]
        return best[0] if len(best) == 1 else None
    return match


def crime_counts(s):
    """Offences against people and property a year in each suburb, 1995 to the last whole year (BOCSAR)."""
    import zipfile
    with zipfile.ZipFile(STATS / "bocsar" / "SuburbData.zip") as z:
        d = pd.read_csv(z.open("SuburbData.csv"), encoding="latin1")
    d = d[d["Offence category"].isin(CRIME) & ~d.Subcategory.isin(CRIME_OUT)]
    months = [c for c in d.columns if c[-4:].isdigit()]
    by = d.groupby("Suburb")[months].sum()
    years = sorted({int(m[-4:]) for m in months if sum(c[-4:] == m[-4:] for c in months) == 12})
    yearly = pd.DataFrame({y: by[[m for m in months if m.endswith(str(y))]].sum(axis=1) for y in years})
    match = matcher(yearly.index)
    rows = [yearly.loc[m].to_numpy(float) if (m := match(n)) is not None else np.full(len(years), np.nan)
            for n in s.suburbname]
    missing = [n for n in s.suburbname if match(n) is None]
    if missing:
        print(f"  crime: no figures for {missing}")
    return years, np.array(rows)


def suburbs_on_map():
    """The suburbs with buildings on the map, and the suburb of every building (by gid)."""
    s = gpd.read_parquet(RAW / "suburbs.parquet").to_crs(CRS)
    b = gpd.read_parquet(DATA / "buildings_dated.parquet", columns=["bid", "geometry"])
    gid = pd.read_parquet(DATA / "gid.parquet")
    b = b.merge(gid, on="bid")
    pts = gpd.GeoDataFrame(b[["gid"]], geometry=b.geometry.representative_point(), crs=CRS)
    j = gpd.sjoin(pts, s[["suburbname", "geometry"]], predicate="within", how="left").drop_duplicates("gid")
    counts = j.suburbname.value_counts()
    s = s[s.suburbname.isin(counts.index)].copy()
    s["buildings"] = s.suburbname.map(counts)
    s = s.sort_values("suburbname").reset_index(drop=True)
    assert len(s) < NONE, "more suburbs than a byte holds"
    index = dict(zip(s.suburbname, s.index))
    of = np.full(len(b), NONE, np.uint8)
    hit = j.suburbname.notna()
    of[j.gid[hit].to_numpy()] = j.suburbname[hit].map(index).to_numpy()
    return s, of


def land_of(s):
    """Each suburb's land on the map: within the councils, on the land, off the water."""
    city = gpd.read_parquet(RAW / "boundary.parquet").to_crs(CRS).union_all()
    _, ground, water = ground_and_water()
    land = city.intersection(ground).difference(water.buffer(0.5).buffer(-0.5))
    polys, owner = [], []
    for i, g in enumerate(s.geometry):
        for p in polygons(shapely.make_valid(g.intersection(land)).simplify(2.0)):
            if p.area > 200:
                polys.append(p)
                owner.append(i)
    return polys, owner


def census(s):
    """Each suburb in the 2011, 2016 and 2021 censuses (ABS DataPacks: State Suburbs, then Suburbs and Localities),
    joined by name, as the codes change from census to census. {year: a frame in the order of s}."""
    import io
    import zipfile
    packs = {2011: ("abs_census_2011_ssc/2011_BCP_SSC_for_NSW_short-header.zip", "B01", "B02", "B40B", "region_id"),
             2016: ("abs_census_2016_ssc/2016_GCP_SSC_for_NSW_short-header.zip", "G01", "G02", "G46B", "SSC_CODE_2016"),
             2021: ("abs_census_gcp_2021/2021_GCP_SAL_for_NSW_short-header.zip", "G01", "G02", "G49B", "SAL_CODE_2021")}
    out = {}
    for year, (f, pop, med, qual, key) in packs.items():
        with zipfile.ZipFile(STATS / f) as z:
            def table(t):
                name = next(n for n in z.namelist() if f"_{t}_NSW_" in n and n.endswith(".csv"))
                return pd.read_csv(z.open(name), index_col=key)
            t = table(pop).join(table(med)).join(table(qual), rsuffix="_q")
            geog = pd.ExcelFile(io.BytesIO(z.read(next(n for n in z.namelist() if "geog_desc" in n))))
            if year == 2011:
                g = geog.parse(0).query("Level == 'SSC'").rename(columns={"Code": "code", "Label": "name", "Area sqkm": "km2"})
                g["code"] = g.code.astype(str)
            else:
                g = pd.concat([geog.parse(sh) for sh in geog.sheet_names if "Non" in sh])
                g = g[g.ASGS_Structure.isin(["SSC", "SAL"])].rename(columns={
                    f"Census_Code_{year}": "code", f"Census_Name_{year}": "name", "Area sqkm": "km2"})
                g["code"] = g.ASGS_Structure + g.code.astype(str).str.replace(r"^(SSC|SAL)", "", regex=True)
        t.index = t.index.astype(str)
        t = t.join(g.set_index("code")[["name", "km2"]], how="inner")
        t.columns = [c.lower() for c in t.columns]
        adults = t.tot_p_p - t.age_0_4_yr_p - t.age_5_14_yr_p
        t = pd.DataFrame(dict(
            name=t["name"], km2=t.km2, population=t.tot_p_p,
            income=t.median_tot_hhd_inc_weekly.where(t.median_tot_hhd_inc_weekly > 0),
            degree=(100 * (t.p_bachdeg_total + t.p_graddip_and_gradcert_total + t.p_pgrad_deg_total) / adults)
            .where(adults >= 50)))
        match = matcher(t.name)
        names = [match(n) for n in s.suburbname]
        missing = [n for n, m in zip(s.suburbname, names) if m is None]
        if missing:
            print(f"  census {year}: no figures for {missing}")
        out[year] = t.set_index("name").reindex(names).reset_index(drop=True)
    return out


def sales(s):
    """Median sale prices a year by postcode, of houses (not strata titled) and of strata homes, from DCJ's quarterly
    Rent and Sales Report (the NSW Valuer General's sales): the year's quarterly medians, weighed by their sales, in
    years of MIN_SALES sales or more."""
    import re
    rows = []
    for f in sorted((STATS / "dcj_rent_sales").glob("*sales*.xlsx")):
        year = int(re.search(r"(?:mar|jun|sep|dec)[a-z]*[-_](\d{4})", f.name.lower())[1])
        d = pd.read_excel(f, sheet_name="Postcode", header=None)
        head = d.index[d[0].astype(str).str.strip() == "Postcode"][0]
        d.columns = [str(c).replace("\n", " ") for c in d.loc[head]]
        d = d.loc[head + 1:]
        median = next(c for c in d.columns if c.startswith("Median"))
        count = next(c for c in d.columns if c.startswith("Sales"))
        rows.append(pd.DataFrame(dict(
            year=year, postcode=pd.to_numeric(d.Postcode, errors="coerce"), kind=d["Dwelling Type"],
            median=pd.to_numeric(d[median], errors="coerce") * 1000,
            n=pd.to_numeric(d[count].replace("s", 11), errors="coerce"))).dropna())  # "s": 11 to 30 sales, at least 11
    d = pd.concat(rows)
    d = d.assign(w=d["median"] * d.n).groupby(["kind", "postcode", "year"])[["w", "n"]].sum()
    d = (d.w / d.n).where(d.n >= MIN_SALES).rename("price").reset_index()
    years = [int(y) for y in sorted(d.year.unique()) if y < pd.Timestamp.now().year]  # whole years only
    out = {}
    for kind in ("Non Strata", "Strata"):
        k = d[d.kind == kind].pivot(index="postcode", columns="year", values="price").reindex(columns=years)
        out[kind] = years, np.array([k.loc[p].to_numpy(float) if p in k.index else np.full(len(years), np.nan)
                                     for p in s.postcode])
    return out


def measure(key, label, short, unit, years, values, *, log=False, decimals=0, money=False, pct=False,
            census=False, interp=True, what="", note="", source=None):
    """A measure for the viewer. Its ramp runs over the middle 96% of every figure of every year, so a few extremes
    do not wash out the rest, and stays the same from year to year, so change shows."""
    values = np.asarray(values, float)
    v = values[np.isfinite(values) & ((values > 0) if log else True)]
    lo, hi = np.percentile(v, [2, 98])
    return dict(key=key, label=label, short=short, unit=unit, years=[int(y) for y in years],
                values=[[None if not np.isfinite(x) else round(float(x), decimals) for x in row] for row in values],
                domain=[round(float(lo), 2), round(float(hi), 2)], domainCut=bool(v.max() > hi * 1.001), log=log,
                decimals=decimals, money=money, pct=pct, census=census, interp=interp, what=what, note=note,
                source=source)


CENSUS_SRC = dict(label="ABS Census 2011, 2016 and 2021, DataPacks by suburb (CC BY 4.0)",
                  url="https://www.abs.gov.au/census/find-census-data/datapacks")
CRIME_SRC = dict(label="NSW Bureau of Crime Statistics and Research, criminal incidents by suburb (CC BY 4.0)",
                 url="https://bocsar.nsw.gov.au/statistics-dashboards/open-datasets/criminal-offences-data.html")
SALES_SRC = dict(label="NSW Department of Communities and Justice, Rent and Sales Report, by postcode (CC BY 4.0)",
                 url="https://dcj.nsw.gov.au/about-us/families-and-communities-statistics/housing-rent-and-sales/rent-and-sales-report.html")


def measures(s):
    c = census(s)
    cy = sorted(c)
    col = lambda k: np.array([c[y][k].to_numpy(float) for y in cy]).T
    pop, km2 = col("population"), col("km2")
    out = [
        measure("population", "Population", "Population", "people", cy, pop, log=True, census=True,
                what="How many people live in each suburb, as each census counted them. Between censuses the map "
                     "reads a straight line from one count to the next.",
                note="The people who usually live in the suburb, within its boundaries in each census year.",
                source=CENSUS_SRC),
        measure("density", "People per square kilometre", "Density", "people a km²", cy,
                np.where(km2 > 0, pop / km2, np.nan), log=True, census=True,
                what="How closely people live: each census's count over the suburb's whole area.",
                note="The area takes in parks, golf courses, rail yards and university grounds, so a suburb with much "
                     "open space reads sparser than its streets are.", source=CENSUS_SRC),
        measure("income", "Median household income", "Income", "a week", cy, col("income"), money=True, census=True,
                what="The weekly income of the household in the middle: half the suburb's households take home more, "
                     "half less. In the dollars of each census year, not adjusted for inflation.",
                note="Households that did not state their income are left out of the median.", source=CENSUS_SRC),
        measure("degree", "Residents with a university degree", "Education", "of residents 15 and over", cy,
                col("degree"), decimals=1, pct=True, census=True,
                what="The share of residents aged 15 and over whose highest qualification is a bachelor's degree or "
                     "higher: graduate diplomas and certificates, master's degrees and doctorates.",
                note="It counts students still at school or university too, so a suburb with many young residents "
                     "reads lower than its adults' schooling.", source=CENSUS_SRC),
    ]
    # Crime a year for every 1,000 residents: the year's residents read between the censuses, held after the last.
    years, counts = crime_counts(s)
    years = np.array(years)
    keep = years >= cy[0]
    residents = np.array([np.interp(years[keep], cy, row) if np.isfinite(row).all() else np.full(keep.sum(), np.nan)
                          for row in pop])
    rate = np.where(residents >= 300, 1000 * counts[:, keep] / np.maximum(residents, 1), np.nan)
    out.append(measure("crime", "Recorded crime", "Crime", "offences a year per 1,000 residents", years[keep], rate,
                       log=True, interp=False, source=CRIME_SRC,
                       what="Offences against people and property that police recorded in the suburb in a year, for "
                            "every 1,000 people who live there: assault, sexual offences, robbery, break and enter, "
                            "theft, malicious damage and the like.",
                       note="Counted against residents, so places many more people visit than live in (the city "
                            "centre, Haymarket, Bondi Beach, Manly) read high. Offences police find by looking, such "
                            "as drug possession, are left out, and so is fraud. Suburbs of fewer than 300 residents "
                            "have no rate."))
    sale = sales(s)
    for kind, key, label, short, what in (
            ("Non Strata", "house", "Median house price", "Houses", "houses and other homes on their own land"),
            ("Strata", "unit", "Median apartment price", "Apartments", "apartments, townhouses and other strata homes")):
        years, v = sale[kind]
        out.append(measure(key, label, short, "", years, v, log=True, money=True, interp=False, source=SALES_SRC,
                           what=f"The price in the middle of a year's sales of {what}, in the dollars of the year.",
                           note="By postcode, so suburbs that share a postcode share a price (Sydney, Haymarket, The "
                                "Rocks, Millers Point and Barangaroo are all 2000). A quarter of 10 or fewer sales "
                                "has no median and is left out, and so is a year of fewer than 20."))
    return out


def main():
    s, of = suburbs_on_map()
    polys, owner = land_of(s)
    c = to_local(np.c_[s.geometry.representative_point().x, s.geometry.representative_point().y])
    title = lambda n: re.sub(r"\bMc(\w)", lambda m: "Mc" + m[1].upper(), n.title())  # McMahons Point
    out = dict(
        suburbs=[dict(name=title(n), postcode=int(p) if pd.notna(p) else None, km2=round(a / 1e6, 3),
                      buildings=int(nb), x=round(float(x)), z=round(float(z)))
                 for n, p, a, nb, (x, z) in zip(s.suburbname, s.postcode, s.geometry.area, s.buildings, c)],
        poly=owner,
        measures=measures(s),
    )
    write_bin(WEB / "suburbs.bin", of.tobytes())
    write_bin(WEB / "suburbs-land.bin", pack(polys))
    (WEB / "suburbs.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")))
    print(f"{len(s)} suburbs, {(of != NONE).sum()} of {len(of)} buildings placed, {len(polys)} land polygons; "
          f"suburbs-land.bin {(WEB / 'suburbs-land.bin').stat().st_size / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
