import os
from enum import Enum

from segittur_commons.app.infrastructure.storage.azure_blob import AzureBlob
from segittur_commons.app.infrastructure.storage.blob import Blob
from segittur_commons.app.infrastructure.storage.minio_blob import MinioBlob


class StorageProvider:

    class SupportedStorages(str, Enum):
        minio = MinioBlob.MINIO
        abs = AzureBlob.AZURE_BLOB_STORAGE

    @classmethod
    def create_storage(cls, bucket, provider: SupportedStorages | None = None) -> Blob:
        if provider is None:
            provider = os.getenv("AVC_STORAGE_PROVIDER", cls.SupportedStorages.minio)

        if provider == cls.SupportedStorages.minio:
            storage = MinioBlob(
                server_url=os.getenv("AVC_STORAGE_URL"),
                access_key=os.getenv("AVC_STORAGE_ACCESS_KEY"),
                secret_key=os.getenv("AVC_STORAGE_SECRET_KEY"),
                region=os.getenv("AVC_STORAGE_REGION"),
                secure=os.getenv("AVC_STORAGE_SECURE", "true") in ["True", "true", "1"],
                bucket=bucket,
            )
            storage.create_bucket(bucket)
        elif provider == cls.SupportedStorages.abs:
            storage = AzureBlob(
                server_url=os.getenv("AVC_STORAGE_URL"),
                access_key=os.getenv("AVC_STORAGE_ACCESS_KEY"),
                secret_key=os.getenv("AVC_STORAGE_SECRET_KEY"),
                region=os.getenv("AVC_STORAGE_REGION"),
                secure=os.getenv("AVC_STORAGE_SECURE", "true") in ["True", "true", "1"],
                bucket=bucket,
            )
            storage.create_bucket(bucket)
        else:
            raise Exception("Cloud Storage no supported")
        return storage
