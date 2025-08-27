import os
from datetime import timedelta

from minio import Minio

from segittur_commons.app.infrastructure.storage.blob import Blob


class MinioBlob(Blob):

    LINK_EXPIRATION = os.getenv("AVC_STORAGE_LINK_EXPIRATION", 60)

    MINIO = "s3-minio"

    def __init__(self, server_url, access_key, secret_key, region, bucket, secure=True):
        self.storage = Minio(
            server_url, access_key=access_key, secret_key=secret_key, secure=secure, region=region
        )
        self.server_url = server_url
        self.access_key = access_key
        self.secret_key = secret_key
        self.region = region
        self.bucket = bucket
        self.secure = secure

    def create_bucket(self, bucket, region=None):
        if not self.storage.bucket_exists(bucket):
            reg = region if region else self.region
            self.storage.make_bucket(bucket, reg)

    def upload_data(self, file_name, data, content_type, metadata: dict = {}, bucket=None):
        bckt = bucket if bucket else self.bucket
        result = self.storage.put_object(
            bckt,
            file_name,
            data,
            length=-1,
            part_size=10 * 1024 * 1024,
            content_type=content_type,
            metadata=metadata,
        )
        return result

    def download_data(self, file_name, bucket=None):
        bckt = bucket if bucket else self.bucket
        result = self.storage.get_object(bckt, file_name)
        return result

    def file_link(self, file_name, bucket=None):
        bckt = bucket if bucket else self.bucket
        return self.storage.get_presigned_url(
            "GET",
            bckt,
            file_name,
            expires=timedelta(seconds=self.LINK_EXPIRATION),
        )

    def get_config(self):
        return {
            "url": self.server_url,
            "access_key": self.access_key,
            "secret_key": self.secret_key,
            "region": self.region,
            "secure": self.secure,
        }

    def get_provider(self):
        return self.MINIO
