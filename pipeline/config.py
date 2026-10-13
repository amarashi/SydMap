"""The area, the coordinate frame and the shared paths.

The map covers the City of Sydney and North Sydney, the two local government areas either side of the
Harbour Bridge. Everything is projected to GDA2020 / MGA zone 56 (EPSG:7856) and then to the viewer's
local frame: metres from the General Post Office in Martin Place, the point NSW measures its road
distances from; x east, z south (three.js, y up).
"""
from pathlib import Path

CRS = 7856                                  # GDA2020 / MGA zone 56
LGAS = ["SYDNEY", "NORTH SYDNEY"]           # NSW Spatial Services lganame values
GPO_LONLAT = (151.20765, -33.86778)         # the GPO clock tower, Martin Place
# A box that holds both LGAs with a margin of harbour around them (lon/lat).
BBOX = (151.155, -33.94, 151.25, -33.81)

RAW = Path("data/raw")
DATA = Path("data")
WEB = Path("web/data")
UA = "SydMap/0.1 (https://github.com/amarashi/SydMap)"


def gpo_mga():
    """The GPO in MGA zone 56 metres."""
    from pyproj import Transformer
    return Transformer.from_crs(4326, CRS, always_xy=True).transform(*GPO_LONLAT)
