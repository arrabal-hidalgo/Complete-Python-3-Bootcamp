import json
from unittest.mock import MagicMock, call, patch

import pytest
from arcgis.features import FeatureSet
from geojson_pydantic.features import Feature as GeoJsonFeature
from geojson_pydantic.features import FeatureCollection
from geojson_pydantic.geometries import LineString, Point

from segittur_commons.app.entities.route import RouteResponse
from segittur_commons.app.infrastructure.gis.arcgis_service import ArcGISService


@pytest.fixture
def mock_gis_class():
    """Fixture to mock the entire arcgis.gis.GIS class."""
    with patch("segittur_commons.app.infrastructure.gis.arcgis_service.GIS") as mock:
        yield mock


class TestArcGISServiceInitialization:
    def test_initialization_success(self, mock_gis_class):
        """Test successful initialization of ArcGISService."""
        api_key = "test_api_key"
        service = ArcGISService(api_key=api_key)
        mock_gis_class.assert_called_once_with(api_key=api_key)
        assert service.gis is not None

    def test_initialization_no_api_key(self):
        """Test that ValueError is raised if no API key is provided."""
        with pytest.raises(ValueError, match="ARCGIS_API_KEY is not provided."):
            ArcGISService(api_key="")

    def test_initialization_connection_error(self, mock_gis_class):
        """Test that ConnectionError is raised if GIS() fails."""
        mock_gis_class.side_effect = Exception("Connection failed")
        with pytest.raises(ConnectionError, match="Cannot connect to ArcGIS: Connection failed"):
            ArcGISService(api_key="test_api_key")


@pytest.fixture
def arcgis_service(mock_gis_class):
    """Provides an ArcGISService instance with a mocked GIS connection."""
    return ArcGISService(api_key="fake_key")


class TestGeocodeAddresses:
    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.geocode")
    def test_geocode_addresses_success(self, mock_geocode, arcgis_service):
        """Test successful geocoding of multiple addresses."""
        addresses = ["Address 1", "Address 2"]
        mock_fs1 = MagicMock(spec=FeatureSet)
        mock_fs1.to_geojson = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [-74.0, 40.7]},
                        "properties": {"Match_addr": "Address 1"},
                    }
                ],
            }
        )

        mock_fs2 = MagicMock(spec=FeatureSet)
        mock_fs2.to_geojson = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [-75.0, 41.7]},
                        "properties": {"Match_addr": "Address 2"},
                    }
                ],
            }
        )

        mock_geocode.side_effect = [
            mock_fs1,
            mock_fs2,
        ]

        result = arcgis_service.geocode_addresses(addresses)

        assert isinstance(result, FeatureCollection)
        assert len(result.features) == 2
        assert isinstance(result.features[0].geometry, Point)
        assert result.features[0].geometry.coordinates == (-74.0, 40.7)
        assert result.features[0].properties["Match_addr"] == "Address 1"
        mock_geocode.assert_has_calls(
            [
                call(
                    addresses[0],
                    max_locations=1,
                    as_featureset=True,
                    out_sr=None,
                    category=None,
                    source_country=None,
                ),
                call(
                    addresses[1],
                    max_locations=1,
                    as_featureset=True,
                    out_sr=None,
                    category=None,
                    source_country=None,
                ),
            ]
        )

    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.geocode")
    def test_geocode_addresses_no_results_for_one(self, mock_geocode, arcgis_service):
        """Test that the process continues if one address has no matches."""
        addresses = ["Address 1", "Address 2"]
        mock_fs = MagicMock(spec=FeatureSet)
        mock_fs.to_geojson = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [-75.0, 41.7]},
                        "properties": {"Match_addr": "Address 2"},
                    }
                ],
            }
        )
        mock_geocode.side_effect = [
            None,
            mock_fs,
        ]

        result = arcgis_service.geocode_addresses(addresses)

        assert isinstance(result, FeatureCollection)
        assert len(result.features) == 1
        assert result.features[0].properties["Match_addr"] == "Address 2"
        mock_geocode.assert_called()

    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.geocode")
    def test_geocode_addresses_api_error(self, mock_geocode, arcgis_service, caplog):
        """Test that an API error during geocoding is logged and skipped."""
        addresses = ["Address 1", "Address 2"]
        mock_geocode.side_effect = [
            Exception("API limit reached"),
            MagicMock(
                spec=FeatureSet,
                to_geojson=MagicMock(
                    return_value=json.dumps({"type": "FeatureCollection", "features": []})
                ),
            ),
        ]

        result = arcgis_service.geocode_addresses(addresses)

        assert isinstance(result, FeatureCollection)
        assert len(result.features) == 0
        assert "Error geocoding 'Address 1': API limit reached" in caplog.text

    def test_geocode_addresses_empty_input(self, arcgis_service):
        """Test that an empty list of addresses returns an empty FeatureCollection."""
        result = arcgis_service.geocode_addresses([])
        assert result == FeatureCollection(type="FeatureCollection", features=[])


