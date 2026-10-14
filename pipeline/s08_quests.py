"""Resolve the quests (quests.py) to buildings, check every claim, write web/data/quests.json.

A step is dropped, with a warning, when its place resolves to no building, when one of its checks fails
(pipeline/checks.py), or when it asks for a year the map does not give that building. A quest left with fewer than
three steps is dropped too.
"""
import json

import geopandas as gpd

from .checks import failures, url
from .config import DATA, WEB
from .quests import QUESTS


def main():
    b = gpd.read_parquet(DATA / "buildings_dated.parquet")
    by_qid = b.groupby("qid").bid.apply(list).to_dict()
    by_id = dict(zip(b.id, b.bid))
    year_of = dict(zip(b.bid, b.year))
    out = []
    for q in QUESTS:
        steps = []
        for i, s in enumerate(q["steps"]):
            kind, ref = s["at"].split(":", 1)
            gids = by_qid.get(ref, []) if kind == "wd" else [by_id[ref]] if ref in by_id else []
            # The building a step is about first: for a year, the one the map dates as the step does.
            if s["kind"] == "year":
                gids = sorted(gids, key=lambda g: year_of[g] != s["year"])
            bad = failures(s["checks"])
            problem = ("no building" if not gids else "; ".join(bad) if bad
                       else f"map year {year_of[gids[0]]} ≠ {s['year']}" if s["kind"] == "year" and year_of[gids[0]] != s["year"]
                       else None)
            if problem:
                print(f"  ✗ {q['id']} step {i + 1}: {problem}")
                continue
            step = {k: v for k, v in s.items() if k not in ("at", "checks") and v not in (None, False)}
            step["gids"] = [int(g) for g in (gids[:1] if s["kind"] != "find" else gids)]
            step["sources"] = list(dict.fromkeys(url(t) for t, _ in s["checks"]))
            steps.append(step)
        if len(steps) >= 3:
            out.append(dict(id=q["id"], level=q["level"], title=q["title"], intro=q["intro"], steps=steps))
        print(f"{q['id']:10s} {len(steps)}/{len(q['steps'])} steps")
    (WEB / "quests.json").write_text(json.dumps(out, ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
