"""Run the whole pipeline, raw downloads to web/data, in order.

    uv run python -m pipeline.run              # every step (downloads are cached in data/raw)
    uv run python -m pipeline.run s05 s03      # some steps, by prefix
"""
import importlib
import sys
import time

STEPS = [
    "s00_fetch",     # raw inputs (cached)
    "s01_load",      # buildings, parts, heights, the Harbour Bridge
    "s02_years",     # construction years, heritage status, Wikidata links
    "s04_water",     # land, water, the other shores
    "s05_layers",    # context layers
    "s06_wiki",      # card data: Wikipedia, Commons photos, names, listings
    "s03_tiles",     # binary tiles, attrs.bin, sydney.json
    "s07_labels",    # street and harbour names
    "s08_quests",    # quests, every claim checked against Wikipedia
    "s09_export",    # every building as GeoParquet and CSV, to download
    "s10_suburbs",   # suburbs and their figures, for the Suburbs lens
]

if __name__ == "__main__":
    wanted = [s for s in STEPS if not sys.argv[1:] or any(s.startswith(a) for a in sys.argv[1:])]
    for name in wanted:
        t = time.time()
        print(f"── {name}")
        importlib.import_module(f"pipeline.{name}").main() if name != "s00_fetch" else \
            [f() for f in importlib.import_module("pipeline.s00_fetch").STEPS.values()]
        print(f"   {time.time() - t:.0f} s")
