import json
import os
from datetime import datetime, timezone

import typer
from langchain_core.documents import Document
from pydantic import Field
from pydantic_settings import BaseSettings
from pymilvus import CollectionSchema, DataType, MilvusClient

from segittur_commons.app.services.milvus import MilvusHandler

DEFAULT_DATABASE = os.getenv("MILVUS_DATABASE", "SEGITTUR_AVC")
DEFAULT_COLLECTION = os.getenv("MILVUS_COLLECTION", "general_vectorstore")
TEST_DATA = "tests/fixtures/milvus_test_data-schema.json"

cli = typer.Typer()


class Settings(BaseSettings):
    milvus_url: str = Field()
    milvus_token: str = Field("")


@cli.callback()
def main(ctx: typer.Context):
    ctx.ensure_object(dict)
    initial_milvus_client = MilvusClient(uri=settings.milvus_url, token=settings.milvus_token)
    ctx.obj["initial_milvus_client"] = initial_milvus_client


def create_milvus_database(milvus_client: MilvusClient, db_name: str, **kwargs_db):
    if db_name not in milvus_client.list_databases():
        milvus_client.create_database(db_name, **kwargs_db)
        print(f"Database '{db_name}' created successfully.")
    milvus_client.use_database(db_name)


def create_milvus_collection(
    milvus_client: MilvusClient,
    collection_name: str,
    db_name: str,
    kwargs_db: dict = {},
    kwargs_collection: dict = {},
):
    create_milvus_database(milvus_client, db_name, **kwargs_db)
    if not milvus_client.has_collection(collection_name):
        milvus_client.create_collection(collection_name=collection_name, **kwargs_collection)
        print(f"Collection '{collection_name}' created successfully in database '{db_name}'.")
    else:
        print(f"Collection with name '{collection_name}' already exists in database '{db_name}'.")


def create_milvus_initial_schema(milvus_client: MilvusClient) -> CollectionSchema:
    schema = milvus_client.create_schema()

    schema.add_field(field_name="pk", datatype=DataType.INT64, is_primary=True, auto_id=True)
    schema.add_field(field_name="name", datatype=DataType.VARCHAR, max_length=1024)
    schema.add_field(field_name="text", datatype=DataType.VARCHAR, max_length=65535)
    schema.add_field(
        field_name="original_content", datatype=DataType.VARCHAR, max_length=65535, nullable=True
    )
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
        description="Timestamp in ISO 8601 format",  # Example: 2025-08-26T12:12:00+0000
        nullable=True,
    )

    return schema


# Only works for milvus >= 2.6
@cli.command(name="update_schema")
def update_schema(
    ctx: typer.Context,
    collection_name: str = typer.Option(DEFAULT_COLLECTION, help="Milvus collection name"),
    db_name: str = typer.Option(DEFAULT_DATABASE, help="Milvus database name"),
):

    initial_milvus_client: MilvusClient = ctx.obj.get("initial_milvus_client")
    initial_milvus_client.use_database(db_name=db_name)
    current_schema = initial_milvus_client.describe_collection(collection_name)
    new_schema = create_milvus_initial_schema(initial_milvus_client)
    current_fields = [field["name"] for field in current_schema["fields"]]
    new_fields = [field.name for field in new_schema.fields]
    to_create = [field for field in new_fields if field not in current_fields]
    for field_name in to_create:
        field = next(field for field in new_schema.fields if field.name == field_name)
        initial_milvus_client.add_collection_field(
            collection_name=collection_name,
            field_name=field.name,
            data_type=field.dtype,
            nullable=field.nullable,
            **field.params,
        )


@cli.command(name="create_database")
def create_database(ctx: typer.Context, db_name: str = typer.Option(help="Milvus database name")):
    initial_milvus_client: MilvusClient = ctx.obj.get("initial_milvus_client")
    create_milvus_database(initial_milvus_client, db_name)


@cli.command(name="create_collection")
def create_collection(
    ctx: typer.Context,
    collection_name: str = typer.Option(help="Milvus collection name"),
    db_name: str = typer.Option(help="Milvus database name"),
    dimension: int = typer.Option(512, help="Milvus vector dimension"),
):
    initial_milvus_client: MilvusClient = ctx.obj.get("initial_milvus_client")
    create_milvus_collection(
        initial_milvus_client, collection_name, db_name, kwargs_collection={"dimension": dimension}
    )


@cli.command(name="remove_collection")
def remove_collection(
    ctx: typer.Context,
    collection_name: str = typer.Option(help="Milvus collection name"),
    db_name: str = typer.Option(help="Milvus database name"),
):
    initial_milvus_client: MilvusClient = ctx.obj.get("initial_milvus_client")
    initial_milvus_client.use_database(db_name)
    initial_milvus_client.drop_collection(collection_name)


@cli.command(name="remove_database")
def remove_database(ctx: typer.Context, db_name: str = typer.Option(help="Milvus database name")):
    initial_milvus_client: MilvusClient = ctx.obj.get("initial_milvus_client")
    initial_milvus_client.use_database(db_name)
    for collection in initial_milvus_client.list_collections():
        initial_milvus_client.drop_collection(collection)
    initial_milvus_client.drop_database(db_name)


@cli.command(name="create_collection_with_initial_schema")
def create_collection_with_initial_schema(
    ctx: typer.Context,
    collection_name: str = typer.Option(DEFAULT_COLLECTION, help="Milvus collection name"),
    db_name: str = typer.Option(DEFAULT_DATABASE, help="Milvus database name"),
):
    initial_milvus_client: MilvusClient = ctx.obj.get("initial_milvus_client")
    if initial_milvus_client.has_collection(collection_name):
        raise typer.BadParameter(f"Collection with name {collection_name} already exists")

    schema = create_milvus_initial_schema(initial_milvus_client)
    create_milvus_collection(
        initial_milvus_client, collection_name, db_name, kwargs_collection={"schema": schema}
    )


@cli.command(name="load_test_data")
def load_test_data(
    ctx: typer.Context,
    data_file: str = typer.Option(TEST_DATA, help="Path to load data"),
    collection_name: str = typer.Option(DEFAULT_COLLECTION, help="Milvus collection name"),
    db_name: str = typer.Option(DEFAULT_DATABASE, help="Milvus database name"),
    use_schema: bool = typer.Option(True, help="Create collection with initial schema"),
):
    """
    Loads test data into the specified Milvus collection.
    """
    initial_milvus_client: MilvusClient = ctx.obj.get("initial_milvus_client")
    create_milvus_database(initial_milvus_client, db_name)
    if not initial_milvus_client.has_collection(collection_name):
        if use_schema:
            create_collection_with_initial_schema(ctx, collection_name, db_name=db_name)
        else:
            create_collection(ctx, collection_name, db_name=db_name)

    with open(data_file, encoding="utf-8") as f:
        data: list[dict] = json.load(f)

    docs: list[Document] = []
    today = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S%z")
    for record in data:
        record["origin"] = "test"
        record.setdefault("creation_datetime", today)
        docs.append(Document(page_content=record.pop("text"), metadata=record))

    milvus = MilvusHandler(db=db_name, collection=collection_name)
    milvus.vector_store.add_documents(docs)
    print("Test data loaded successfully.")


if __name__ == "__main__":
    settings = Settings(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore
    cli()
