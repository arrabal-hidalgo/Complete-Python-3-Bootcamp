import importlib
import os

from langchain_core.language_models import BaseChatModel


class LlmProvider:

    @classmethod
    def create_llm(
        cls, model_name, temperature=0.5, max_tokens=None, model_kwargs={}
    ) -> BaseChatModel:
        model = os.getenv(
            "CHAT_MODEL", "app.infrastructure.ai.llm.chat_open_ai_factory.ChatOpenAIFactory"
        )
        module_name, class_name = model.rsplit(".", 1)
        module = importlib.import_module(module_name)
        chat_model = getattr(module, class_name)
        return chat_model().create(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            model_kwargs=model_kwargs,
        )