class TestFlattenFeatureSets:
    def test_flatten_featuresets_combines_results(self, arcgis_service):
        """Test that it correctly combines features from multiple FeatureSets."""
        # Use GeoJSON Pydantic models for testing this method
        feature1 = GeoJsonFeature(
            type="Feature", geometry=Point(type="Point", coordinates=(1, 1)), properties={}
        )
        feature2 = GeoJsonFeature(
            type="Feature", geometry=Point(type="Point", coordinates=(2, 2)), properties={}
        )
        feature3 = GeoJsonFeature(
            type="Feature", geometry=Point(type="Point", coordinates=(3, 3)), properties={}
        )

        fc1 = FeatureCollection(type="FeatureCollection", features=[feature1])
        fc2 = FeatureCollection(type="FeatureCollection", features=[feature2, feature3])

        result = arcgis_service._flatten_featuresets([fc1, fc2])

        assert len(result.features) == 3
        assert result.features[0].properties["OBJECTID"] == 1
        assert result.features[1].properties["OBJECTID"] == 2
        assert result.features[2].properties["OBJECTID"] == 3
        assert result.features[0] is feature1

    def test_flatten_featuresets_with_empty_and_none(self, arcgis_service):
        """Test that it handles empty or None FeatureSets gracefully."""
        feature1 = GeoJsonFeature(
            type="Feature", geometry=Point(type="Point", coordinates=(1, 1)), properties={}
        )
        fc1 = FeatureCollection(type="FeatureCollection", features=[feature1])
        fc_empty = FeatureCollection(type="FeatureCollection", features=[])

        result = arcgis_service._flatten_featuresets([fc1, fc_empty, None])

        assert len(result.features) == 1
        assert result.features[0].properties["OBJECTID"] == 1

    def test_flatten_featuresets_empty_input(self, arcgis_service):
        """Test that an empty input list results in an empty FeatureSet."""
        result = arcgis_service._flatten_featuresets([])
        assert len(result.features) == 0


class TestFindOptimalRoute:
    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.find_routes")
    def test_find_optimal_route_success(self, mock_find_routes, arcgis_service):
        """Test successful route finding."""
        # Mock the .to_geojson property of the FeatureSet objects returned by the API
        mock_stops_fs = MagicMock(spec=FeatureSet)
        mock_stops_fs.to_geojson = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {"type": "Point", "coordinates": [-74.0, 40.7]},
                        "properties": {"Name": "Stop 1"},
                    }
                ],
            }
        )

        mock_routes_fs = MagicMock(spec=FeatureSet)
        mock_routes_fs.to_geojson = json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "geometry": {
                            "type": "LineString",
                            "coordinates": [[-74.1, 40.8], [-74.2, 40.9]],
                        },
                        "properties": {"Total_Length": 10.5},
                    }
                ],
            }
        )

        # Create a mock ToolOutput object that find_routes actually returns
        mock_tool_output = MagicMock()
        mock_tool_output.output_stops = mock_stops_fs
        mock_tool_output.output_routes = mock_routes_fs
        # mock_tool_output.output_directions = mock_directions_fs

        mock_find_routes.return_value = mock_tool_output

        # The input stops_data for find_optimal_route should be a GeoJSON FeatureCollection
        stops_data = FeatureCollection(
            type="FeatureCollection",
            features=[
                GeoJsonFeature(
                    type="Feature",
                    geometry=Point(type="Point", coordinates=(-74.0, 40.7)),
                    properties={"Name": "Stop 1"},
                ),
                GeoJsonFeature(
                    type="Feature",
                    geometry=Point(type="Point", coordinates=(-75.0, 41.7)),
                    properties={"Name": "Stop 2"},
                ),
            ],
        )

        result = arcgis_service.find_optimal_route(stops_data)

        assert isinstance(result, RouteResponse)
        assert isinstance(result.output_stops, FeatureCollection)
        assert len(result.output_stops.features) == 1
        assert result.output_stops.features[0].properties["Name"] == "Stop 1"
        assert isinstance(result.output_stops.features[0].geometry, Point)
        assert result.output_stops.features[0].geometry.coordinates == (-74.0, 40.7)

        assert isinstance(result.output_routes, FeatureCollection)
        assert len(result.output_routes.features) == 1
        assert result.output_routes.features[0].properties["Total_Length"] == 10.5
        assert isinstance(result.output_routes.features[0].geometry, LineString)
        assert result.output_routes.features[0].geometry.coordinates == [
            (-74.1, 40.8),
            (-74.2, 40.9),
        ]

        assert result.output_directions is None
        mock_find_routes.assert_called_once()

    def test_find_optimal_route_insufficient_stops(self, arcgis_service):
        """Test that ValueError is raised for less than two stops."""
        stops_data_single = FeatureCollection(
            type="FeatureCollection",
            features=[
                GeoJsonFeature(
                    type="Feature", geometry=Point(type="Point", coordinates=(0, 0)), properties={}
                )
            ],
        )
        stops_data_empty = FeatureCollection(type="FeatureCollection", features=[])

        with pytest.raises(ValueError, match="At least two stops are required"):
            arcgis_service.find_optimal_route(stops_data_single)

        with pytest.raises(ValueError, match="At least two stops are required"):
            arcgis_service.find_optimal_route(stops_data_empty)

    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.find_routes")
    def test_find_optimal_route_api_error(self, mock_find_routes, arcgis_service, caplog):
        """Test that None is returned and error is logged on API failure."""
        mock_find_routes.side_effect = Exception("Routing service unavailable")
        stops_data = FeatureCollection(
            type="FeatureCollection",
            features=[
                GeoJsonFeature(
                    type="Feature", geometry=Point(type="Point", coordinates=(0, 0)), properties={}
                ),
                GeoJsonFeature(
                    type="Feature", geometry=Point(type="Point", coordinates=(1, 1)), properties={}
                ),
            ],
        )

        result = arcgis_service.find_optimal_route(stops_data)

        assert result is None
        assert (
            "Error calculating route or processing result: Routing service unavailable"
            in caplog.text
        )


