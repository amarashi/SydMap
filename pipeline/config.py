"""The area, the coordinate frame and the shared paths.

The map covers both shores of Sydney Harbour and the Parramatta River and the ocean coast from Bondi to Coogee: the
local government areas (LGAs) in LGAS whole, and the suburbs in PARTS of the councils taken in part. Everything is
projected to GDA2020 / MGA zone 56 (EPSG:7856) and then to the viewer's local frame: metres from the General Post
Office in Martin Place, the point NSW measures its road distances from; x east, z south (three.js, y up).
"""
from pathlib import Path

CRS = 7856                                  # GDA2020 / MGA zone 56
# Councils taken whole (NSW Spatial Services lganame values).
LGAS = ["SYDNEY", "NORTH SYDNEY", "MOSMAN", "WOOLLAHRA", "LANE COVE", "HUNTERS HILL", "WAVERLEY", "INNER WEST",
        "WILLOUGHBY", "CANADA BAY"]
# Councils taken only in part: the suburbs of each to keep (NSW Spatial Services suburbname values). The rest of
# the Northern Beaches runs to Palm Beach, Ryde's to Macquarie Park, Randwick's to La Perouse.
PARTS = {"NORTHERN BEACHES": ["MANLY", "FAIRLIGHT", "BALGOWLAH", "BALGOWLAH HEIGHTS", "CLONTARF", "SEAFORTH",
                              "QUEENSCLIFF", "FRESHWATER", "CURL CURL", "NORTH MANLY", "MANLY VALE",
                              "NORTH BALGOWLAH"],
         "RYDE": ["GLADESVILLE", "PUTNEY", "TENNYSON POINT"],
         "RANDWICK": ["CLOVELLY", "COOGEE", "SOUTH COOGEE", "RANDWICK", "KENSINGTON", "KINGSFORD",
                      "CENTENNIAL PARK"]}
GPO_LONLAT = (151.20765, -33.86778)         # the GPO clock tower, Martin Place
# A box that holds the LGAs with a margin of harbour around them (lon/lat), from Putney to Manly and from Seaforth
# to South Coogee, so suburbs can be added within it without downloading the rest again.
BBOX = (151.08, -33.95, 151.32, -33.765)

RAW = Path("data/raw")
DATA = Path("data")
WEB = Path("web/data")
UA = "SydMap/0.1 (https://github.com/amarashi/SydMap)"


def gpo_mga():
    """The GPO in MGA zone 56 metres."""
    from pyproj import Transformer
    return Transformer.from_crs(4326, CRS, always_xy=True).transform(*GPO_LONLAT)
