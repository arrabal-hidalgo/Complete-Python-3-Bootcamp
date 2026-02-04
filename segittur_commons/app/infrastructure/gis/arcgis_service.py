import datetime as dt
import logging
from typing import Any, List, Optional

from pydantic import ValidationError

# isort: off
from arcgis.gis import GIS
from arcgis.features import FeatureLayer, FeatureSet
from arcgis.geocoding import geocode
from arcgis.network.analysis import find_routes

# isort: on

from arcgis.geometry.filters import intersects
from geojson_pydantic.features import Feature as GeoJsonFeature
from geojson_pydantic.features import FeatureCollection
from geojson_pydantic.geometries import Point

from segittur_commons.app.entities.route import (
    ManeuverList,
    RouteManeuver,
    RouteResponse,
)
from segittur_commons.app.enums import PreserveStops

logger = logging.getLogger(__name__)


class ArcGISService:
    """
    Service for interacting with ArcGIS: geocoding addresses and calculating optimal routes.
    """

    def __init__(self, api_key: str):
        if not api_key:
            raise ValueError("ARCGIS_API_KEY is not provided.")
        try:
            self.gis = GIS(api_key=api_key)
            logger.info("ArcGIS connection established successfully.")
        except Exception as e:
            raise ConnectionError(f"Cannot connect to ArcGIS: {e}") from e

    # --------------------------
    # Geocoding
    # --------------------------
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
        Geocode a list of addresses and return a unified FeatureCollection.

        Args:
            addresses: List of addresses to geocode.
            out_sr: Output spatial reference, e.g., {"wkid": 4326}.
            max_locations: Max matches per address.
            category: Optional category filter for geocoding.
            source_country: Optional country code filter.
            kwargs: Additional params for arcgis.geocoding.geocode.

        Returns:
            FeatureCollection: All geocoded stops combined into one FeatureCollection.
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
                logger.error(f"Error geocoding '{address}': {e}")
                continue

            if isinstance(geocode_result, FeatureSet) and geocode_result.features:
                try:
                    fc: FeatureCollection = FeatureCollection.model_validate_json(
                        geocode_result.to_geojson
                    )
                    feature_collections.append(fc)
                except (ValidationError, AttributeError) as e:
                    logger.error(
                        f"Failed to convert geocode result for '{address}' to FeatureCollection: {e}"
                    )
            else:
                logger.warning(f"No matches found for address: '{address}'")

        return self._flatten_featuresets(feature_collections)

    def _flatten_featuresets(
        self, feature_collections: List[FeatureCollection]
    ) -> FeatureCollection:
        """
        Merge multiple FeatureCollections into a single FeatureCollection.
        """
        all_features: List[GeoJsonFeature] = []
        object_id_counter = 1

        for fc in feature_collections:
            if fc and fc.features:
                for feature in fc.features:
                    if feature.properties is None:
                        feature.properties = {}
                    feature.properties["OBJECTID"] = object_id_counter
                    all_features.append(feature)
                    object_id_counter += 1

        return FeatureCollection(type="FeatureCollection", features=all_features)

    # --------------------------
    # Routing
    # --------------------------
    def find_optimal_route(
        self,
        stops_data: FeatureCollection,
        time_of_day: Optional[dt.datetime] = None,
        time_zone_for_time_of_day: str = "UTC",
        preserve_terminal_stops: PreserveStops = PreserveStops.NONE,
        travel_mode: Optional[str] = None,
        **arcgis_route_params: Any,
    ) -> Optional[RouteResponse]:
        """
        Finds the optimal route between a series of geocoded stops.

        Args:
            stops_data (FeatureCollection): GeoJSON FeatureCollection of stop points.
            time_of_day (Optional[datetime]): Start time in milliseconds since epoch. Defaults to current time.
            time_zone_for_time_of_day (str): Time zone for the start time. Defaults to "UTC".
            preserve_terminal_stops (PreserveStops): Whether to preserve start/end stops.
            travel_mode (Optional[str]): The travel mode to use for the route calculation (e.g., 'Driving Time').
            arcgis_route_params (Any): Additional parameters to pass directly to the arcgis.network.analysis.find_routes function.

        Returns:
            RouteResult: Route details including stops, routes, and directions.
        """
        if not stops_data or len(stops_data.features) < 2:
            raise ValueError("At least two stops are required to calculate a route.")

        current_time = time_of_day if time_of_day is not None else dt.datetime.now()

        logger.info(
            "Calculating route for %d stops at %s",
            len(stops_data.features),
            time_of_day,
        )

        # Convert FeatureCollection to ArcGIS FeatureSet
        geojson_dict = stops_data.model_dump()
        arcgis_stops_fs = FeatureSet.from_geojson(geojson_dict)

        try:
            params = {
                "stops": arcgis_stops_fs,
                "time_of_day": current_time,
                "time_zone_for_time_of_day": time_zone_for_time_of_day,
                "preserve_terminal_stops": preserve_terminal_stops.value,
                **arcgis_route_params,
            }

            if travel_mode:
                params["travel_mode"] = travel_mode

            result = find_routes(**params)

            return RouteResponse(
                output_stops=FeatureCollection.model_validate_json(result.output_stops.to_geojson),
                output_routes=FeatureCollection.model_validate_json(
                    result.output_routes.to_geojson
                ),
                output_directions=self._transform_arcgis_directions(result.output_directions),
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

        # Convert Pydantic geometry back to a dictionary for the ArcGIS API
        if not (entity.features and isinstance(entity.features[0].geometry, Point)):
            logger.error(
                "Expected a GeoJSON Point geometry for nearby POIs query, but received a different type or empty entity."
            )
            return None

        geometry_dict = entity.features[0].geometry.model_dump()

        geometry = geometry_dict
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

    def _transform_arcgis_directions(self, arcgis_directions: FeatureSet) -> ManeuverList:
        """
        Transforms the verbose ArcGIS directions FeatureSet into a clean ManeuverList
        of RouteManeuver objects.
        """
        if not arcgis_directions:
            return ManeuverList(items=[])

        maneuvers = []
        for step_feature in arcgis_directions.features:
            attributes = step_feature.attributes
            maneuver_data = {
                "instruction": attributes.get("Text", ""),
                "distance": attributes.get("DriveDistance", 0.0),
                "arrive_time": attributes.get("ArriveTime", 0.0),
            }

            maneuvers.append(RouteManeuver(**maneuver_data))

        return ManeuverList(items=maneuvers)
