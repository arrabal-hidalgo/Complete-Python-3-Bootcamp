import pytest

from segittur_commons.app.services.milvus import MilvusHandler


class TestMilvusHandler:
    test_db = "test_db"
    test_collection = "test_collection"

    @pytest.fixture(scope="class")
    def milvus_conexion(self):
        milvus = MilvusHandler()
        yield milvus
        milvus.client.drop_collection(self.test_collection)
        milvus.client.drop_database(self.test_db)

    def test_manage_database_and_collections(self, milvus_conexion: MilvusHandler):
        milvus_conexion._use_database(self.test_db)
        assert (
            self.test_db in milvus_conexion.client.list_databases()
        ), f"Database '{self.test_db}' should be in the list of databases"

        assert (
            milvus_conexion.client.list_collections() == []
        ), "Collection list should be empty at this moment"
        milvus_conexion.client.create_collection(self.test_collection, dimension=512)
        assert milvus_conexion.client.list_collections() == [
            self.test_collection
        ], f"Collection list should contain ONLY the created collection '{self.test_collection}'"

        milvus_conexion.remove_database(self.test_db)
        assert (
            self.test_db not in milvus_conexion.client.list_databases()
        ), f"Database '{self.test_db}' should NOT be in the list of databases after removing it"
