from pathlib import Path

import typer
from langfuse import Langfuse


def check_langfuse_connection(langfuse: Langfuse):
    try:
        langfuse.auth_check()
    except Exception as e:
        raise typer.Abort(
            f"Auth check failed. Please check your credentials and config. Error: {e}"
        )


def get_list_objects_from_str(list_arg: str) -> list[str]:
    if list_arg:
        objects_list = [arg.strip() for arg in list_arg.split(",")]
        print(f"\nObjects: {objects_list}\n")
        return objects_list
    print("\n--- ALL ---")
    return []


def get_files(input_dir: str, list_objects: list[str], file_format: str) -> list[Path]:
    base_path = Path(input_dir)
    return (
        [base_path.joinpath(f"{object_name}.{file_format}") for object_name in list_objects]
        if list_objects
        else list(base_path.glob(f"*.{file_format}"))
    )
