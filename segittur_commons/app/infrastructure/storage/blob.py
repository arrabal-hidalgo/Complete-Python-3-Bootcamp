from abc import ABC, abstractmethod


class Blob(ABC):

    @abstractmethod
    def create_bucket(self, bucket, region=None):
        pass

    @abstractmethod
    def upload_data(self, file_name, data, content_type, metadata: dict = {}, bucket=None):
        pass

    @abstractmethod
    def download_data(self, file_name, bucket=None):
        pass

    @abstractmethod
    def file_link(self, file_name, bucket=None):
        pass

    @abstractmethod
    def delete_data(self, file_name, bucket=None):
        pass

    @abstractmethod
    def get_provider(self) -> str:
        pass

    @abstractmethod
    def get_config(self) -> dict:
        pass
