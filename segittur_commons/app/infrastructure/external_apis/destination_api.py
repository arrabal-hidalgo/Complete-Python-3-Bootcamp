import os
from typing import Any

from segittur_commons.app.entities.destination import (
    DestinationInfo,
    DestinationLightlistRequest,
    DestinationLightlistWrapper,
    DestinationType,
)
from segittur_commons.app.infrastructure.external_apis.external_api import ExternalApi


class DestinationAPI(ExternalApi):
    """
    A class to interact with the destination API of the PID.
    """

    base_url = f"{os.environ['BASE_API_URL_SEGITTUR_PID']}/cgpid-backend/api/destinations/"

    def __init__(self, user_token: str):
        super().__init__(user_token)

    def _get_headers(self) -> dict:
        return {"Authorization": f"Bearer {self.api_key}", "Content-Type": "application/json"}

    def get_destination_data(self, endpoint: str, **kwargs) -> Any:
        response = self.call_external_api(self.base_url + endpoint, headers=self.headers, **kwargs)
        return response.json()

    def _get_detail_info(self, destination_id: str) -> Any:
        return self.get_destination_data(f"{destination_id}/detail", method="GET")

    def get_destination_info(self, destination_id: str) -> DestinationInfo:
        destination_details = self._get_detail_info(destination_id)
        return DestinationInfo(
            dest_type=DestinationType(destination_details["type"]),
            ineCode=destination_details["ineCode"],
        )

    def _get_light_list(
        self,
        criteria: DestinationLightlistRequest,
        lang: str | None = None,
        page: int | None = None,
        size: int | None = None,
    ) -> Any:
        params = {"lang": lang, "page": page, "size": size}
        cleaned_params = {k: v for k, v in params.items() if v is not None}
        return self.get_destination_data(
            "lightlist",
            method="POST",
            data=criteria.model_dump_json(by_alias=True),
            params=cleaned_params,
        )

    def get_destinations_lightlist(self, **kwargs_endpoint) -> DestinationLightlistWrapper:
        light_list = self._get_light_list(**kwargs_endpoint)
        return DestinationLightlistWrapper(**light_list)
