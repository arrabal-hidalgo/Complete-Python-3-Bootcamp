from typing import Any

from langchain_core.embeddings import Embeddings
from langchain_core.language_models import BaseChatModel

from segittur_commons.app.infrastructure.ai.llm.ai_factory import AIFactory
from segittur_commons.app.infrastructure.ai.llm.azure_open_ai_factory import (
    AzureOpenAIFactory,
)
from segittur_commons.app.infrastructure.ai.llm.chat_open_ai_factory import (
    ChatOpenAIFactory,
)
from segittur_commons.app.infrastructure.ai.llm.fake_open_ai_factory import (
    FakeOpenAIFactory,
)
from segittur_commons.config.global_settings import SettingGlobal


class LlmProvider(SettingGlobal):
    default_config_file = "models.json"
    config_file_var_env = "MODEL_CONFIG_FILE"

    PROVIDERS = {
        "azure-models": AzureOpenAIFactory(),
        "openai-models": ChatOpenAIFactory(),
        "fake-models": FakeOpenAIFactory(),
    }

    @classmethod
    def get_model_config(cls, model_name: str) -> Any:
        config = cls._load_config()
        model_configs = config.get("models", {})
        return model_configs.get(
            model_name,
            config.get(
                "default_model", {"name": "fake", "provider": "fake-models", "config": "default"}
            ),
        )

    @classmethod
    def create_llm(
        cls, model, temperature=0.5, max_tokens=None, model_kwargs={}
    ) -> BaseChatModel | Embeddings:
        config = cls._load_config()
        model_config = cls.get_model_config(model)
        provider_name = model_config.get("provider", "fake-models")
        model_name = model_config.get("name", "fake")
        model_provider: AIFactory = cls.PROVIDERS.get(provider_name, FakeOpenAIFactory())

        provider_info = config["providers"].get(provider_name)
        if not provider_info:
            raise ValueError(f"Provider '{provider_name}' not found in configuration.")

        config_name = model_config.get("config", "default")

        provider_config_params = provider_info["configs"].get(config_name, {})

        return model_provider.create(
            model_name=model_name,
            temperature=temperature,
            max_tokens=max_tokens,
            model_config=provider_config_params,
            model_kwargs=model_kwargs,
        )
