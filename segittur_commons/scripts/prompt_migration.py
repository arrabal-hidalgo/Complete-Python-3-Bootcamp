import json
import os
import re
from pathlib import Path
from typing import Union

import typer
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

from segittur_commons.app.services.langfuse_service import LangfuseHandler
from segittur_commons.scripts.utils import (
    check_langfuse_connection,
    get_files,
    get_list_objects_from_str,
)

cli = typer.Typer()


class Settings(BaseSettings):
    langfuse_public_key: str = Field()
    langfuse_secret_key: str = Field()
    langfuse_host: str = Field()
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class ChatPrompt(BaseModel):
    role: str
    content: str


class Placeholder(BaseModel):
    name: str
    type: str


class PromptModel(BaseModel):
    prompt: Union[str, list[Union[ChatPrompt, Placeholder]]]
    name: str
    version: int
    config: dict
    labels: list[str]
    tags: list[str]
    type: str


def get_prefix_and_prompt_name(prompt_full_name: str):
    return re.findall(r"^\[(.*?)\](.*)", prompt_full_name)[0]


def get_prompt_versions(
    langfuse_handler: LangfuseHandler, prefix_names_prompts: dict[str, list[str]]
) -> dict[str, dict[str, list[int]]]:
    prefix_prompt_versions = {}
    for prompt in langfuse_handler.langfuse.api.prompts.list(limit=50).data:
        try:
            prompt_prefix, prompt_name = get_prefix_and_prompt_name(prompt.name)
        except IndexError:
            continue
        if not prefix_names_prompts or prompt_name in prefix_names_prompts.get(prompt_prefix, []):
            prefix_prompt_versions.setdefault(prompt_prefix, {})[prompt_name] = prompt.versions
    return prefix_prompt_versions


def get_prompt_objects(
    langfuse_handler: LangfuseHandler, prompt_name: str, versions: list[int]
) -> list[dict[str, str]]:
    langfuse_prompts_client = langfuse_handler.langfuse.api.prompts
    return [
        {
            key: value
            for key, value in langfuse_prompts_client.get(prompt_name=prompt_name, version=version)
            .dict()
            .items()
            if key in PromptModel.model_fields
        }
        for version in versions
    ]


def create_prompt(langfuse_handler: LangfuseHandler, prompt: PromptModel):
    print(f"- {prompt.name}, version: {prompt.version}")
    content = (
        prompt.prompt
        if prompt.type == "text"
        else [prompt_object.model_dump() for prompt_object in prompt.prompt]
    )
    langfuse_handler.langfuse.create_prompt(
        type=prompt.type,
        name=prompt.name,
        prompt=content,
        config=prompt.config,
        labels=prompt.labels,
        tags=prompt.tags,
    )


def get_list_prompts_from_args(list_args: str) -> dict[str, list[str]]:
    list_prompts_args = get_list_objects_from_str(list_args)
    prefix_names_dict = {}
    list_aux = list_prompts_args.copy()
    for prompt_full_name in list_prompts_args:
        try:
            prompt_prefix, prompt_name = get_prefix_and_prompt_name(prompt_full_name)
            prefix_names_dict.setdefault(prompt_prefix, []).append(prompt_name)
        except IndexError:
            print(f"\n>>>>>> Incorrect prompt name format ({prompt_full_name})!!! <<<<<<\n")
            list_aux.remove(prompt_full_name)
    if list_prompts_args and not list_aux:
        raise Exception(f"None of the prompts have a correct name format: {list_prompts_args}")
    return prefix_names_dict


@cli.callback()
def main(ctx: typer.Context):
    ctx.ensure_object(dict)
    langfuse_handler = LangfuseHandler()
    check_langfuse_connection(langfuse_handler.langfuse)
    ctx.obj["langfuse_handler"] = langfuse_handler


@cli.command(name="export")
def export_prompts(
    ctx: typer.Context,
    output_data_dir: str = typer.Option(help="Directory path to save the exported prompts"),
    prompts_to_export: str = typer.Option(
        "", help="Comma-separated list of prompts to export. e.g. 'prompt1,prompt2'"
    ),
):
    langfuse_handler: LangfuseHandler = ctx.obj.get("langfuse_handler")

    prefix_names_dict = get_list_prompts_from_args(prompts_to_export)
    prefix_prompt_versions = get_prompt_versions(langfuse_handler, prefix_names_dict).items()

    for prompt_prefix, prompt_versions in prefix_prompt_versions:
        dir_path = Path(output_data_dir).joinpath(prompt_prefix)
        os.makedirs(dir_path, exist_ok=True)
        for prompt_name, versions in prompt_versions.items():
            prompt_full_name = f"[{prompt_prefix}]{prompt_name}"
            prompts = get_prompt_objects(langfuse_handler, prompt_full_name, versions)
            with open(dir_path.joinpath(f"{prompt_name}.json"), "w", encoding="utf-8") as file:
                print(f"-> Prompt: {prompt_full_name}")
                json.dump(prompts, file, indent=2, ensure_ascii=False)


@cli.command(name="import")
def import_prompts(
    ctx: typer.Context,
    input_data_dir: str = typer.Option(help="Path's directory of the prompts's data"),
    prompts_to_import: str = typer.Option(
        "", help="Comma-separated list of prompts to import. e.g. 'prompt1,prompt2'"
    ),
):
    langfuse_handler: LangfuseHandler = ctx.obj.get("langfuse_handler")

    prefix_names_dict = get_list_prompts_from_args(prompts_to_import)
    old_prefix_prompt_versions = get_prompt_versions(langfuse_handler, prefix_names_dict)

    base_path = Path(input_data_dir)
    for subdir in base_path.iterdir():
        if subdir.is_dir():
            if not (list_prompts := prefix_names_dict.get(subdir.name, [])) and prefix_names_dict:
                continue
            print(f"\n---- Prompts group: {subdir.name} ----")
            list_files = get_files(base_path.joinpath(subdir.name), list_prompts, "json")
            for file_path in list_files:
                with open(file_path, "r", encoding="utf-8") as file:
                    prompts = json.load(file)
                new_prompts = [
                    PromptModel(**prompt)
                    for prompt in prompts
                    if prompt["version"]
                    not in old_prefix_prompt_versions.get(subdir.name, {}).get(file_path.stem, [])
                ]
                if not new_prompts:
                    continue
                print(f"NEW VERSIONS ({file_path.name}):")
                for prompt in new_prompts:
                    create_prompt(langfuse_handler, prompt)
                print("--------------")


if __name__ == "__main__":
    settings = Settings(_env_file=".env", _env_file_encoding="utf-8")  # type: ignore
    cli()
