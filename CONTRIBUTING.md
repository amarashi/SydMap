# Contributing

## Add a context layer

A layer is a set of buildings with a story: a hand-picked list with a note for each, or a rule over an open dataset.
Layers live in [`pipeline/s05_layers.py`](pipeline/s05_layers.py), one function each:

```python
@layer(id="wool", section="The changing city", title="Wool stores", era="1880–1930",
       text="Two or three sentences on what the layer shows and why it matters.",
       caveat="What the layer leaves out, if anything.",
       source=("Who published the data, and its licence", "https://link.to/the/data"),
       groups=[("store", "Wool store"), ("bond", "Bond store")])
def wool():
    b = buildings()                         # every building, with its year, heritage and OSM tags
    ...
    return {bid: "store"}                   # or {bid: ("store", dict(name=..., story=..., source=url))}
```

- `section` is one of: Country, Architecture, Faith and community, Everyday life, The changing city, The modern city.
- Up to eight groups per layer, and 64 groups across all layers.
- Use open data only (CC0, CC BY, ODbL or the like) and say where it comes from in `source`.
- `at_points(points, radius)` finds the building at or nearest each point; `osm_points(...)` reads OpenStreetMap POIs.

Then run `uv run python -m pipeline.run s05 s06 s03 s09` and look at it with `python3 scripts/serve.py`.

## Add a quest

Quests are in [`pipeline/quests.py`](pipeline/quests.py). Every claim a step makes needs a Wikipedia article and the
exact strings it must contain:

```python
find("wd:Q54518",                                     # the building(s) linked to this Wikidata item
     "Find the Romanesque Revival marketplace that fills a whole city block.",
     ["The block is bounded by George, Market, York and Druitt streets."],
     "The Queen Victoria Building, designed by George McRae and built between 1893 and 1898.",
     [("Queen Victoria Building", ["Designed by the architect George McRae", "constructed between 1893 and 1898"])])
```

`uv run python -m pipeline.checks` checks every claim against the live articles; `s08_quests` drops any step whose
checks fail, that finds no building, or that asks for a year the map does not give the building.

## Style

Write in Australian English, in short plain sentences. Name your sources. Do not make persecution or loss into a game.
