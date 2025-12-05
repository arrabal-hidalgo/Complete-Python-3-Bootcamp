import csv
import json
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd
import typer
from langfuse import Langfuse
from langfuse.api import Dataset
from langfuse.api.resources.dataset_items.client import DatasetItemsClient
from langfuse.api.resources.datasets.client import DatasetsClient
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from segittur_commons.scripts.utils import get_list_args_from_str

cli = typer.Typer()

MAX_PAGE_SIZE = 100


class Settings(BaseSettings):
    langfuse_public_key: str = Field()
    langfuse_secret_key: str = Field()
    langfuse_host: str = Field()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@dataclass
class DatasetItem:
    input: dict = field(default_factory=dict)
    expected_output: dict | str = field(default_factory=str)


def check_langfuse_connection(langfuse: Langfuse):
    try:
        langfuse.auth_check()
    except Exception as e:
        raise typer.Abort(
            f"Auth check failed. Please check your credentials and config. Error: {e}"
        )


@cli.callback()
def main(ctx: typer.Context):
    ctx.ensure_object(dict)
    langfuse = Langfuse()
    check_langfuse_connection(langfuse)
    ctx.obj["langfuse"] = langfuse


def get_datasets(datasets_client: DatasetsClient, datasets_names: str) -> list[Dataset]:
    return (
        datasets_client.list(limit=50).data
        if not datasets_names
        else [
            datasets_client.get(dataset_name)
            for dataset_name in get_list_args_from_str(datasets_names)
        ]
    )


def get_dataset_items(
    datasets_items_client: DatasetItemsClient, dataset: Dataset, limit: int
) -> list[DatasetItem]:
    items = []
    page = 1
    while True:
        page_items = datasets_items_client.list(
            dataset_name=dataset.name, page=page, limit=limit
        ).data
        items.extend(page_items)
        if len(page_items) < limit:
            break
        page += 1
    return [
        DatasetItem(item.input, item.expected_output)
        for item in items
        if item.input and item.expected_output
    ]


def create_csv_for_items(dataset_name: str, items: list[DatasetItem], dir: str):
    with open(f"{dir}/{dataset_name}.csv", "w", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow(["input", "expected_output"])
        for item in items:
            input = json.dumps(item.input)
            output = (
                item.expected_output
                if isinstance(item.expected_output, str)
                else json.dumps(item.expected_output)
            )
            writer.writerow([input, output])


@cli.command(name="export")
def export_datasets(
    ctx: typer.Context,
    output_dir: str = typer.Option(None, help="Directory path to save the exported datasets"),
    datasets_to_export: str = typer.Option(
        "", help="Comma-separated list of datasets to export. e.g. 'dataset1,dataset2'"
    ),
    page_size: int = typer.Option(1000, help="Page size"),
):
    if page_size > (max_page_size := 100):
        print(f"WARNING: Resized page size to maximum size allowed ({max_page_size})")
        page_size = 100

    langfuse: Langfuse = ctx.obj.get("langfuse")
    for dataset in get_datasets(langfuse.api.datasets, datasets_to_export):
        dataset_name = dataset.name
        print(f"-> Dataset: {dataset_name}")
        items = get_dataset_items(langfuse.api.dataset_items, dataset, page_size)
        create_csv_for_items(dataset_name, items, output_dir)


def get_files(input_dir: str, datasets_names: str) -> list[Path]:
    base_path = Path(input_dir)
    return (
        list(base_path.glob("*.csv"))
        if not datasets_names
        else [
            base_path.joinpath(f"{dataset_name}.csv")
            for dataset_name in get_list_args_from_str(datasets_names)
        ]
    )


def create_dataset(langfuse: Langfuse, path: Path):
    with open(path, "r", encoding="utf-8") as file:
        reader = csv.reader(file)
        dataset_name = path.stem
        print(f"-> Dataset: {dataset_name}")

        next(reader, None)  # Skip header
        langfuse.create_dataset(name=dataset_name)
        for row in reader:
            input = json.loads(row[0])
            try:
                output = json.loads(row[1])
            except json.decoder.JSONDecodeError:
                output = row[1]
            item = DatasetItem(input=input, expected_output=output)
            langfuse.create_dataset_item(
                dataset_name=dataset_name, input=item.input, expected_output=item.expected_output
            )


@cli.command(name="import")
def import_datasets(
    ctx: typer.Context,
    input_dir: str = typer.Option(None, help="Directory path to import the exported datasets"),
    datasets_to_import: str = typer.Option(
        "", help="Comma-separated list of datasets to import. e.g. 'dataset1,dataset2'"
    ),
):
    for path in get_files(input_dir, datasets_to_import):
        create_dataset(ctx.obj.get("langfuse"), path)


if __name__ == "__main__":
    settings = Settings(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore
    cli()
