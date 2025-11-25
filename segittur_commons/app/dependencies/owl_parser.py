import os

from segittur_commons.app.services.owl_parser import OWLParser


def get_owl_parser():
    return OWLParser(
        os.getenv("OWL_URL"),
        [
            "AccommodationEstablishment",
            "TourGuide",
            "TouristIntermediary",
            "TourismResource",
            "TourismOrganisation"
            "LocalBusiness",
            "FoodEstablishment",
            "PassengerTransportCompany",
            "TouristDestination",
            "HistoricalOrCulturalResource",
            "TransportInfraestructure",
            "TourismOrRelatedFacility",
            "SportFacility",
            "PublicService",
            "Person",
            "Event",
        ],
    )
