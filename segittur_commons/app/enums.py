from enum import Enum


class TravelMode(str, Enum):
    fastest = "fastest"
    shortest = "shortest"
    driving = "Driving Time"
    trucking = "Trucking Time"
    walking = "Walking Time"
    cycling = "Biking Time"


class PreserveStops(str, Enum):
    """Options for preserving terminal stops in route calculation."""

    NONE = "Preserve None"
    START = "Preserve First"
    END = "Preserve Last"
    BOTH = "Preserve Both"


class GeocodeCategory(str, Enum):
    POI = "POI"
    Address = "Address"
    Postal = "Postal"
