import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import AzureChatOpenAI


class AzureOpenAIFactory:

    def create(cls, model_name, temperature=0.5, max_tokens=None, model_kwargs={}) -> BaseChatModel:
        # FIXME:  Preview models like gpt-4o-mini-audio-preview are not deployed to Europe
        if model_name == "gpt-4o-mini-audio-preview":
            azure_endpoint = os.getenv("AZURE_OPENAI_PREVIEW_ENDPOINT")
            openai_api_key = os.getenv("AZURE_OPENAI_PREVIEW_API_KEY")
            openai_api_version = os.getenv("OPENAI_PREVIEW_API_VERSION")
        else:
            azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
            openai_api_key = os.getenv("AZURE_OPENAI_API_KEY")
            openai_api_version = os.getenv("OPENAI_API_VERSION")
        return AzureChatOpenAI(
            deployment_name=model_name,
            azure_deployment=model_name,
            openai_api_type="azure",
            openai_api_key=openai_api_key,
            azure_endpoint=azure_endpoint,
            openai_api_version=openai_api_version,
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=None,
            max_retries=2,
            model_kwargs=model_kwargs,
        )
