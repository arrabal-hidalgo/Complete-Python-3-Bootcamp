import datetime as dt
import logging
import os
from typing import Any, Dict, List, Optional

# isort: off
from arcgis.gis import GIS
from arcgis.features import Feature, FeatureLayer, FeatureSet
from arcgis.geocoding import geocode
from arcgis.network.analysis import find_routes

# isort: on

from arcgis.geometry import Geometry, Point
from arcgis.geometry.filters import intersects

from segittur_commons.app.entities.route import RouteResult

logger = logging.getLogger(__name__)


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
    ) -> List[FeatureSet]:
        """
        Geocodes a list of addresses and prepares them as stops for routing.

        Args:
            addresses (List[str]): A list of address strings to geocode.
            out_sr: The spatial reference system (WKID or WKT) for the output geometries.
                For example: `{"wkid": 4326}` for WGS84.
            max_locations: The maximum number of locations to return for each address.
                Default is 1 (best match).
            category: A string to limit search results to a specific category (e.g., "Address", "Street", "Point of Interest").
            source_country: A country code (e.g., "USA", "CAN") to limit the search.
            **kwargs: Additional parameters to be passed directly to the `arcgis.geocoding.geocode` function.

        Returns:
            List[FeatureSet]: A list of FeatureSet
            represents a stop with its geometry and spatial reference.
            Returns an empty list if no addresses can be geocoded.
        """

        featuresets: List[FeatureSet] = []

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
                featuresets.append(geocode_result)
            else:
                logger.warning(f"No matches found for address: '{address}'")

        return featuresets

    def flatten_featuresets(self, featuresets: List[FeatureSet]):
        all_features = []
        object_id_counter = 1

        for fs in featuresets:
            if fs and fs.features:
                for feature in fs.features:
                    feature.attributes["OBJECTID"] = object_id_counter
                    all_features.append(feature)
                    object_id_counter += 1

        return FeatureSet(all_features)

    def find_optimal_route(
        self,
        stops_data: FeatureSet,
        time_of_day: Optional[int] = None,
        time_zone_for_time_of_day: str = "UTC",
        preserve_terminal_stops: str = "Preserve None",
    ) -> Optional[RouteResult]:
        """
        Finds the optimal route between a series of geocoded stops.

        Args:
            stops_data (List[Dict[str, Any]]): A list of stop dictionaries,
            obtained from `geocode_addresses`.
            time_of_day (Optional[int]): The route's start time in milliseconds since the Unix epoch.
            If None, uses the current time.
            time_zone_for_time_of_day (str): Time zone for the start time.
            Defaults to "UTC".
            preserve_terminal_stops (str): Determines whether to preserve the start/end points.
            Defaults to "Preserve None".

        Returns:
            Optional[RouteResult]: A RouteResult object containing the route details.
            Returns None if there are not enough stops or if an error occurs.

        Raises:
            ValueError: If not enough stops are provided to calculate a route.
        """

        if not stops_data or len(stops_data.features) < 2:
            raise ValueError("At least two stops are required to calculate a route.")

        if time_of_day is None:
            current_time_ms = int(dt.datetime.now().timestamp() * 1000)
        else:
            current_time_ms = time_of_day

        logger.info(
            "Calculating route for %d stops at %s...",
            len(stops_data.features),
            dt.datetime.fromtimestamp(current_time_ms / 1000),
        )

        try:
            result = find_routes(
                stops_data,
                time_of_day=current_time_ms,
                time_zone_for_time_of_day=time_zone_for_time_of_day,
                preserve_terminal_stops=preserve_terminal_stops,
            )
            return RouteResult(**result)
        except Exception as e:
            logger.error(f"Error calculating route: {e}")
            return None

    def get_nearby_pois(
        self,
        entity: FeatureSet = None,
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

        geometry = entity.features[0].geometry
        spatial_reference = geometry["spatialReference"]
        result_query = feature_layer.query(
            where=where_clause,
            distance=distance,
            units="esriSRUnit_Meter",
            out_sr=4326,
            geometry_filter=intersects(geometry=geometry, sr=spatial_reference),
            result_record_count=result_record_count,
            **kwargs,
        )

        return result_query
