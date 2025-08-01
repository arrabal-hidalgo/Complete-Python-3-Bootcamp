import json
from pathlib import Path
from typing import Any, Union

import typer
import yaml
from langfuse import Langfuse
from langfuse.api import ChatMessage, CreatePromptRequest_Chat, CreatePromptRequest_Text
from langfuse.callback import CallbackHandler
from pydantic import BaseModel, Field
from pydantic_settings import BaseSettings, SettingsConfigDict

cli = typer.Typer()


class Settings(BaseSettings):
    langfuse_public_key: str = Field()
    langfuse_secret_key: str = Field()
    langfuse_host: str = Field()

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")


class ChatPrompt(BaseModel):
    role: str
    content: str


class PromptModel(BaseModel):
    prompt: Union[str, list[ChatPrompt]]
    name: str
    version: int
    config: dict
    labels: list[str]
    tags: list[str]
    type: str


def check_langfuse_connection(langfuse: Langfuse):
    langfuse_callback_handler = CallbackHandler()
    try:
        langfuse.auth_check()
        langfuse_callback_handler.auth_check()
    except Exception as e:
        raise typer.Exit(f"Auth check failed. Please check your credentials and config. Error: {e}")


def clean_prompts(prompts: list[PromptModel]) -> list[dict[Any, Any]]:
    return [
        {key: value for key, value in prompt.items() if key in PromptModel.model_fields}
        for prompt in prompts
    ]


def get_list_prompts_from_str(list_arg: str) -> list[str]:
    prompts_list = [p.strip() for p in list_arg.split(",")] if list_arg else []
    print("\nPrompts:", prompts_list if prompts_list else "ALL")
    return prompts_list


def get_prompts(langfuse: Langfuse, prompts: list[str] = []) -> list[dict[str, str]]:
    prompts_client = langfuse.client.prompts
    list_prompts = prompts_client.list(limit=60).data

    prompts_with_names = []
    for prompt in list_prompts:
        if prompt.name in prompts or not prompts:
            prompt_versions = [
                prompts_client.get(prompt_name=prompt.name, version=prompt_version).dict()
                for prompt_version in prompt.versions
            ]
            prompts_with_names.extend(prompt_versions)

    return clean_prompts(prompts_with_names)


def get_prompt_versions(langfuse: Langfuse, prompts: list[str] = []) -> list[dict[str, str]]:
    prompts_client = langfuse.client.prompts
    list_prompts = prompts_client.list(limit=60).data
    return {
        prompt.name: prompt.versions
        for prompt in list_prompts
        if prompt.name in prompts or not prompts
    }


def create_prompt(langfuse: Langfuse, prompt: PromptModel):
    prompts_client = langfuse.client.prompts

    if prompt.type == "text":
        prompt_request = CreatePromptRequest_Text(
            name=prompt.name,
            prompt=prompt.prompt,
            config=prompt.config,
            labels=prompt.labels,
            tags=prompt.tags,
        )
    else:
        prompt_request = CreatePromptRequest_Chat(
            name=prompt.name,
            prompt=[
                ChatMessage(role=chat_prompt.role, content=chat_prompt.content)
                for chat_prompt in prompt.prompt
            ],
            config=prompt.config,
            labels=prompt.labels,
            tags=prompt.tags,
        )
    prompts_client.create(request=prompt_request)


def create_prompts(langfuse: Langfuse, prompts: list[PromptModel]):
    for prompt in prompts:
        create_prompt(langfuse, prompt)


@cli.callback()
def main(ctx: typer.Context):
    ctx.ensure_object(dict)
    langfuse = Langfuse()
    check_langfuse_connection(langfuse)
    ctx.obj["langfuse"] = langfuse


@cli.command(name="export")
def export_prompts(
    output_path: str = typer.Option(None, help="Path to save the exported prompts"),
    prompts_to_export: str = typer.Option(
        "", help="Comma-separated list of prompts to export. e.g. 'prompt1,prompt2'"
    ),
    ctx: typer.Context = typer.Context,
):
    prompts = get_prompts(ctx.obj.get("langfuse"), get_list_prompts_from_str(prompts_to_export))
    with open(output_path, "w", encoding="utf-8") as file:
        if Path(output_path).suffix == ".json":
            json.dump(prompts, file, indent=2, ensure_ascii=False)
        else:
            yaml.dump(prompts, file)


@cli.command(name="import")
def import_prompts(
    input_path: str = typer.Option(None, help="Path to import the exported prompts"),
    prompts_to_import: str = typer.Option(
        "", help="Comma-separated list of prompts to import. e.g. 'prompt1,prompt2'"
    ),
    ctx: typer.Context = typer.Context,
):
    prompts_list = get_list_prompts_from_str(prompts_to_import)
    old_prompts_versions = get_prompt_versions(ctx.obj.get("langfuse"), prompts_list)

    with open(input_path, encoding="utf-8") as file:
        prompts = json.load(file) if Path(input_path).suffix == ".json" else yaml.safe_load(file)

    new_prompts = [
        PromptModel(**prompt)
        for prompt in prompts
        if prompt["name"] in prompts_list or not prompts_list
        if prompt["version"] not in old_prompts_versions.get(prompt["name"], [])
    ]
    print("\n--- NEW PROMPTS ---")
    for prompt in new_prompts:
        print(f"- {prompt.name}, versions: {prompt.version}")
    print("--------------")
    create_prompts(ctx.obj.get("langfuse"), new_prompts)


if __name__ == "__main__":
    settings = Settings(_env_file=".env", _env_file_encoding="utf-8")
    cli()