class TestGetNearbyPois:
    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.FeatureLayer")
    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.intersects")
    def test_get_nearby_pois_success(self, mock_intersects, mock_feature_layer_cls, arcgis_service):
        """Test successful query of nearby POIs."""
        # Mock de la geometría y referencia espacial
        mock_point_geometry = Point(type="Point", coordinates=(-74.0, 40.7))
        mock_geojson_feature = GeoJsonFeature(
            type="Feature",
            geometry=mock_point_geometry,
            properties={},
        )
        mock_entity = FeatureCollection(type="FeatureCollection", features=[mock_geojson_feature])

        # Mock de la instancia de FeatureLayer y su método query
        mock_feature_layer_instance = MagicMock()
        mock_feature_layer_cls.return_value = mock_feature_layer_instance
        mock_feature_layer_instance.query.return_value = "Query Result"

        # Mock del filtro de geometría
        mock_intersects.return_value = "geometry_filter"

        url = "http://fake-layer.com"
        result = arcgis_service.get_nearby_pois(
            entity=mock_entity,
            feature_layer_url=url,
            where_clause="type='restaurant'",
            distance=50,
        )

        assert result == "Query Result"
        mock_feature_layer_cls.assert_called_once_with(url)
        mock_intersects.assert_called_once_with(geometry=mock_point_geometry.model_dump())
        mock_feature_layer_instance.query.assert_called_once_with(
            where="type='restaurant'",
            distance=50,
            units="esriSRUnit_Meter",
            out_sr=4326,
            geometry_filter="geometry_filter",
            result_record_count=200,
        )

    def test_get_nearby_pois_no_feature_layer_url(self, arcgis_service):
        """Test that ValueError is raised if feature_layer_url is missing."""
        mock_entity = FeatureCollection(
            type="FeatureCollection", features=[MagicMock(GeoJsonFeature)]
        )
        with pytest.raises(ValueError, match="No feature_layer_url provided"):
            arcgis_service.get_nearby_pois(entity=mock_entity)

    def test_get_nearby_pois_invalid_route_result(self, arcgis_service, caplog):
        """Test that it returns None for an invalid or empty route result."""
        url = "http://fake-layer.com"

        # Caso 1: entity es None
        result_none = arcgis_service.get_nearby_pois(entity=None, feature_layer_url=url)
        assert result_none is None
        assert "Cannot get nearby POIs from an empty or invalid entity" in caplog.text

        # Caso 2: entity no tiene features
        result_empty = arcgis_service.get_nearby_pois(
            entity=FeatureCollection(type="FeatureCollection", features=[]), feature_layer_url=url
        )
        assert result_empty is None
        assert "Cannot get nearby POIs from an empty or invalid entity" in caplog.text

    def test_get_nearby_pois_non_point_geometry(self, arcgis_service, caplog):
        """Test that it returns None if the entity's geometry is not a PointGeometry."""
        mock_linestring_geom = LineString(type="LineString", coordinates=[(1, 1), (2, 2)])
        mock_entity = FeatureCollection(
            type="FeatureCollection",
            features=[GeoJsonFeature(type="Feature", geometry=mock_linestring_geom, properties={})],
        )
        result = arcgis_service.get_nearby_pois(
            entity=mock_entity, feature_layer_url="http://fake.com"
        )
        assert result is None
        assert "Expected a GeoJSON Point geometry for nearby POIs query" in caplog.text
