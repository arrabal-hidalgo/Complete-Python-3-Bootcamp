import csv
import glob
import json
import os
from dataclasses import dataclass, field

import typer
from langfuse import Langfuse
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

cli = typer.Typer()


class Settings(BaseSettings):
    langfuse_public_key: str = Field()
    langfuse_secret_key: str = Field()
    langfuse_host: str = Field()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


@dataclass
class DatasetItem:
    input: dict = field(default_factory=dict)
    expected_output: dict = field(default_factory=dict)


def check_langfuse_connection(langfuse: Langfuse):
    try:
        langfuse.auth_check()
    except Exception as e:
        raise typer.Abort(
            f"Auth check failed. Please check your credentials and config. Error: {e}"
        )


def get_datasets(langfuse: Langfuse) -> dict[str, list[DatasetItem]]:
    datasets_client = langfuse.api.datasets
    datasets = datasets_client.list(limit=60).data
    data = {}
    for dataset in datasets:
        items = get_dataset_items(langfuse=langfuse, dataset=dataset)
        data[dataset.name] = items
    return data


def get_dataset_items(langfuse: Langfuse, dataset) -> list[DatasetItem]:
    return langfuse.get_dataset(dataset.name).items


def create_csv_for_items(dataset_name, items: list[DatasetItem], dir: str):
    with open(f"{dir}/{dataset_name}.csv", "w", encoding="utf-8") as file:
        file.write("input, expected_output\n")
        for item in items:
            file.write(
                f'"{json.dumps(item.input, ensure_ascii=False).replace('"', '""')}",{json.dumps(item.expected_output, ensure_ascii=False)}\n'
            )


def create_dataset(langfuse: Langfuse, name: str, items: list[DatasetItem]):
    langfuse.create_dataset(name=name)
    for item in items:
        langfuse.create_dataset_item(
            dataset_name=name, input=item.input, expected_output=item.expected_output
        )


@cli.callback()
def main(ctx: typer.Context):
    ctx.ensure_object(dict)
    langfuse = Langfuse()
    check_langfuse_connection(langfuse)
    ctx.obj["langfuse"] = langfuse


@cli.command(name="export")
def export_datasets(
    ctx: typer.Context,
    output_path: str = typer.Option(None, help="Directory path to save the exported datasets"),
):
    datasets = get_datasets(ctx.obj.get("langfuse"))
    for dataset, items in datasets.items():
        create_csv_for_items(dataset_name=dataset, items=items, dir=output_path)


@cli.command(name="import")
def import_datasets(
    ctx: typer.Context,
    input_path: str = typer.Option(None, help="Directory path to import the exported datasets"),
):
    file_paths = glob.glob(f"{input_path}/*.csv")

    for file_path in file_paths:
        name = os.path.basename(file_path).replace(".csv", "")
        items = []
        with open(file_path, encoding="utf-8") as file:
            reader = csv.reader(file, delimiter=";")
            # Skip header
            next(reader, None)
            for row in reader:
                items.append(
                    DatasetItem(input=json.loads(row[0]), expected_output=json.loads(row[1]))
                )
        create_dataset(ctx.obj.get("langfuse"), name, items)


if __name__ == "__main__":
    settings = Settings(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore
    cli()
