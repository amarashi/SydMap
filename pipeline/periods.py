"""Sydney periods. Boundaries follow the city's turning points, not decades. The colours are The Third Script's:
wine and rust for the convict and colonial town, a coral terracotta for the boom years (clear of the logo's sun, which
the page keeps for its mark), then clay, sandstone, lichen and eucalypt, a harbour teal, the logo's cypress teal and a
dusk violet for the newest city. Neighbours are checked for colour-blind separation (design/README.md)."""
PERIODS = [
    # (key, label, start, end, colour)
    ("p1", "Before 1840 The convict town",          1788, 1839, "#491321"),
    ("p2", "1840–1869 Free colony and gold",        1840, 1869, "#7c2d18"),
    ("p3", "1870–1890 The boom years",              1870, 1890, "#c0594e"),
    ("p4", "1891–1918 Depression and Federation",   1891, 1918, "#e38752"),
    ("p5", "1919–1945 Interwar and the Bridge",     1919, 1945, "#e0ca78"),
    ("p6", "1946–1960 Post-war",                    1946, 1960, "#859f55"),
    ("p7", "1961–1975 The first towers",            1961, 1975, "#35816a"),
    ("p8", "1976–1999 Darling Harbour to the Games", 1976, 1999, "#77b0b7"),
    ("p9", "2000–2014 The apartment city",          2000, 2014, "#4a798d"),
    ("p10", "2015– Barangaroo and Green Square",    2015, 2100, "#5b4087"),
]


def period_index(year: int) -> int:
    for i, (_, _, a, b, _) in enumerate(PERIODS):
        if a <= year <= b:
            return i
    return 0 if year < PERIODS[0][2] else len(PERIODS) - 1
