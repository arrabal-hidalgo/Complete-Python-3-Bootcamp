import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI


class ChatOpenAIFactory:

    def create(cls, model_name, temperature=0.5, max_tokens=None, model_kwargs={}) -> BaseChatModel:
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=None,
            max_retries=2,
            api_key=os.getenv("OPENAI_API_KEY"),
            model_kwargs=model_kwargs,
        )
