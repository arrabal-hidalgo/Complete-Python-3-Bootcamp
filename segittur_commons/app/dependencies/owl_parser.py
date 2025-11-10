import os

from segittur_commons.app.services.owl_parser import OWLParser


def get_owl_parser():
    return OWLParser(
        os.getenv("OWL_URL"),
        [
            "Accommodation",
            "TourGuide",
            "TouristIntermediary",
            "TourismResource",
            "LocalBusiness",
            "RestaurantService",
            "PassengerTransport",
            "TouristDestination",
            "TransportInfraestructure",
            "TouristOrRelatedFacility",
            "PublicService",
            "Person",
            "Event",
        ],
    )
