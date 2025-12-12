from typing import List

from geojson_pydantic.features import FeatureCollection
from pydantic import BaseModel


class RouteManeuver(BaseModel):
    """
    Represents a single, simplified turn-by-turn instruction for a route.
    """

    instruction: str
    distance: float
    arrive_time: float

    class Config:
        from_attributes = True


class ManeuverList(BaseModel):
    items: List[RouteManeuver]


class RouteResponse(BaseModel):
    """
    Represents the result of a route calculation using standard GeoJSON FeatureCollections.
    """

    output_stops: FeatureCollection
    output_routes: FeatureCollection
    output_directions: ManeuverList
