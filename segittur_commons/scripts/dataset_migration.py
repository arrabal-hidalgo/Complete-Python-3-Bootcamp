import json
from pathlib import Path

import pandas as pd
import typer
from langfuse import Langfuse
from langfuse.api import NotFoundError
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


def get_datasets(datasets_client: DatasetsClient, datasets_names: str) -> list[str]:
    if not datasets_names:
        return [dataset.name for dataset in datasets_client.list(limit=50).data]
    return get_list_args_from_str(datasets_names)


def get_dataset_items(
    langfuse: Langfuse, dataset_name: str, limit: int = MAX_PAGE_SIZE
) -> pd.DataFrame:
    list_items = [
        (item.id, item.input, item.expected_output, item.dataset_id, item.dataset_name)
        for item in langfuse.get_dataset(dataset_name, fetch_items_page_size=limit).items
    ]
    df = pd.DataFrame(
        list_items, columns=["id", "input", "expected_output", "dataset_id", "dataset_name"]
    )
    df["input"] = df["input"].apply(lambda x: json.dumps(x, ensure_ascii=False))
    if isinstance(df["expected_output"].loc[0], dict):
        df["expected_output"] = df["expected_output"].apply(
            lambda x: json.dumps(x, ensure_ascii=False)
        )
    # reverse items to keep the original order
    return df.iloc[::-1].reset_index(drop=True)


@cli.command(name="export")
def export_datasets(
    ctx: typer.Context,
    output_data_dir: str = typer.Option(help="Directory path to save the exported datasets"),
    datasets_to_export: str = typer.Option(
        "", help="Comma-separated list of datasets to export. e.g. 'dataset1,dataset2'"
    ),
    page_size: int = typer.Option(MAX_PAGE_SIZE, help="Page size"),
):
    if page_size > (max_page_size := MAX_PAGE_SIZE):
        print(f"\nWARNING: Resized page size to maximum size allowed ({max_page_size})")
        page_size = MAX_PAGE_SIZE

    langfuse: Langfuse = ctx.obj.get("langfuse")
    for dataset_name in get_datasets(langfuse.api.datasets, datasets_to_export):
        print(f"\n-> Dataset: {dataset_name}")
        df_items = get_dataset_items(langfuse, dataset_name, page_size)
        df_items.to_csv(Path(output_data_dir, f"{dataset_name}.csv"), index=False)
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


def create_dataset(langfuse: Langfuse, path: Path):
    dataset_name = path.stem
    print(f"\n- Dataset: {dataset_name}")
    df = pd.read_csv(path, usecols=["input", "expected_output"]).drop_duplicates()

    try:
        # Get old items from the dataset
        df_old_data = get_dataset_items(langfuse, dataset_name)[["input", "expected_output"]]
        # Remove duplicates in the new data
        df = pd.concat([df_old_data, df]).drop_duplicates(keep=False)
    except NotFoundError:
        pass

    df["input"] = df["input"].apply(json.loads)
    try:
        df["expected_output"] = df["expected_output"].apply(json.loads)
    except json.JSONDecodeError:
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
    input_data_dir: str = typer.Option(help="Path's directory of the datasets's data"),
    datasets_to_import: str = typer.Option(
        "", help="Comma-separated list of datasets to import. e.g. 'dataset1,dataset2'"
    ),
):
    for path in get_files(input_data_dir, datasets_to_import):
        create_dataset(ctx.obj.get("langfuse"), path)


if __name__ == "__main__":
    settings = Settings(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore
    cli()
