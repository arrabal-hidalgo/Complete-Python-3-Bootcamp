import os

from langchain_core.language_models import BaseChatModel
from langchain_openai import ChatOpenAI
from pydantic import Field

from segittur_commons.app.infrastructure.ai.llm.ai_factory import AIFactory


class ChatOpenAIFactory(AIFactory):

    def create(
        self,
        model_name,
        temperature=0.5,
        max_tokens: int | None = Field(default=None),
        model_config={},
        model_kwargs={},
    ) -> BaseChatModel:
        api_key = model_config.get("api_key", os.getenv("OPENAI_API_KEY"))
        return ChatOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,  # type: ignore[call-arg]
            timeout=None,
            max_retries=2,
            api_key=api_key,
            model_kwargs=model_kwargs,
        )
