from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer
from datamodel_code_generator import DataModelType, PythonVersion

from segittur_commons.app.services.graphql_dowloader import download_graphql_schema

app = typer.Typer(
    help="CLI to download GraphQL/REST schemas and generate Pydantic v2 models."
)


def convert_introspection_json_to_sdl(
    json_path: Path, sdl_output_dir: Path = Path("schemas")
) -> Optional[Path]:
    """Convert an introspection JSON file to GraphQL SDL and save it under schemas/.

    - If the JSON has the shape {"data": {"__schema": ...}}, it will be converted to SDL
      and written to sdl_output_dir/<stem>.graphql.
    - Returns the saved .graphql Path on success, or None if the JSON is not an introspection
      result or if conversion fails.
    """
    try:
        import json

        from graphql import build_client_schema  # type: ignore
        from graphql import print_schema

        with json_path.open(encoding="utf-8") as f:
            data = json.load(f)

        if not (
            isinstance(data, dict)
            and isinstance(data.get("data"), dict)
            and data["data"].get("__schema")
        ):
            return None

        schema = build_client_schema(data["data"])  # type: ignore[arg-type]
        sdl_text = print_schema(schema)

        sdl_output_dir = sdl_output_dir.expanduser().resolve()
        sdl_output_dir.mkdir(parents=True, exist_ok=True)
        sdl_path = sdl_output_dir / (json_path.stem + ".graphql")
        sdl_path.write_text(sdl_text, encoding="utf-8")
        typer.echo(f"SDL schema saved to: {sdl_path}")
        return sdl_path
    except Exception as conv_err:
        typer.echo(f"Warning: Failed to convert introspection JSON to SDL: {conv_err}")
        return None


@app.command("download-graphql")
def download_graphql(
    url: str = typer.Argument(..., help="GraphQL endpoint URL."),
    output_path: str = typer.Option("schemas", help="Output directory."),
    output_file: str = typer.Option("schema.json", help="Output file name (JSON)."),
    auth_header: Optional[str] = typer.Option(
        None,
        help=(
            "Authorization header to include, e.g., 'Bearer <TOKEN>'. "
            "If provided, it will be sent as 'Authorization'."
        ),
    ),
    timeout: float = typer.Option(30.0, help="Request timeout in seconds."),
):
    """Download the GraphQL schema from the provided endpoint and save it to disk."""
    headers = {"Authorization": auth_header} if auth_header else None
    saved = download_graphql_schema(
        url=url,
        output_path=output_path,
        output_file=output_file,
        headers=headers,
        timeout=timeout,
    )
    typer.echo(f"Schema saved to: {saved}")


@app.command("generate-models")
def generate_models(
    input_path: str = typer.Argument(
        ..., help="Path to the schema (GraphQL, OpenAPI, etc.)."
    ),
    output: str = typer.Option(
        "models.py", help="Output path for the generated models file (.py)."
    ),
    target_python_version: PythonVersion = typer.Option(
        PythonVersion.PY_313.value,
        help=(
            "Target Python version for the generated code (PythonVersion enum, e.g., PY_39, PY_310). "
            "If a GraphQL introspection JSON is provided, it will be converted to SDL and saved under 'schemas/'."
        ),
    ),
):
    """Generate Pydantic v2 classes from a GraphQL schema using datamodel-code-generator.

    This command supports multiple schema formats like GraphQL (.graphql, .gql, introspection .json)
    and OpenAPI (.json, .yaml).

    When a GraphQL introspection JSON is provided, it is first converted to a .graphql SDL file
    to ensure stable code generation.
    """
    try:
        # Lazy import, so the 'download' command does not require this dependency unless used.
        from datamodel_code_generator import InputFileType  # type: ignore
        from datamodel_code_generator import generate as dcg_generate  # type: ignore
    except Exception as e:  # pragma: no cover - runtime help message
        raise typer.BadParameter(
            "The package 'datamodel-code-generator' is required. Install the dependency:\n"
            "  pip install datamodel-code-generator\n\n"
            f"Error details: {e}"
        )

    output_path = Path(output).expanduser().resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    src_path = Path(input_path).expanduser().resolve()

    # Let datamodel-code-generator detect the input file type
    input_file_type = InputFileType.Auto

    # If input is a GraphQL introspection JSON, convert it to SDL first for better processing.
    actual_input: Path = src_path
    if src_path.suffix.lower() == ".json":
        converted = convert_introspection_json_to_sdl(src_path, Path("schemas"))
        if converted is not None:
            # If conversion is successful, we know it's GraphQL.
            # Using the converted SDL file is more reliable with the generator.
            actual_input = converted
            input_file_type = InputFileType.GraphQL

    dcg_generate(
        input_=actual_input,
        output=output_path,
        input_file_type=input_file_type,
        target_python_version=target_python_version,
        output_model_type=DataModelType.PydanticV2BaseModel,
    )

    typer.echo(f"Models generated at: {output_path}")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
