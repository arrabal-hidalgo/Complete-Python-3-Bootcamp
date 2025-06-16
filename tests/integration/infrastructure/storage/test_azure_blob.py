import os
import time  # For link expiration testing
import unittest
import uuid
from datetime import datetime, timedelta, timezone

from azure.core.exceptions import ResourceExistsError, ResourceNotFoundError
from azure.storage.blob import BlobSasPermissions, BlobServiceClient, ContentSettings

# Assuming the AzureBlob class is in this path
# Adjust the import path if your project structure is different
from segittur_commons.app.infrastructure.storage.azure_blob import AzureBlob

# Environment variables for Azure configuration
AZURE_ACCOUNT_URL = os.getenv("AVC_STORAGE_URL")
AZURE_ACCOUNT_NAME = os.getenv("AVC_STORAGE_ACCESS_KEY")
AZURE_ACCOUNT_KEY = os.getenv("AVC_STORAGE_SECRET_KEY")
AZURE_REGION = os.getenv("TEST_AZURE_REGION")

# Skip tests if essential Azure configuration is missing
SKIP_AZURE_TESTS = not (AZURE_ACCOUNT_URL and AZURE_ACCOUNT_NAME and AZURE_ACCOUNT_KEY)
SKIP_REASON = "Azure Blob Storage environment variables (TEST_AZURE_ACCOUNT_URL, TEST_AZURE_ACCOUNT_NAME, TEST_AZURE_ACCOUNT_KEY) not set."


