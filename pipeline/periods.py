"""Sydney periods. Boundaries follow the city's turning points, not decades; the colours are the
Amsterdam map's ramp, oxblood for the oldest through ochre and green to slate and violet."""
PERIODS = [
    # (key, label, start, end, colour)
    ("p1", "Before 1840 The convict town",          1788, 1839, "#4a1410"),
    ("p2", "1840–1869 Free colony and gold",        1840, 1869, "#8c1c13"),
    ("p3", "1870–1890 The boom years",              1870, 1890, "#c0462b"),
    ("p4", "1891–1918 Depression and Federation",   1891, 1918, "#d97a2b"),
    ("p5", "1919–1945 Interwar and the Bridge",     1919, 1945, "#e5b13a"),
    ("p6", "1946–1960 Post-war",                    1946, 1960, "#8e9f3c"),
    ("p7", "1961–1975 The first towers",            1961, 1975, "#3f8f6b"),
    ("p8", "1976–1999 Darling Harbour to the Games", 1976, 1999, "#2c7391"),
    ("p9", "2000–2014 The apartment city",          2000, 2014, "#3a4f9a"),
    ("p10", "2015– Barangaroo and Green Square",    2015, 2100, "#6a3f8f"),
]


def period_index(year: int) -> int:
    for i, (_, _, a, b, _) in enumerate(PERIODS):
        if a <= year <= b:
            return i
    return 0 if year < PERIODS[0][2] else len(PERIODS) - 1
