import datetime as dt
import logging
import os
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import ValidationError

# isort: off
from arcgis.gis import GIS
from arcgis.features import Feature, FeatureLayer, FeatureSet
from arcgis.geocoding import geocode
from arcgis.network.analysis import find_routes

# isort: on

from arcgis.geometry.filters import intersects
from geojson_pydantic.features import Feature as GeoJsonFeature
from geojson_pydantic.features import FeatureCollection
from geojson_pydantic.geometries import Point

from segittur_commons.app.entities.route import RouteResult

logger = logging.getLogger(__name__)


class PreserveStops(str, Enum):
    """Options for preserving terminal stops in route calculation."""

    NONE = "Preserve None"
    START = "Preserve First"
    END = "Preserve Last"
    BOTH = "Preserve Both"


class ArcGISService:
    """
    A service for interacting with ArcGIS, allowing you to geocode addresses
    and find routes between them.
    """

    def __init__(self, api_key: str):
        """
            Initializes the ArcGIS service with the provided API key.

        Args:
            api_key (str): The API key for authenticating with ArcGIS Online.
        """
        if not api_key:
            raise ValueError("ARCGIS_API_KEY is not provided.")
        try:
            self.gis = GIS(api_key=api_key)
            logger.info("ArcGIS connection established successfully.")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to ArcGIS: {e}") from e

    def geocode_addresses(
        self,
        addresses: List[str],
        out_sr: Optional[dict[str, Any]] = None,
        max_locations: int = 1,
        category: Optional[str] = None,
        source_country: Optional[str] = None,
        **kwargs: Any,
    ) -> FeatureCollection:
        """
        Geocodes a list of addresses and prepares them as stops for routing.

        Args:
        addresses: A list of address strings to geocode.
        out_sr: The spatial reference system (WKID or WKT) for the output geometries. For example: `{"wkid": 4326}` for WGS84.
        max_locations: The maximum number of locations to return for each address. Default is 1 (best match).
        category: A string to limit search results to a specific category (e.g., "Address", "Street", "Point of Interest").
        source_country: A country code (e.g., "USA", "CAN") to limit the search.
        kwargs: Additional parameters to be passed directly to the `arcgis.geocoding.geocode` function.

        Returns:
        List[FeatureCollection]: A list of GeoJSON FeatureCollection objects, where each represents a stop with its geometry and spatial reference. Returns an empty list if no addresses can be geocoded.
        """

        feature_collections: List[FeatureCollection] = []

        for address in addresses:
            try:
                geocode_result = geocode(
                    address,
                    max_locations=max_locations,
                    as_featureset=True,
                    out_sr=out_sr,
                    category=category,
                    source_country=source_country,
                    **kwargs,
                )
            except Exception as e:
                logger.error(f"Error in geocode for '{address}': {e}")
                continue

            if geocode_result:
                # best_match = geocode_result[0]
                try:
                    fc = FeatureCollection.model_validate_json(geocode_result.to_geojson)
                    feature_collections.append(fc)
                except (ValidationError, AttributeError) as e:
                    logger.error(
                        f"Failed to convert geocode result for '{address}' to GeoJSON: {e}"
                    )
            else:
                logger.warning(f"No matches found for address: '{address}'")

        return self._flatten_featuresets(feature_collections)

    def _flatten_featuresets(
        self, feature_collections: List[FeatureCollection]
    ) -> FeatureCollection:
        all_features: List[GeoJsonFeature] = []
        object_id_counter = 1

        for fc in feature_collections:
            if fc and fc.features:
                for i, feature in enumerate(fc.features):
                    if feature.properties is None:
                        feature.properties = {}
                    feature.properties["OBJECTID"] = object_id_counter
                    all_features.append(feature)
                    object_id_counter += 1

        return FeatureCollection(type="FeatureCollection", features=all_features)

    def find_optimal_route(
        self,
        stops_data: str,
        time_of_day: Optional[int] = None,
        time_zone_for_time_of_day: str = "UTC",
        preserve_terminal_stops: PreserveStops = PreserveStops.NONE,
    ) -> Optional[RouteResult]:
        """
        Finds the optimal route between a series of geocoded stops provided as a GeoJSON string.

        Args:
            stops_data (str): A string containing a valid GeoJSON FeatureCollection of stop points. This is typically the output from the `geocode_addresses` tool.
            time_of_day (Optional[int]): The route's start time in milliseconds since the Unix epoch. If None, uses the current time.
            time_zone_for_time_of_day (str): Time zone for the start time. Defaults to "UTC".
            preserve_terminal_stops (PreserveStops): Determines whether to preserve the start/end points. Defaults to PreserveStops.NONE.

        Returns:
        Optional[RouteResult]: A RouteResult object containing the route details. Returns None if there are not enough stops or if an error occurs.

        Raises:
        ValueError: If not enough stops are provided to calculate a route.
        """
        try:
            stops_fc = FeatureCollection.model_validate_json(stops_data)
        except ValidationError as e:
            logger.error(f"Invalid GeoJSON format for stops_data: {e}")
            raise ValueError("The provided stops_data is not a valid GeoJSON FeatureCollection.") from e

        if not stops_fc or len(stops_fc.features) < 2:
            raise ValueError("At least two stops are required to calculate a route.")

        if time_of_day is None:
            current_time_ms = int(dt.datetime.now().timestamp() * 1000)
        else:
            current_time_ms = time_of_day

        logger.info(
            "Calculating route for %d stops at %s...",
            len(stops_fc.features),
            dt.datetime.fromtimestamp(current_time_ms / 1000),
        )

        # Convert our Pydantic model back to an ArcGIS FeatureSet just for the API call
        geojson_dict = stops_fc.model_dump(mode="json")
        arcgis_stops_fs = FeatureSet.from_geojson(geojson_dict)

        try:
            result = find_routes(
                arcgis_stops_fs,
                time_of_day=current_time_ms,
                time_zone_for_time_of_day=time_zone_for_time_of_day,
                preserve_terminal_stops=preserve_terminal_stops.value,
            )
            return RouteResult(
                output_stops=FeatureCollection.model_validate_json(result.output_stops.to_geojson),
                output_routes=FeatureCollection.model_validate_json(
                    result.output_routes.to_geojson
                ),
                output_directions=FeatureCollection.model_validate_json(
                    result.output_direction_lines.to_geojson
                ),
            )
        except (ValidationError, AttributeError, Exception) as e:
            logger.error(f"Error calculating route or processing result: {e}")
            return None

    def get_nearby_pois(
        self,
        entity: FeatureCollection = None,
        feature_layer_url: str = None,
        where_clause: str = None,
        distance: int = 100,
        result_record_count: int = 200,
        **kwargs: Any,
    ):
        if not feature_layer_url:
            raise ValueError("No feature_layer_url provided")

        if not (entity and entity.features):
            logger.warning("Cannot get nearby POIs from an empty or invalid entity.")
            return None

        feature_layer = FeatureLayer(feature_layer_url)

        # Convert our Pydantic geometry back to a dictionary for the ArcGIS API
        # Ensure we are dealing with a Point geometry for querying nearby POIs
        if not (entity.features and isinstance(entity.features[0].geometry, Point)):
            logger.error(
                "Expected a GeoJSON Point geometry for nearby POIs query, but received a different type or empty entity."
            )
            return None

        geometry_dict = entity.features[0].geometry.model_dump()

        # The ArcGIS API expects a Geometry object or a dictionary.
        geometry = geometry_dict
        # GeoJSON does not have a spatialReference field, ArcGIS API assumes WGS84 (4326) for GeoJSON dicts.
        result_query = feature_layer.query(
            where=where_clause,
            distance=distance,
            units="esriSRUnit_Meter",
            out_sr=4326,
            geometry_filter=intersects(geometry=geometry),
            result_record_count=result_record_count,
            **kwargs,
        )

        return result_query
