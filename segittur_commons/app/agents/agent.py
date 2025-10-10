from abc import ABC
from typing import List

from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.prompts import (
    BasePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder,
    PromptTemplate,
)
from langchain_core.runnables import RunnableSequence

from segittur_commons.app.entities.graph import PromptType
from segittur_commons.app.services.langfuse_service import LangfuseHandler


class Agent(ABC):
    prompt_name: PromptType
    langfuse_handler = LangfuseHandler()
    user_input_var: str = "user_input"
    messages_var: str = "messages"

    def __init__(self, llm: BaseChatModel, **kwargs_prompt):
        self.llm = llm
        self.prompt = self.langfuse_handler.get_langfuse_prompt(self.prompt_name, **kwargs_prompt)
        self.template = self._create_template()
        self.chain = self._create_chain()

    @classmethod
    def _get_prompt_vars(cls) -> List[str]:
        return [getattr(cls, attr) for attr in cls.__dict__ if attr.endswith("_var")]

    @classmethod
    def human_template(cls) -> str:
        if not (args := cls._get_prompt_vars()):
            template = f"{{{cls.user_input_var}}}"
        else:
            vars: list[str] = (
                [cls.user_input_var] + args if cls.user_input_var not in args else args
            )
            template = "\n\n".join(
                [f"**{arg.replace('_', ' ').capitalize()}**\n```\n{{{arg}}}\n```" for arg in vars]
            )
        return template

    @property
    def messages_placeholder(self) -> MessagesPlaceholder:
        return MessagesPlaceholder(variable_name=self.messages_var)

    def create_simple_template(self) -> PromptTemplate:
        return PromptTemplate.from_template(self.prompt)

    def create_messages_template(
        self,
        system_prompt: str | None = None,
        human_prompt: str | None = None,
        extra_messages: list = [],
    ) -> ChatPromptTemplate:
        human_message = (
            [] if human_prompt == "" else [("human", human_prompt or self.human_template())]
        )
        return ChatPromptTemplate.from_messages(
            [("system", system_prompt or self.prompt), *human_message, *extra_messages]
        )

    def _create_template(self) -> BasePromptTemplate:
        return self.create_messages_template()

    def _create_chain(self) -> RunnableSequence:
        return self.template | self.llm
