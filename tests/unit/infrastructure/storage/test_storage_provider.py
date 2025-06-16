import os
import unittest
from unittest.mock import MagicMock, patch

from segittur_commons.app.infrastructure.storage.azure_blob import AzureBlob
from segittur_commons.app.infrastructure.storage.blob import Blob
from segittur_commons.app.infrastructure.storage.minio_blob import MinioBlob
from segittur_commons.app.infrastructure.storage.storage_provider import StorageProvider


class TestStorageProvider(unittest.TestCase):

    @patch.dict(
        os.environ,
        {
            "AVC_STORAGE_URL": "http://minio:9000",
            "AVC_STORAGE_ACCESS_KEY": "minio_access_key",
            "AVC_STORAGE_SECRET_KEY": "minio_secret_key",
            "AVC_STORAGE_REGION": "us-east-1",
            "AVC_STORAGE_SECURE": "true",
        },
    )
    @patch("segittur_commons.app.infrastructure.storage.storage_provider.MinioBlob")
    def test_create_storage_minio_explicit_provider(self, MockMinioBlob):
        mock_minio_instance = MagicMock(spec=MinioBlob)
        MockMinioBlob.return_value = mock_minio_instance
        bucket_name = "test-bucket"

        storage = StorageProvider.create_storage(
            bucket_name, provider=StorageProvider.SupportedStorages.minio
        )

        MockMinioBlob.assert_called_once_with(
            server_url="http://minio:9000",
            access_key="minio_access_key",
            secret_key="minio_secret_key",
            region="us-east-1",
            secure=True,
            bucket=bucket_name,
        )
        mock_minio_instance.create_bucket.assert_called_once_with(bucket_name)
        self.assertIsInstance(storage, Blob)
        self.assertEqual(storage, mock_minio_instance)

    @patch.dict(
        os.environ,
        {
            "AVC_STORAGE_URL": "http://azure.blob.core.windows.net",
            "AVC_STORAGE_ACCESS_KEY": "azure_account_name",
            "AVC_STORAGE_SECRET_KEY": "azure_account_key",
            "AVC_STORAGE_REGION": "westeurope",
            "AVC_STORAGE_SECURE": "false",  # Test with false
        },
    )
    @patch("segittur_commons.app.infrastructure.storage.storage_provider.AzureBlob")
    def test_create_storage_azure_explicit_provider(self, MockAzureBlob):
        mock_azure_instance = MagicMock(spec=AzureBlob)
        MockAzureBlob.return_value = mock_azure_instance
        bucket_name = "test-container"

        storage = StorageProvider.create_storage(
            bucket_name, provider=StorageProvider.SupportedStorages.abs
        )

        MockAzureBlob.assert_called_once_with(
            server_url="http://azure.blob.core.windows.net",
            access_key="azure_account_name",
            secret_key="azure_account_key",
            region="westeurope",
            secure=False,
            bucket=bucket_name,
        )
        mock_azure_instance.create_bucket.assert_called_once_with(bucket_name)
        self.assertIsInstance(storage, Blob)
        self.assertEqual(storage, mock_azure_instance)

    @patch.dict(
        os.environ,
        {
            "AVC_STORAGE_URL": "http://default-minio:9000",
            "AVC_STORAGE_ACCESS_KEY": "default_access",
            "AVC_STORAGE_SECRET_KEY": "default_secret",
            "AVC_STORAGE_REGION": "default-region",
            "AVC_STORAGE_SECURE": "1",  # Test with "1"
            "AVC_STORAGE_PROVIDER": MinioBlob.MINIO,  # Explicitly set to minio via env
        },
    )
    @patch("segittur_commons.app.infrastructure.storage.storage_provider.MinioBlob")
    def test_create_storage_default_provider_minio_from_env(self, MockMinioBlob):
        mock_minio_instance = MagicMock(spec=MinioBlob)
        MockMinioBlob.return_value = mock_minio_instance
        bucket_name = "default-bucket"

        storage = StorageProvider.create_storage(bucket_name, provider=None)

        MockMinioBlob.assert_called_once_with(
            server_url="http://default-minio:9000",
            access_key="default_access",
            secret_key="default_secret",
            region="default-region",
            secure=True,
            bucket=bucket_name,
        )
        mock_minio_instance.create_bucket.assert_called_once_with(bucket_name)
        self.assertEqual(storage, mock_minio_instance)

    @patch.dict(
        os.environ,
        {
            "AVC_STORAGE_URL": "http://another-minio:9000",
            "AVC_STORAGE_ACCESS_KEY": "another_access",
            "AVC_STORAGE_SECRET_KEY": "another_secret",
            "AVC_STORAGE_REGION": "another-region",
            "AVC_STORAGE_SECURE": "True",  # Test with "True"
        },
        clear=True,
    )  # Clear other env vars like AVC_STORAGE_PROVIDER
    @patch("segittur_commons.app.infrastructure.storage.storage_provider.MinioBlob")
    def test_create_storage_default_provider_minio_no_env_provider_set(self, MockMinioBlob):
        mock_minio_instance = MagicMock(spec=MinioBlob)
        MockMinioBlob.return_value = mock_minio_instance
        bucket_name = "another-bucket"

        # Ensure AVC_STORAGE_PROVIDER is not set for this test
        if "AVC_STORAGE_PROVIDER" in os.environ:
            del os.environ["AVC_STORAGE_PROVIDER"]

        storage = StorageProvider.create_storage(bucket_name, provider=None)

        MockMinioBlob.assert_called_once_with(
            server_url="http://another-minio:9000",
            access_key="another_access",
            secret_key="another_secret",
            region="another-region",
            secure=True,
            bucket=bucket_name,
        )
        mock_minio_instance.create_bucket.assert_called_once_with(bucket_name)
        self.assertEqual(storage, mock_minio_instance)

    @patch.dict(
        os.environ,
        {
            "AVC_STORAGE_URL": "http://env-azure.blob.core.windows.net",
            "AVC_STORAGE_ACCESS_KEY": "env_azure_account",
            "AVC_STORAGE_SECRET_KEY": "env_azure_key",
            "AVC_STORAGE_REGION": "env_westeurope",
            "AVC_STORAGE_SECURE": "true",
            "AVC_STORAGE_PROVIDER": AzureBlob.AZURE_BLOB_STORAGE,  # Set to Azure via env
        },
    )
    @patch("segittur_commons.app.infrastructure.storage.storage_provider.AzureBlob")
    def test_create_storage_provider_azure_from_env(self, MockAzureBlob):
        mock_azure_instance = MagicMock(spec=AzureBlob)
        MockAzureBlob.return_value = mock_azure_instance
        bucket_name = "env-azure-bucket"

        storage = StorageProvider.create_storage(bucket_name, provider=None)

        MockAzureBlob.assert_called_once_with(
            server_url="http://env-azure.blob.core.windows.net",
            access_key="env_azure_account",
            secret_key="env_azure_key",
            region="env_westeurope",
            secure=True,
            bucket=bucket_name,
        )
        mock_azure_instance.create_bucket.assert_called_once_with(bucket_name)
        self.assertEqual(storage, mock_azure_instance)

    def test_create_storage_unsupported_provider(self):
        bucket_name = "any-bucket"
        with self.assertRaisesRegex(Exception, "Cloud Storage no supported"):
            StorageProvider.create_storage(bucket_name, provider="unsupported_cloud")

    def test_supported_storages_enum(self):
        self.assertEqual(StorageProvider.SupportedStorages.minio, "s3-minio")
        self.assertEqual(StorageProvider.SupportedStorages.abs, "azure-blob")
        # Check that it's a string enum
        self.assertIsInstance(StorageProvider.SupportedStorages.minio.value, str)
        self.assertIsInstance(StorageProvider.SupportedStorages.abs.value, str)


if __name__ == "__main__":
    unittest.main()
