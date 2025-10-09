from unittest.mock import MagicMock, Mock, call, patch

import pytest
from arcgis.features import Feature, FeatureSet

from segittur_commons.app.entities.route import RouteResult
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
        mock_geocode.side_effect = [
            FeatureSet(features=[Feature()]),
            FeatureSet(features=[Feature()]),
        ]

        result = arcgis_service.geocode_addresses(addresses)

        assert len(result) == 2
        assert isinstance(result[0], FeatureSet)
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
        mock_geocode.side_effect = [
            None,
            FeatureSet([Feature()]),
        ]

        result = arcgis_service.geocode_addresses(addresses)

        assert len(result) == 1
        mock_geocode.assert_called()

    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.geocode")
    def test_geocode_addresses_api_error(self, mock_geocode, arcgis_service, caplog):
        """Test that an API error during geocoding is logged and skipped."""
        addresses = ["Address 1", "Address 2"]
        mock_geocode.side_effect = [
            Exception("API limit reached"),
            FeatureSet([MagicMock(Feature())]),
        ]

        result = arcgis_service.geocode_addresses(addresses)

        assert len(result) == 1
        assert "Error in geocode for 'Address 1': API limit reached" in caplog.text

    def test_geocode_addresses_empty_input(self, arcgis_service):
        """Test that an empty list of addresses returns an empty list."""
        result = arcgis_service.geocode_addresses([])
        assert result == []


class TestFlattenFeatureSets:
    def test_flatten_featuresets_combines_results(self, arcgis_service):
        """Test that it correctly combines features from multiple FeatureSets."""
        mock_feature1 = MagicMock(Feature())
        mock_feature1.attributes = {}
        mock_feature2 = MagicMock(Feature())
        mock_feature2.attributes = {}
        mock_feature3 = MagicMock(Feature())
        mock_feature3.attributes = {}

        fs1 = FeatureSet([mock_feature1])
        fs2 = FeatureSet([mock_feature2, mock_feature3])

        result = arcgis_service.flatten_featuresets([fs1, fs2])

        assert len(result.features) == 3
        assert result.features[0].attributes["OBJECTID"] == 1
        assert result.features[1].attributes["OBJECTID"] == 2
        assert result.features[2].attributes["OBJECTID"] == 3

    def test_flatten_featuresets_with_empty_and_none(self, arcgis_service):
        """Test that it handles empty or None FeatureSets gracefully."""
        mock_feature = MagicMock(Feature())
        mock_feature.attributes = {}
        fs1 = FeatureSet([mock_feature])
        fs_empty = FeatureSet([])

        result = arcgis_service.flatten_featuresets([fs1, fs_empty, None])

        assert len(result.features) == 1
        assert result.features[0].attributes["OBJECTID"] == 1

    def test_flatten_featuresets_empty_input(self, arcgis_service):
        """Test that an empty input list results in an empty FeatureSet."""
        result = arcgis_service.flatten_featuresets([])
        assert len(result.features) == 0


class TestFindOptimalRoute:
    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.find_routes")
    def test_find_optimal_route_success(self, mock_find_routes, arcgis_service):
        """Test successful route finding."""
        # Simular el resultado de la API como un diccionario, que es lo que Pydantic espera.
        mock_api_result = {
            "output_stops": MagicMock(),
            "output_routes": MagicMock(),
            "output_directions": MagicMock(),
        }
        mock_find_routes.return_value = mock_api_result

        stops_data = FeatureSet([MagicMock(Feature()), MagicMock(Feature())])
        result = arcgis_service.find_optimal_route(stops_data)

        assert isinstance(result, RouteResult)
        assert result.output_stops == mock_api_result["output_stops"]
        assert result.output_routes == mock_api_result["output_routes"]
        assert result.output_directions == mock_api_result["output_directions"]
        mock_find_routes.assert_called_once()

    def test_find_optimal_route_insufficient_stops(self, arcgis_service):
        """Test that ValueError is raised for less than two stops."""
        stops_data_single = FeatureSet([Feature()])
        stops_data_empty = FeatureSet([])

        with pytest.raises(ValueError, match="At least two stops are required"):
            arcgis_service.find_optimal_route(stops_data_single)

        with pytest.raises(ValueError, match="At least two stops are required"):
            arcgis_service.find_optimal_route(stops_data_empty)

    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.find_routes")
    def test_find_optimal_route_api_error(self, mock_find_routes, arcgis_service, caplog):
        """Test that None is returned and error is logged on API failure."""
        mock_find_routes.side_effect = Exception("Routing service unavailable")
        stops_data = FeatureSet([Feature(), Feature()])

        result = arcgis_service.find_optimal_route(stops_data)

        assert result is None
        assert "Error calculating route: Routing service unavailable" in caplog.text


class TestGetNearbyPois:
    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.FeatureLayer")
    @patch("segittur_commons.app.infrastructure.gis.arcgis_service.intersects")
    def test_get_nearby_pois_success(self, mock_intersects, mock_feature_layer_cls, arcgis_service):
        """Test successful query of nearby POIs."""
        # Mock de la geometría y referencia espacial
        mock_geometry = {"spatialReference": {"wkid": 4326}}

        # Mock del resultado de la ruta
        mock_route_result = MagicMock(spec=RouteResult)
        mock_route_result.features = [MagicMock()]
        mock_route_result.features[0].geometry = mock_geometry

        # Mock de la instancia de FeatureLayer y su método query
        mock_feature_layer_instance = MagicMock()
        mock_feature_layer_cls.return_value = mock_feature_layer_instance
        mock_feature_layer_instance.query.return_value = "Query Result"

        # Mock del filtro de geometría
        mock_intersects.return_value = "geometry_filter"

        url = "http://fake-layer.com"
        result = arcgis_service.get_nearby_pois(
            entity=mock_route_result,
            feature_layer_url=url,
            where_clause="type='restaurant'",
            distance=50,
        )

        assert result == "Query Result"
        mock_feature_layer_cls.assert_called_once_with(url)
        mock_intersects.assert_called_once_with(geometry=mock_geometry, sr={"wkid": 4326})
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
        with pytest.raises(ValueError, match="No feature_layer_url provided"):
            arcgis_service.get_nearby_pois(entity=MagicMock())

    def test_get_nearby_pois_invalid_route_result(self, arcgis_service, caplog):
        """Test that it returns None for an invalid or empty route result."""
        url = "http://fake-layer.com"

        # Caso 1: entity es None
        result_none = arcgis_service.get_nearby_pois(entity=None, feature_layer_url=url)
        assert result_none is None
        assert "Cannot get nearby POIs from an empty or invalid entity" in caplog.text

        # Caso 2: entity no tiene features
        result_empty = arcgis_service.get_nearby_pois(entity=FeatureSet([]), feature_layer_url=url)
        assert result_empty is None
