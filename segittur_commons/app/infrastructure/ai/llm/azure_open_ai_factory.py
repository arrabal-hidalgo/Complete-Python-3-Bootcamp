import os

from segittur_commons.app.infrastructure.ai.llm.ai_factory import AIFactory

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from langchain_openai import AzureChatOpenAI
from langchain_openai import AzureOpenAIEmbeddings


class AzureOpenAIFactory(AIFactory):

    def create(
        self, model_name, temperature=0.5, max_tokens=None, model_config={}, model_kwargs={}
    ) -> BaseChatModel | Embeddings:
        azure_endpoint = model_config.get("azure_endpoint", os.getenv("AZURE_OPENAI_ENDPOINT"))
        api_key = model_config.get("api_key", os.getenv("AZURE_OPENAI_API_KEY"))
        openai_api_version = model_config.get("openai_api_version", os.getenv("OPENAI_API_VERSION"))
        model_type = model_config.get("type", "chat")
        if "chat" == model_type:
            return AzureChatOpenAI(
                azure_deployment=model_name,
                openai_api_type="azure",
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                api_version=openai_api_version,
                model=model_name,
                temperature=temperature,
                max_tokens=max_tokens,
                timeout=None,
                max_retries=2,
                model_kwargs=model_kwargs,
            )
        elif "embedding" == model_type:
            return AzureOpenAIEmbeddings(
                model=model_name,
                api_key=api_key,
                azure_endpoint=azure_endpoint,
                api_version=openai_api_version,
                max_retries=2,
                model_kwargs=model_kwargs,
            )
        raise ValueError(f"${model_type } model type not supported. Only [chat|embedding]")
