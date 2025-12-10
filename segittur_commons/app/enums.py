from enum import Enum


class TravelMode(str, Enum):
    driving_time = "Driving Time"
    driving_distance = "Driving Distance"
    rural_driving_time = "Rural Driving Time"
    rural_driving_distance = "Rural Driving Distance"
    walking_time = "Walking Time"
    walking_distance = "Walking Distance"
    custom = "Custom"


class PreserveStops(str, Enum):
    """Options for preserving terminal stops in route calculation."""

    NONE = "Preserve None"
    START = "Preserve First"
    END = "Preserve Last"
    BOTH = "Preserve First and Last"


class GeocodeCategory(str, Enum):
    POI = "POI"
    Address = "Address"
    Postal = "Postal"
