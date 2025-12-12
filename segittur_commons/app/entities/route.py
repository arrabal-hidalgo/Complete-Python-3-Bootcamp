from typing import List

from geojson_pydantic.features import FeatureCollection
from pydantic import BaseModel



class RouteResponse(BaseModel):
    """
    Represents the result of a route calculation using standard GeoJSON FeatureCollections.
    """

    output_stops: FeatureCollection
    output_routes: FeatureCollection
    output_directions: ManeuverList
