import os

from segittur_commons.app.infrastructure.destination.external_api import ExternalApi


class DestinationAPI(ExternalApi):
    """
    A class to interact with the destination API of the PID.
    """

    base_url = f"{os.environ['BASE_API_URL_SEGITTUR_PID']}/cgpid-backend/api/destinations/"

    def __init__(self, user_token: str):
        super().__init__(user_token)

    def _get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def get_destination_data(self, endpoint: str, **kwargs):
        response = self.call_external_api(self.base_url + endpoint, headers=self.headers, **kwargs)
        return response.json()
