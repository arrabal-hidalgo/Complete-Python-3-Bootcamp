import re
from dataclasses import dataclass, field
from pathlib import Path
from pathlib import Path

import pandas as pd
import typer
from langfuse import Langfuse
from langfuse.api import NotFoundError
from langfuse.api.resources.datasets.client import DatasetsClient
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from segittur_commons.scripts.utils import get_list_args_from_str

from segittur_commons.scripts.utils import get_list_args_from_str

cli = typer.Typer()

MAX_PAGE_SIZE = 100


class Settings(BaseSettings):
    langfuse_public_key: str = Field()
    langfuse_secret_key: str = Field()
    langfuse_host: str = Field()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


def check_langfuse_connection(langfuse: Langfuse):
    try:
        langfuse.auth_check()
    except Exception as e:
        raise typer.Abort(
            f"Auth check failed. Please check your credentials and config. Error: {e}"
        )


@dataclass
class DatasetName:
    prefix: str = field(default_factory=str)
    name: str = field(default_factory=str)

    def __str__(self):
        return f"[{self.prefix}]{self.name}"


@cli.callback()
def main(ctx: typer.Context):
    ctx.ensure_object(dict)
    langfuse = Langfuse()
    check_langfuse_connection(langfuse)
    ctx.obj["langfuse"] = langfuse


def get_dataset_name(full_name: str) -> DatasetName:
    return DatasetName(*re.findall(r"\[(.*)\](.*)", full_name)[0])


def get_datasets(
    datasets_client: DatasetsClient, dataset_prefix: str, datasets_names: str
) -> list[DatasetName]:
    if not datasets_names:
        return [get_dataset_name(dataset.name) for dataset in datasets_client.list(limit=50).data]
    return [
        DatasetName(dataset_prefix, dataset_main_name)
        for dataset_main_name in get_list_args_from_str(datasets_names)
    ]


def get_dataset_items(
    langfuse: Langfuse, dataset_name: DatasetName, limit: int = MAX_PAGE_SIZE
) -> pd.DataFrame:
    list_items = [
        (item.input, item.expected_output)
        for item in langfuse.get_dataset(str(dataset_name), fetch_items_page_size=limit).items
    ]
    return pd.DataFrame(list_items, columns=["input", "expected_output"])


@cli.command(name="export")
def export_datasets(
    ctx: typer.Context,
    output_data_dir: str = typer.Option(None, help="Directory path to save the exported datasets"),
    dataset_prefix: str = typer.Option(
        None, help="Langfuse prefix of the datasets's data to export"
    ),
    datasets_to_export: str = typer.Option(
        "", help="Comma-separated list of datasets to export. e.g. 'dataset1,dataset2'"
    ),
    page_size: int = typer.Option(MAX_PAGE_SIZE, help="Page size"),
):
    if page_size > (max_page_size := MAX_PAGE_SIZE):
        print(f"\nWARNING: Resized page size to maximum size allowed ({max_page_size})")
        page_size = MAX_PAGE_SIZE

    langfuse: Langfuse = ctx.obj.get("langfuse")
    for dataset_name in get_datasets(langfuse.api.datasets, dataset_prefix, datasets_to_export):
        print(f"\n-> Dataset: {dataset_name}")
        df_items = get_dataset_items(langfuse, dataset_name, page_size)
        df_items.to_csv(Path(output_data_dir, f"{dataset_name.name}.csv"), index=False)
        print(f"--> {len(df_items)} exported items.\n")


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


def create_dataset(langfuse: Langfuse, path: Path, dataset_prefix: str):
    dataset_name = DatasetName(dataset_prefix, path.stem)
    print(f"\n- Dataset: {dataset_name}")
    df = pd.read_csv(path).drop_duplicates()

    try:
        # Get old items from the dataset
        df_old_data = get_dataset_items(langfuse, dataset_name)
        # Remove duplicates in the new data
        df = pd.concat([df_old_data, df]).drop_duplicates(keep=False)
    except NotFoundError:
        pass

    str_dataset_name = str(dataset_name)
    langfuse.create_dataset(name=str_dataset_name)
    if df.empty:
        print("--> No new items to import.\n")
    else:
        for item in df.itertuples(index=False):
            langfuse.create_dataset_item(
                dataset_name=str_dataset_name,
                input=item.input,
                expected_output=item.expected_output,
            )
        print(f"--> {len(df)} new imported items.\n")


@cli.command(name="import")
def import_datasets(
    ctx: typer.Context,
    input_data_dir: str = typer.Option(None, help="Path's directory of the datasets's data"),
    dataset_prefix: str = typer.Option(None, help="Langfuse prefix to import the datasets's data"),
    datasets_to_import: str = typer.Option(
        "", help="Comma-separated list of datasets to import. e.g. 'dataset1,dataset2'"
    ),
):
    for path in get_files(input_data_dir, datasets_to_import):
        create_dataset(ctx.obj.get("langfuse"), path, dataset_prefix)


if __name__ == "__main__":
    settings = Settings(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore
    cli()
