from typing import Any, Union

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langfuse import Langfuse, LangfuseSpan
from langfuse.langchain import CallbackHandler
from langfuse.model import ChatPromptClient, PromptClient
from opentelemetry.util._decorator import _AgnosticContextManager


class LangfuseHandler:
    """
    Creates a connection to Langfuse service
    """

    def __init__(self):
        self.langfuse = Langfuse()
        self.callback_handler = CallbackHandler()

    def create_langfuse_prompt(self, name: str, prompt_text: str, **kwargs):
        self.langfuse.create_prompt(name, prompt_text, type="text", **kwargs)

    def get_prompt_object(self, name: str, label: str = "latest", **kwargs) -> PromptClient:
        return self.langfuse.get_prompt(name, label=label, **kwargs)

    def get_langfuse_prompt(self, name: str, label: str = "latest", **kwargs) -> str:
        prompt: str = self.get_prompt_object(name, label, **kwargs).prompt
        return prompt

    def get_langchain_prompt(
        self, name: str, label: str = "latest", **kwargs
    ) -> Union[ChatPromptTemplate, PromptTemplate]:
        prompt = self.get_prompt_object(name, label, **kwargs)
        args = {**kwargs, "metadata": {"config": {"langfusePrompt": name}}}

        template = prompt.get_langchain_prompt()
        if isinstance(prompt, ChatPromptClient):
            return ChatPromptTemplate(template, **args)
        return PromptTemplate.from_template(template, **args)

    def get_dataset(self, name: str):
        return self.langfuse.get_dataset(name)

    def start_as_current_span(
        self, trace_id: str, trace_name: str
    ) -> Union[_AgnosticContextManager[LangfuseSpan], Any]:
        predefined_trace_id = Langfuse.create_trace_id(seed=trace_id)
        return self.langfuse.start_as_current_span(
            name=trace_name, trace_context={"trace_id": predefined_trace_id}
        )
