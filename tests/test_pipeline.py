"""Offline tests: the date parsers, the tile format, the Opera House's shells, the fact-check normaliser. No network,
no data downloads."""
import struct

import numpy as np
import shapely

from pipeline.checks import norm
from pipeline.landmarks import OPERA_TOP, SPHERE, SPRING, Mesh, half_shell, opera_house, sphere_centre
from pipeline.periods import PERIODS, period_index
from pipeline.s02_years import INSTITUTION_WORDS, class_text, parse_osm_date, parse_wiki_built
from pipeline.s03_tiles import ATTR_DTYPE, GPO, MAGIC, PALE, pack_tile


def test_osm_dates():
    assert parse_osm_date("1885") == (1885, 1885, 1885, False)
    assert parse_osm_date("1885-03-01") == (1885, 1885, 1885, False)
    assert parse_osm_date("1880s") == (1885, 1880, 1889, True)
    assert parse_osm_date("C19") == (1850, 1800, 1899, True)
    assert parse_osm_date("~1890") == (1890, 1890, 1890, True)
    assert parse_osm_date("1885..1890") == (1885, 1885, 1890, True)
    assert parse_osm_date(None) is None and parse_osm_date("unknown") is None


def test_wikipedia_built_years():
    # The forms the NSW heritage articles use.
    assert parse_wiki_built("It was designed by Walter Liberty Vernon and built from 1898 to 1900.") == (1900, 1898, 1900, False)
    assert parse_wiki_built("It was built during 1852.") == (1852, 1852, 1852, False)
    assert parse_wiki_built("Built between 1811 and 1816 as the southern wing") == (1816, 1811, 1816, False)
    # A long build is dated by its start, and marked approximate.
    assert parse_wiki_built("the cathedral was built from 1866 to 1928.") == (1866, 1866, 1928, True)
    assert parse_wiki_built("The house was built in the 1880s.") == (1885, 1880, 1889, True)
    assert parse_wiki_built("It was built by 1840.") == (1840, 1830, 1840, True)
    assert parse_wiki_built("The parish dates from 1838 and the church building from 1845.") == (1845, 1845, 1845, False)
    assert parse_wiki_built("A park in the city.") is None


def test_periods_cover_every_year():
    for y in range(1788, 2027):
        lo, hi = PERIODS[period_index(y)][2:4]
        assert lo <= y <= hi
    starts = [p[2] for p in PERIODS]
    assert starts == sorted(starts)


