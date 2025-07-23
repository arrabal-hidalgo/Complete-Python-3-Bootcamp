from abc import ABC, abstractmethod

import requests


class ExternalApi(ABC):
    """
    Base class for external APIs.
    This class should be inherited by any specific external API implementation.
    """

    base_url: str = ""

    def __init__(self, api_key):
        self.api_key = api_key
        self.headers = self._get_headers()

    @abstractmethod
    def _get_headers(self) -> dict:
        """
        Returns the headers required for making requests to the external service.
        This method should be implemented by subclasses to provide the actual headers.
        """
        raise NotImplementedError

    def call_external_api(
        self, url_template: str, method: str = "GET", kwargs_url={}, **kwargs_request
    ):
        url = url_template.format(**kwargs_url)
        response = requests.request(method, url, **kwargs_request)
        response.raise_for_status()
        return response

    def check_unique_result(self, result):
        n_results = len(result)
        if n_results > 1:
            raise Exception("There are more than one result.")
        elif n_results == 0:
            raise Exception("There isn't any result.")
