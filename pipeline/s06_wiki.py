"""What the building cards say: names, photos, architects, styles, article extracts and heritage listings.

  wiki.json      one entry per Wikidata item a building is linked to (s02_years): label, architects, styles,
                 the Wikipedia lead and a Wikimedia Commons photo with its author and licence
  names.json     OpenStreetMap / Overture names of buildings without a Wikidata entry
  heritage.json  the heritage listing and conservation area each building belongs to
  data/cards.parquet   per building: wk, nm, hi (indexes into the three files, -1 for none), dsrc
"""
import json
import re
import time
from urllib.parse import unquote

import geopandas as gpd
import numpy as np
import pandas as pd
import requests

from .config import DATA, RAW, UA, WEB
from .s02_years import wikidata_items

COMMONS_API = "https://commons.wikimedia.org/w/api.php"
DSRC = {"wikidata": 0, "wikipedia": 1, "osm": 2}


def commons_get(params: dict) -> dict:
    for attempt in range(12):
        r = requests.get(COMMONS_API, params=dict(params, format="json", formatversion=2, maxlag=5),
                         headers={"User-Agent": UA}, timeout=60)
        if r.status_code == 200:
            return r.json()
        wait = float(r.headers.get("retry-after") or 5 * (attempt + 1))
        print(f"  commons {r.status_code}, waiting {wait:.0f} s")
        time.sleep(wait + 1)
    r.raise_for_status()
    return {}


def strip_html(s: str | None) -> str | None:
    if not s:
        return None
    s = re.sub(r"<[^>]+>", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s[:120] or None


def commons_info(files: list[str]) -> dict:
    """Thumbnail, page, author and licence for each Commons file, cached in data/raw/commons.json."""
    cache_p = RAW / "commons.json"
    cache = json.loads(cache_p.read_text()) if cache_p.exists() else {}
    todo = [f for f in files if f not in cache]
    for k in range(0, len(todo), 40):
        batch = todo[k:k + 40]
        d = commons_get(dict(action="query", prop="imageinfo", iiprop="url|extmetadata", iiurlwidth=640,
                             titles="|".join(f"File:{f}" for f in batch)))
        norm = {n["to"]: n["from"] for n in d.get("query", {}).get("normalized", [])}
        for page in d.get("query", {}).get("pages", []):
            title = norm.get(page["title"], page["title"])
            name = title.split(":", 1)[1]
            ii = (page.get("imageinfo") or [{}])[0]
            meta = ii.get("extmetadata", {})
            cache[name] = dict(thumb=ii.get("thumburl"), page=ii.get("descriptionurl"),
                               artist=strip_html(meta.get("Artist", {}).get("value")),
                               license=meta.get("LicenseShortName", {}).get("value"),
                               licenseUrl=meta.get("LicenseUrl", {}).get("value"))
        for f in batch:
            cache.setdefault(f, {})
        print(f"  commons {min(k + 40, len(todo))}/{len(todo)}")
        cache_p.write_text(json.dumps(cache, ensure_ascii=False))
        time.sleep(1.0)
    return cache


def lead(text: str | None, limit=700) -> str | None:
    """The first sentences of an article's lead, up to about `limit` characters."""
    if not text:
        return None
    text = text.split("\n")[0].strip()
    if len(text) <= limit:
        return text
    cut = text[:limit]
    end = max(cut.rfind(". "), cut.rfind(".” "))
    return cut[:end + 1] if end > 200 else cut.rsplit(" ", 1)[0] + "…"


def main():
    b = gpd.read_parquet(DATA / "buildings_dated.parquet")
    wd = wikidata_items().set_index("qid")
    articles = json.loads((RAW / "wikipedia.json").read_text()) if (RAW / "wikipedia.json").exists() else {}

    b["card_q"] = b.qid.fillna(b.qid_area)
    used = [q for q in b.card_q.dropna().unique() if q in wd.index]
    files = sorted({unquote(wd.image[q].rsplit("/", 1)[1]) for q in used if isinstance(wd.image[q], str)})
    info = commons_info(files)

    entries, index = [], {}
    for q in used:
        it = wd.loc[q]
        title = unquote(it.article.rsplit("/wiki/", 1)[1]).replace("_", " ") if isinstance(it.article, str) else None
        art = articles.get(title) if title else None
        img = info.get(unquote(it.image.rsplit("/", 1)[1])) if isinstance(it.image, str) else None
        entries.append(dict(
            qid=q, label=it.label if it.label and not re.fullmatch(r"Q\d+", it.label) else None,
            architects=sorted(it.architects), styles=sorted(it.styles),
            image=img if img and img.get("thumb") else None,
            wiki=dict(url=art.get("url"), title=art.get("title"), extract=lead(art.get("extract"))) if art else None))
        index[q] = len(entries) - 1
    b["wk"] = b.card_q.map(index).fillna(-1).astype(int)

    # Names for the rest: OpenStreetMap's, else Overture's.
    nm = b.osm_name.fillna(b["name"]).where(b.wk < 0)
    nm = nm.where(~nm.fillna("").str.fullmatch(r"\d*"))
    names = sorted(nm.dropna().unique())
    pos = {n: i for i, n in enumerate(names)}
    b["nm"] = nm.map(pos).fillna(-1).astype(int)

    # Heritage: the listing (State register, else local item) and the conservation area.
    kind = np.where(b.shr.notna(), "shr", np.where(b["item"].notna(), "local", None))
    hname = b.shr.fillna(b["item"])
    combos = pd.DataFrame(dict(kind=kind, name=hname, shrId=b.shr_id, hca=b.hca))
    combos["shrId"] = combos.shrId.map(lambda v: str(int(v)) if pd.notna(v) else None)
    has = combos.kind.notna() | combos.hca.notna()
    key = lambda df: df.apply(lambda r: "|".join("" if pd.isna(v) else str(v) for v in r), axis=1)  # noqa: E731
    keys = key(combos[has])
    uniq = combos[has].loc[~keys.duplicated()].reset_index(drop=True)
    uniq_keys = key(uniq)
    kpos = {k: i for i, k in enumerate(uniq_keys)}
    b["hi"] = -1
    b.loc[has, "hi"] = keys.map(kpos).astype(int)
    heritage = [{k: v for k, v in r.items() if isinstance(v, str)} for r in uniq.to_dict("records")]

    b["dsrc"] = b.date_src.map(DSRC).fillna(3).astype(int)
    WEB.mkdir(parents=True, exist_ok=True)
    (WEB / "wiki.json").write_text(json.dumps(entries, ensure_ascii=False, separators=(",", ":")))
    (WEB / "names.json").write_text(json.dumps(names, ensure_ascii=False, separators=(",", ":")))
    (WEB / "heritage.json").write_text(json.dumps(heritage, ensure_ascii=False, separators=(",", ":")))
    b[["bid", "wk", "nm", "hi", "dsrc"]].to_parquet(DATA / "cards.parquet")
    print(f"{len(entries)} wiki entries ({sum(1 for e in entries if e['image'])} with photos, "
          f"{sum(1 for e in entries if e['wiki'])} with articles) on {(b.wk >= 0).sum()} buildings; "
          f"{len(names)} names; {len(heritage)} heritage records on {(b.hi >= 0).sum()} buildings")


if __name__ == "__main__":
    main()
