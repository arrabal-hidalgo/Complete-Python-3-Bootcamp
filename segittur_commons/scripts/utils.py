import typer
from langfuse import Langfuse


def get_list_args_from_str(list_arg: str) -> list[str]:
    return [arg.strip() for arg in list_arg.split(",")]


def check_langfuse_connection(langfuse: Langfuse):
    try:
        langfuse.auth_check()
    except Exception as e:
        raise typer.Abort(
            f"Auth check failed. Please check your credentials and config. Error: {e}"
        )
