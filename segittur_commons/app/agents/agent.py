from abc import ABC
from typing import Union

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.runnables import RunnableSerializable

from segittur_commons.app.entities.graph import PromptType
from segittur_commons.app.services.langfuse_service import (
    LangfuseHandler,
    get_langfuse_handler,
)


class Agent(ABC):
    prompt_name: PromptType
    user_input_var: str = "user_input"
    prompt_prefix: str = "agents"

    def __init__(self, llm: BaseChatModel, **kwargs_prompt):
        self.llm = llm
        self.langfuse_handler = get_langfuse_handler()
        if llm is None:
            return
        self.template = self.langfuse_handler.get_langchain_prompt(
            f"[{self.prompt_prefix}]{self.prompt_name}", **kwargs_prompt
        )
        self.chain = self._create_chain()

    @staticmethod
    def add_vars_to_string(input: dict) -> dict:
        if variables := input.get("variables"):
            input["variables"] = "\n\n".join(
                [
                    f"**{key.replace('_', ' ').capitalize()}**\n```\n{value}\n```"
                    for key, value in variables.items()
                ]
            )
        return input

    def _create_partial_chain(
        self,
    ) -> Union[RunnableSerializable, ChatPromptTemplate, PromptTemplate]:
        if "variables" in self.template.input_variables:
            return Agent.add_vars_to_string | self.template
        return self.template

    def _create_chain(self) -> RunnableSerializable:
        return self._create_partial_chain() | self.llm
