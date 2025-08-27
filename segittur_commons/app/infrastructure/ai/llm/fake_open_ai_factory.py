from langchain_core.language_models import BaseChatModel

from segittur_commons.app.infrastructure.ai.llm.ai_factory import AIFactory
from segittur_commons.app.infrastructure.ai.llm.fake_open_ai import FakeOpenAI


class FakeOpenAIFactory(AIFactory):

    def create(
        self, model_name, temperature=0.5, max_tokens=None, model_config={}, model_kwargs={}
    ) -> BaseChatModel:
        api_key = model_config.get("api_key", "fake")
        return FakeOpenAI(
            model=model_name,
            temperature=temperature,
            timeout=None,
            max_retries=2,
            api_key=api_key,
            model_kwargs=model_kwargs,
        )
