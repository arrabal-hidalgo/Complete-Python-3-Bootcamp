from langfuse import Langfuse
from langfuse.client import DatasetClient
from langfuse.model import TextPromptClient


class LangfuseHandler:
    """
    Creates a connection to Langfuse service
    """

    def __init__(self):
        self.langfuse = Langfuse()

    def create_langfuse_prompt(self, name: str, prompt_text: str, **kwargs):
        self.langfuse.create_prompt(name, prompt_text, type="text", **kwargs)

    def get_prompt_object(self, name: str, label: str = "latest", **kwargs) -> TextPromptClient:
        return self.langfuse.get_prompt(name, label=label, **kwargs)

    def get_langfuse_prompt(self, name: str, label: str = "latest", **kwargs) -> str:
        prompt: str = self.get_prompt_object(name, label, **kwargs).prompt
        return prompt

    def get_dataset(self, name: str) -> DatasetClient:
        return self.langfuse.get_dataset(name)
