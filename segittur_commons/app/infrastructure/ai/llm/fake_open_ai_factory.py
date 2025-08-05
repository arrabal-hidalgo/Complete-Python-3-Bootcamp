import os

from langchain_core.language_models import BaseChatModel

from segittur_commons.app.infrastructure.ai.llm.fake_open_ai import FakeOpenAI


class FakeOpenAIFactory:

    def create(
        self, model_name, temperature=0.5, max_tokens=None, model_kwargs={}
    ) -> BaseChatModel:
        return FakeOpenAI(
            model=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            timeout=None,
            max_retries=2,
            api_key=os.getenv("OPENAI_API_KEY"),
            model_kwargs=model_kwargs,
        )
