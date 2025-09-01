import json

import typer
from pymilvus import DataType

from segittur_commons.app.services.milvus import (
    DEFAULT_COLLECTION,
    DEFAULT_DATABASE,
    MilvusHandler,
)

cli = typer.Typer()

TEST_DATA = "tests/fixtures/milvus_test_data.json"


@cli.callback()
def main(ctx: typer.Context):
    ctx.ensure_object(dict)
    milvus = MilvusHandler()
    ctx.obj["milvus"] = milvus


@cli.command(name="create_milvus_schema")
def create_milvus_initial_schema(
    ctx: typer.Context,
    collection_name: str = typer.Option(DEFAULT_COLLECTION, help="Milvus collection name"),
    db_name: str = typer.Option(DEFAULT_DATABASE, help="Milvus database name"),
):
    milvus: MilvusHandler = ctx.obj.get("milvus")
    if milvus.exists_collection(collection_name=collection_name):
        raise typer.Exit(f"Collection with name {collection_name} already exists")

    schema = milvus.create_schema()

    schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True, auto_id=True)
    schema.add_field(field_name="name", datatype=DataType.VARCHAR, max_length=1024)
    schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(
        field_name="classes", datatype=DataType.VARCHAR, max_length=65535, nullable=True
    )
    schema.add_field(field_name="origin", datatype=DataType.VARCHAR, max_length=5535)
    schema.add_field(
        field_name="destination", datatype=DataType.VARCHAR, max_length=512, is_partition_key=True
    )
    schema.add_field(field_name="vector", datatype=DataType.FLOAT_VECTOR, dim=1536)
    schema.add_field(
        field_name="creation_datetime",
        datatype=DataType.VARCHAR,
        max_length=64,
        description="Timestamp in ISO 8601 format",  # Example: 2025-08-26T12:12:00+0000
    )
    schema.add_field(
        field_name="expiration_date",
        datatype=DataType.VARCHAR,
        max_length=64,
        description="Timestamp in ISO 8601 format",  # Example: 2025-08-26T12:12:00+0000,
        nullable=True,
    )

    milvus.create_collection(collection_name=collection_name, schema=schema, db_name=db_name)


@cli.command(name="load_data")
def load_initial_milvus_data(
    ctx: typer.Context,
    data_file: str = typer.Option(TEST_DATA, help="Path to load data"),
    collection_name: str = typer.Option(DEFAULT_COLLECTION, help="Milvus collection name"),
    db_name: str = typer.Option(DEFAULT_DATABASE, help="Milvus database name"),
):
    milvus: MilvusHandler = ctx.obj.get("milvus")
    if not milvus.exists_collection(collection_name):
        with open(data_file, encoding="utf-8") as f:
            raw_docs: list[dict] = json.load(f)
        texts = [doc.pop("text") for doc in raw_docs]
        milvus.create_vector_store_from_texts(
            texts=texts, metadatas=raw_docs, collection_name=collection_name, db_name=db_name
        )


@cli.command(name="create_database")
def create_database(
    ctx: typer.Context, db_name: str = typer.Option(DEFAULT_DATABASE, help="Milvus database name")
):
    milvus: MilvusHandler = ctx.obj.get("milvus")
    milvus.create_database(db_name)


@cli.command(name="remove_collection")
def remove_milvus_collection(
    ctx: typer.Context,
    collection_name: str = typer.Option(DEFAULT_COLLECTION, help="Milvus collection name"),
):
    milvus: MilvusHandler = ctx.obj.get("milvus")
    milvus.remove_collection(collection_name)


@cli.command(name="remove_database")
def remove_milvus_database(
    ctx: typer.Context, db_name: str = typer.Option(DEFAULT_DATABASE, help="Milvus database name")
):
    milvus: MilvusHandler = ctx.obj.get("milvus")
    milvus.remove_database(db_name)


if __name__ == "__main__":
    cli()
