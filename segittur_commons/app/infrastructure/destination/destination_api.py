import os

from segittur_commons.app.infrastructure.destination.external_api import ExternalApi


class DestinationAPI(ExternalApi):
    """
    A class to interact with the destination API of the PID.
    """

    base_url = os.environ["DESTINATION_API_BASE_URL"]

    def __init__(self):
        self.user = os.environ["DESTINATION_API_USER_NAME"]
        self.password = os.environ["DESTINATION_API_PASSWORD"]
        super().__init__()

    def _get_api_key(self) -> str:
        token_data = {
            "grant_type": "password",
            "username": self.user,
            "password": self.password,
            "client_id": os.environ["DESTINATION_API_CLIENT_ID"],
            "scope": "openid",
        }

        response = self.call_external_api(
            f"{self.base_url}/auth/realms/onesaitplatform/protocol/openid-connect/token",
            "POST",
            headers={},
            data=token_data,
        )
        apy_key: str = response.json()["access_token"]
        return apy_key

    def _get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def get_destination_data(self, endpoint: str, **kwargs):
        response = self.call_external_api(self.base_url + endpoint, headers=self.headers, **kwargs)
        return response.json()
