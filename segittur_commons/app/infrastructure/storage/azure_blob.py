import os
from datetime import datetime, timedelta

from azure.identity import DefaultAzureCredential
from azure.storage.blob import (
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
    BlobSasPermissions,
)

from .blob import Blob


class AzureBlob(Blob):

    class ResultBlob:

        def __init__(self, file_name):
            self.file_name = file_name

        @property
        def object_name(self):
            return self.file_name

    LINK_EXPIRATION = os.getenv("AVC_STORAGE_LINK_EXPIRATION", 60)

    AZURE_BLOB_STORAGE = "azure-blob"

    def __init__(self, server_url, access_key, secret_key, region, bucket, secure=True):
        self.account_url = server_url
        self.account_name = access_key
        self.account_key = secret_key

        if access_key and secret_key:
            self.azure_credential = {"account_name": access_key, "account_key": secret_key}
        else:
            self.azure_credential = DefaultAzureCredential()

        self.blob_service_client = BlobServiceClient(server_url, credential=self.azure_credential)

        self.storage = None

        self.region = region
        self.bucket = bucket

    def create_bucket(self, bucket, region=None):
        container_client = self.blob_service_client.get_container_client(bucket)
        if not container_client.exists():
            container_client.create_container()

        self.storage = self.storage or container_client

    def upload_data(self, file_name, data, content_type, metadata: dict = {}, bucket=None):
        blob_client = (
            self.blob_service_client.get_container_client(bucket).get_blob_client(file_name)
            if bucket
            else self.storage.get_blob_client(file_name)
        )
        content_settings = ContentSettings(content_type=content_type)
        blob_client.upload_blob(data=data, metadata=metadata, content_settings=content_settings)
        return self.ResultBlob(file_name)

    def download_data(self, file_name, bucket=None):
        blob_client = (
            self.blob_service_client.create_container(bucket).get_blob_client(file_name)
            if bucket
            else self.storage.get_blob_client(file_name)
        )
        result = blob_client.download_blob().chunks()
        return result

    def file_link(self, file_name, bucket=None):
        bckt = bucket if bucket else self.bucket

        expiry_time = datetime.now() + timedelta(minutes=self.LINK_EXPIRATION)

        sas_token = generate_blob_sas(
            account_name=self.account_name,
            container_name=bckt,
            blob_name=file_name,
            account_key=self.account_key,
            permission=BlobSasPermissions(read=True),
            expiry=expiry_time,
        )

        return f"https://{self.account_name}.blob.core.windows.net/{bckt}/{file_name}?{sas_token}"

    def get_config(self):
        return {
            "url": self.account_url,
            "access_key": self.account_name,
            "secret_key": self.account_key,
            "region": self.region,
            "secure": self.secure,
        }

    def get_provider(self):
        return self.AZURE_BLOB_STORAGE
