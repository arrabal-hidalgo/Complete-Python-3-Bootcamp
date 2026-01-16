import json
from enum import Enum
from pathlib import Path
from uuid import uuid4

import pandas as pd
import typer
from langfuse.api import NotFoundError
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from segittur_commons.app.services.langfuse_service import LangfuseHandler
from segittur_commons.scripts.utils import (
    check_langfuse_connection,
    get_list_args_from_str,
)

cli = typer.Typer()

MAX_PAGE_SIZE = 100


class Settings(BaseSettings):
    langfuse_public_key: str = Field()
    langfuse_secret_key: str = Field()
    langfuse_host: str = Field()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class DatasetCols(str, Enum):
    id = "id"
    input = "input"
    expected_output = "expected_output"
    dataset_name = "dataset_name"

    @classmethod
    def values(cls):
        return [member.value for member in DatasetCols]


def read_data(df: pd.DataFrame) -> tuple[pd.DataFrame, list[str], list[str]]:
    def expand_json(df: pd.DataFrame, col_name: str) -> pd.DataFrame:
        return df[col_name].apply(json.loads).apply(pd.Series)

    df_inputs = expand_json(df, DatasetCols.input)
    try:
        df_outputs = expand_json(df, DatasetCols.expected_output)
    except json.JSONDecodeError:
        df_outputs = df[[DatasetCols.expected_output]]

    data_dfs = [df_inputs, df_outputs]
    list_dfs = [df[id_col], *data_dfs] if (id_col := DatasetCols.id) in df.columns else data_dfs
    return pd.concat(list_dfs, axis=1), list(df_inputs.columns), list(df_outputs.columns)


def restore_data(df: pd.DataFrame, input_cols: list[str], output_cols: list[str]):
    def restore_json(df: pd.DataFrame, columns: list[str]) -> pd.Series:
        return df.apply(
            lambda x: json.dumps({col: x[col] for col in columns}, ensure_ascii=False), axis=1
        )

    df[DatasetCols.input] = restore_json(df, input_cols)
    if output_cols != [DatasetCols.expected_output]:
        df[DatasetCols.expected_output] = restore_json(df, output_cols)
    return df[[DatasetCols.input, DatasetCols.expected_output]]


def get_datasets(langfuse_handler: LangfuseHandler, datasets_names: str) -> list[str]:
    if not datasets_names:
        return [
            dataset.name for dataset in langfuse_handler.langfuse.api.datasets.list(limit=50).data
        ]
    return get_list_args_from_str(datasets_names)


def get_dataset_items(
    langfuse_handler: LangfuseHandler, dataset_name: str, limit: int = MAX_PAGE_SIZE
) -> pd.DataFrame:
    list_items = [
        (item.id, item.input, item.expected_output, item.dataset_name)
        for item in langfuse_handler.get_dataset_items(dataset_name, fetch_items_page_size=limit)
    ]
    df = pd.DataFrame(list_items, columns=DatasetCols.values())
    df[DatasetCols.input] = df[DatasetCols.input].apply(lambda x: json.dumps(x, ensure_ascii=False))
    if isinstance(df[DatasetCols.expected_output].loc[0], dict):
        df[DatasetCols.expected_output] = df[DatasetCols.expected_output].apply(
            lambda x: json.dumps(x, ensure_ascii=False)
        )
    return df.reset_index(drop=True)


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


def create_dataset(langfuse_handler: LangfuseHandler, path: Path):
    dataset_name = path.stem
    print(f"\n- Dataset: {dataset_name}")

    df, input_cols, output_cols = read_data(pd.read_csv(path))
    df = df.drop_duplicates()

    try:
        # Get old items from the dataset
        df_old_data, _, _ = read_data(get_dataset_items(langfuse_handler, dataset_name))
        # Remove duplicates in the new data
        df = pd.concat([df_old_data, df]).drop_duplicates(input_cols + output_cols, keep="first")
        # Check if there are rows with the same input, and different expected_output
        df_input_duplicated = df[df.duplicated(input_cols, keep=False)]
        if len(df_input_duplicated) > 0:
            raise Exception(
                f"There are duplicated inputs for the ids: {list(df_input_duplicated[DatasetCols.id].dropna())}"
            )
        # Restore df with new data
        df = df[df[DatasetCols.id].isna()]
    except NotFoundError:
        pass

    if df.empty:
        print("--> No new items to import.\n")
    else:
        df = restore_data(df, input_cols, output_cols)

        langfuse_handler.langfuse.create_dataset(name=dataset_name)

        df[DatasetCols.input] = df[DatasetCols.input].apply(json.loads)
        try:
            df[DatasetCols.expected_output] = df[DatasetCols.expected_output].apply(json.loads)
        except json.JSONDecodeError:
            pass

        for row in df.iterrows():
            item = row[1]
            langfuse_handler.langfuse.create_dataset_item(
                dataset_name=dataset_name,
                input=item[DatasetCols.input],
                expected_output=item[DatasetCols.expected_output],
                id=str(uuid4()),
            )
        print(f"--> {len(df)} new imported items.\n")


@cli.callback()
def main(ctx: typer.Context):
    ctx.ensure_object(dict)
    langfuse_handler = LangfuseHandler()
    check_langfuse_connection(langfuse_handler.langfuse)
    ctx.obj["langfuse_handler"] = langfuse_handler


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

    langfuse_handler: LangfuseHandler = ctx.obj.get("langfuse_handler")
    for dataset_name in get_datasets(langfuse_handler, datasets_to_export):
        print(f"\n-> Dataset: {dataset_name}")
        df_items = get_dataset_items(langfuse_handler, dataset_name, page_size)
        df_items.to_csv(Path(output_data_dir, f"{dataset_name}.csv"), index=False)
        print(f"--> {len(df_items)} exported items.\n")


@cli.command(name="import")
def import_datasets(
    ctx: typer.Context,
    input_data_dir: str = typer.Option(help="Path's directory of the datasets's data"),
    datasets_to_import: str = typer.Option(
        "", help="Comma-separated list of datasets to import. e.g. 'dataset1,dataset2'"
    ),
):
    for path in get_files(input_data_dir, datasets_to_import):
        create_dataset(ctx.obj.get("langfuse_handler"), path)


if __name__ == "__main__":
    settings = Settings(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore
    cli()