def test_tile_round_trip():
    """A packed tile reads back as web/worker.js reads it: same counts, same heights, vertices in decimetres."""
    at = lambda pts: shapely.Polygon([(GPO[0] + x, GPO[1] + y) for x, y in pts])  # noqa: E731  (MGA, near the GPO)
    sq = at([(10, 10), (30, 10), (30, 25), (10, 25)])
    tower = at([(15, 12), (25, 12), (25, 20), (15, 20)])
    shell = (np.array([[GPO[0] + 10, GPO[1] + 10, 0.0], [GPO[0] + 30, GPO[1] + 10, 0.0], [GPO[0] + 20, GPO[1] + 20, 40.0]]),
             np.array([[0, 1, 2]]), True)
    rows = [dict(gid=7, year=1932, flag=0, period=4, floors=3, heritage=1, lay0=5, lay1=0,
                 parts=[(12.0, 0.0, sq), (80.0, 12.0, tower)]),
            dict(gid=8, year=1973, flag=0, period=6, floors=5, heritage=1, lay0=0, lay1=0,
                 parts=[(16.0, 0.0, sq)], mesh=shell)]
    origin = np.array([0.0, 0.0])
    buf = pack_tile(origin, rows)
    magic, nB, nP, nR, nV, nMV, nMT = struct.unpack_from("<7I", buf)
    assert (magic, nB, nP, nR, nV, nMV, nMT) == (MAGIC, 2, 3, 3, 12, 3, 1)
    o = 36
    def take(dtype, n):
        nonlocal o
        a = np.frombuffer(buf, dtype, n, o)
        o += -(-n * np.dtype(dtype).itemsize // 4) * 4
        return a
    gid, year = take("<u4", 2), take("<i2", 2)
    for _ in range(4):
        take("u1", 2)
    take("<u4", 2); take("<u4", 2); part_start = take("<u4", 3)
    height, base = take("<f4", 3), take("<f4", 3)
    ring_start, vert_start, hole = take("<u4", 4), take("<u4", 4), take("u1", 3)
    xz = take("<i2", 2 * nV).reshape(-1, 2)
    assert list(gid) == [7, 8] and year[0] == 1932 and list(part_start) == [0, 2, 3]
    assert list(height) == [12.0, 80.0, 16.0] and list(base) == [0.0, 12.0, 0.0]
    assert list(ring_start) == [0, 1, 2, 3] and list(vert_start) == [0, 4, 8, 12] and not hole.any()
    # x east, z south, in decimetres from the tile origin.
    assert set(map(tuple, xz[:4])) == {(100, -100), (300, -100), (300, -250), (100, -250)}
    # The mesh: its building's index in the tile (marked pale), then x, height, z in decimetres, then the triangles.
    mesh_bld, mesh_pos, mesh_tri = take("<u2", nMV), take("<i2", 3 * nMV).reshape(-1, 3), take("<u2", 3 * nMT)
    assert list(mesh_bld) == [1 | PALE] * 3 and list(mesh_tri) == [0, 1, 2]
    assert mesh_pos.tolist() == [[100, 0, -100], [300, 0, -100], [200, 400, -200]]
    assert o == len(buf)


def test_opera_house_shells():
    """Every half-shell lies on one 75.2 m sphere through its pedestal, tip and back corner, on its own side of the
    hall's axis, and the whole roof tops out at the documented 67 m."""
    tip, back, ped = np.array([-5.0, 0, 67.0]), np.array([-49.7, 0, 32.7]), np.array([-24.0, 25.0, 12.6])
    v, t = half_shell(tip, back, ped)
    c = sphere_centre(np.array([ped, tip, back]), SPHERE, np.array([0.0, 1.0, 1.0]))
    assert np.allclose(np.linalg.norm(v - c, axis=1), SPHERE)
    assert np.allclose(v[0], ped) and np.allclose(v[12], tip) and np.allclose(v[-1], back)
    assert v[:, 1].min() > -1e-9 and t.max() < len(v)
    verts, tris = opera_house()
    assert abs(verts[:, 2].max() - OPERA_TOP) < 1e-6 and verts[:, 2].min() >= SPRING - 1e-6
    assert tris.max() < len(verts) <= 0x10000


def test_bridge_beam_is_closed():
    """A beam is a closed box along its path: four corners a section, every edge shared by two triangles."""
    m = Mesh()
    m.beam([(0, 0, 0), (10, 0, 5), (20, 0, 0)], 2.0, 1.0)
    v, t = np.concatenate(m.verts), np.concatenate(m.tris)
    assert v.shape == (12, 3) and t.max() == 11
    edges = {}
    for tri in t:
        for a, b in ((tri[0], tri[1]), (tri[1], tri[2]), (tri[2], tri[0])):
            edges[tuple(sorted((a, b)))] = edges.get(tuple(sorted((a, b))), 0) + 1
    assert set(edges.values()) == {2}
    # a vertical member keeps its full section
    m = Mesh()
    m.beam([(0, 0, 0), (0, 0, 10)], 2.0, 4.0)
    v = m.verts[0]
    assert np.ptp(v[:, 1]) == 2.0 and np.ptp(v[:, 0]) == 4.0


def test_institution_classes_do_not_depend_on_order():
    """Wikidata classes are a set: whether an item counts as an institution must not depend on their order."""
    for classes, institution in [({"railway station", "heritage site"}, True), ({"road-rail bridge", "steel bridge"}, False),
                                 ({"road"}, True), ({"substation"}, False), ({"station building"}, False)]:
        for order in (sorted(classes), sorted(classes, reverse=True)):
            assert bool(INSTITUTION_WORDS.search(class_text(order))) == institution, classes


def test_attr_record_is_aligned():
    assert ATTR_DTYPE.itemsize % 4 == 0
    assert ATTR_DTYPE.fields["osm"][1] == 0          # the f8 first, read with getFloat64


def test_check_normaliser():
    assert norm("Sydney’s “oldest” pub – 1828") == norm("Sydney's \"oldest\" pub - 1828")


def test_site_files_fit_cloudflare():
    # Cloudflare serves no static file over 25 MiB, and a deploy with one fails. The downloads are split by council so
    # that no file grows with the whole map.
    from pathlib import Path
    big = [f"{f} {f.stat().st_size / 2**20:.1f} MiB" for f in Path("web").rglob("*") if f.is_file()
           and f.stat().st_size > 20 * 2**20]
    assert not big, f"files near or over Cloudflare's 25 MiB limit: {big}"