@unittest.skipIf(SKIP_AZURE_TESTS, SKIP_REASON)
class TestAzureBlobIntegration(unittest.TestCase):
    azure_blob_instance: AzureBlob = None
    raw_blob_service_client: BlobServiceClient = None
    test_buckets = []  # Keep track of buckets created by tests

    @classmethod
    def setUpClass(cls):
        cls.raw_blob_service_client = BlobServiceClient(
            account_url=AZURE_ACCOUNT_URL,
            credential={"account_name": AZURE_ACCOUNT_NAME, "account_key": AZURE_ACCOUNT_KEY},
        )

    @classmethod
    def tearDownClass(cls):
        for bucket_name in cls.test_buckets:
            try:
                container_client = cls.raw_blob_service_client.get_container_client(bucket_name)
                if container_client.exists():
                    # Delete all blobs in the container first
                    blob_list = container_client.list_blobs()
                    for blob in blob_list:
                        container_client.delete_blob(blob.name)
                    container_client.delete_container()
                    print(f"Cleaned up test bucket: {bucket_name}")
            except Exception as e:
                print(f"Warning: Could not delete container {bucket_name} during cleanup: {e}")

    def _generate_unique_bucket_name(self):
        name = f"test-bucket-int-{uuid.uuid4().hex[:16]}"
        self.test_buckets.append(name)  # Add to list for cleanup
        return name

    def setUp(self):
        self.default_bucket_name = self._generate_unique_bucket_name()
        self.azure_blob_instance = AzureBlob(
            server_url=AZURE_ACCOUNT_URL,
            access_key=AZURE_ACCOUNT_NAME,
            secret_key=AZURE_ACCOUNT_KEY,
            region=AZURE_REGION,
            bucket=self.default_bucket_name,
            secure=True,  # The 'secure' flag's effect is mainly on URL scheme for S3 types
        )
        # Create the default bucket for the instance
        self.azure_blob_instance.create_bucket(self.default_bucket_name)

    def tearDown(self):
        # Individual test cleanup can be added here if needed,
        # but tearDownClass handles bucket deletion.
        pass

    def test_create_bucket(self):
        new_bucket_name = self._generate_unique_bucket_name()
        self.azure_blob_instance.create_bucket(new_bucket_name)
        container_client = self.raw_blob_service_client.get_container_client(new_bucket_name)
        self.assertTrue(container_client.exists(), f"Bucket {new_bucket_name} should exist.")

        # Test idempotency: creating an existing bucket should not fail
        try:
            self.azure_blob_instance.create_bucket(new_bucket_name)
        except ResourceExistsError:
            self.fail(
                f"create_bucket raised ResourceExistsError for existing bucket {new_bucket_name}"
            )

    def test_upload_and_download_data_default_bucket(self):
        file_name = f"test_upload_{uuid.uuid4().hex[:8]}.txt"
        data_content = b"Hello Azure Blob Storage from integration test!"
        content_type = "text/plain"
        metadata = {"source": "integration_test", "version": "1.0"}

        # Upload
        result_blob = self.azure_blob_instance.upload_data(
            file_name, data_content, content_type, metadata=metadata
        )
        self.assertEqual(result_blob.object_name, file_name)

        # Verify metadata and content type using raw client
        blob_client = self.raw_blob_service_client.get_blob_client(
            self.default_bucket_name, file_name
        )
        properties = blob_client.get_blob_properties()
        self.assertEqual(properties.content_settings.content_type, content_type)
        # Azure stores metadata keys in lowercase
        self.assertEqual(properties.metadata.get("source"), metadata["source"])
        self.assertEqual(properties.metadata.get("version"), metadata["version"])

        # Download
        downloaded_data_chunks = self.azure_blob_instance.download_data(file_name)
        downloaded_data = b"".join(downloaded_data_chunks)
        self.assertEqual(downloaded_data, data_content)

    def test_upload_and_download_data_specific_bucket(self):
        specific_bucket_name = self._generate_unique_bucket_name()
        self.azure_blob_instance.create_bucket(specific_bucket_name)  # Ensure bucket exists

        file_name = f"test_upload_specific_{uuid.uuid4().hex[:8]}.txt"
        data_content = b"Data for specific bucket!"
        content_type = "application/octet-stream"

        # Upload to specific bucket
        result_blob = self.azure_blob_instance.upload_data(
            file_name, data_content, content_type, bucket=specific_bucket_name
        )
        self.assertEqual(result_blob.object_name, file_name)

        # Download from specific bucket
        # Note: The original AzureBlob.download_data uses `create_container` when a bucket is specified.
        # This will raise ResourceExistsError if the container already exists.
        # A more robust implementation would use `get_container_client`.
        # This test will expose that behavior.
        try:
            downloaded_data_chunks = self.azure_blob_instance.download_data(
                file_name, bucket=specific_bucket_name
            )
            downloaded_data = b"".join(downloaded_data_chunks)
            self.assertEqual(downloaded_data, data_content)
        except ResourceExistsError:
            self.fail(
                "download_data with specific bucket failed with ResourceExistsError. "
                "This is likely due to using 'create_container' instead of 'get_container_client' "
                "in the AzureBlob class for specific bucket downloads."
            )
        except Exception as e:
            self.fail(f"download_data with specific bucket failed unexpectedly: {e}")

    def test_file_link(self):
        file_name = f"test_link_{uuid.uuid4().hex[:8]}.txt"
        self.azure_blob_instance.upload_data(file_name, b"link_test", "text/plain")

        link = self.azure_blob_instance.file_link(file_name)
        self.assertTrue(
            link.startswith(
                f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{self.default_bucket_name}/{file_name}"
            )
        )
        self.assertIn("sig=", link, "SAS token signature missing in link")
        self.assertIn("se=", link, "SAS token expiry missing in link")
        self.assertIn("sp=r", link, "SAS token permission should be read (sp=r)")

        # Test with a different bucket
        other_bucket_name = self._generate_unique_bucket_name()
        self.azure_blob_instance.create_bucket(other_bucket_name)
        other_file_name = f"other_link_{uuid.uuid4().hex[:8]}.txt"
        # Need to upload to this other bucket first
        blob_client_other = self.raw_blob_service_client.get_blob_client(
            other_bucket_name, other_file_name
        )
        blob_client_other.upload_blob(b"other_link_data", overwrite=True)

        link_other_bucket = self.azure_blob_instance.file_link(
            other_file_name, bucket=other_bucket_name
        )
        self.assertTrue(
            link_other_bucket.startswith(
                f"https://{AZURE_ACCOUNT_NAME}.blob.core.windows.net/{other_bucket_name}/{other_file_name}"
            )
        )
        self.assertIn("sig=", link_other_bucket)

    def test_get_config(self):
        config = self.azure_blob_instance.get_config()
        self.assertEqual(config["url"], AZURE_ACCOUNT_URL)
        self.assertEqual(config["access_key"], AZURE_ACCOUNT_NAME)
        self.assertEqual(config["secret_key"], AZURE_ACCOUNT_KEY)
        self.assertEqual(config["region"], AZURE_REGION)
        self.assertTrue(config["secure"])  # Based on secure=True passed in setUp

    def test_get_provider(self):
        self.assertEqual(self.azure_blob_instance.get_provider(), AzureBlob.AZURE_BLOB_STORAGE)

    def test_non_existent_blob_download(self):
        non_existent_file = f"does_not_exist_{uuid.uuid4().hex[:8]}.dat"
        with self.assertRaises(ResourceNotFoundError):
            self.azure_blob_instance.download_data(non_existent_file)


if __name__ == "__main__":
    unittest.main()
