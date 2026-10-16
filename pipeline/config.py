"""The area, the coordinate frame and the shared paths.

The map covers the City of Sydney and North Sydney, the two local government areas either side of the
Harbour Bridge, the harbour councils around them (Mosman, Woollahra, Lane Cove and Hunters Hill) and, of the
Inner West, only the Balmain peninsula. Everything is projected to GDA2020 / MGA zone 56 (EPSG:7856) and then to
the viewer's local frame: metres from the General Post Office in Martin Place, the point NSW measures its road
distances from; x east, z south (three.js, y up).
"""
from pathlib import Path

CRS = 7856                                  # GDA2020 / MGA zone 56
LGAS = ["SYDNEY", "NORTH SYDNEY", "MOSMAN", "WOOLLAHRA", "LANE COVE", "HUNTERS HILL", "WAVERLEY"]  # NSW Spatial Services lganame
# Councils taken only in part: the suburbs of each to keep (NSW Spatial Services suburbname values). The rest of the
# Inner West runs inland to Marrickville and Ashfield, the rest of Canada Bay to Concord, Willoughby's
# to Chatswood.
PARTS = {"INNER WEST": ["BALMAIN", "BALMAIN EAST", "BIRCHGROVE", "ROZELLE", "LILYFIELD"],
         "CANADA BAY": ["DRUMMOYNE", "RUSSELL LEA", "RODD POINT", "FIVE DOCK", "ABBOTSFORD", "CHISWICK", "WAREEMBA"],
         "WILLOUGHBY": ["NORTHBRIDGE", "CASTLECRAG", "MIDDLE COVE", "CASTLE COVE", "NAREMBURN"]}
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
