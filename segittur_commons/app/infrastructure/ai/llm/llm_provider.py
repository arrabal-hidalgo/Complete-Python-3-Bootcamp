import os
import re
from importlib import resources
import json
from typing import Any, Dict

from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings

from segittur_commons.app.infrastructure.ai.llm.ai_factory import AIFactory
from segittur_commons.app.infrastructure.ai.llm.azure_open_ai_factory import AzureOpenAIFactory
from segittur_commons.app.infrastructure.ai.llm.chat_open_ai_factory import ChatOpenAIFactory
from segittur_commons.app.infrastructure.ai.llm.fake_open_ai_factory import FakeOpenAIFactory


class LlmProvider:

    PROVIDERS = {
        "azure-models": AzureOpenAIFactory(),
        "openai-models": ChatOpenAIFactory(),
        "fake-models": FakeOpenAIFactory(),
    }

    _config: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def __open_config(cls) -> str:
        config = os.getenv("MODEL_CONFIG_FILE")
        if config:
            with open(config, "r") as f:
                config_str = f.read()
        else:
            with resources.files("segittur_commons.config").joinpath("models.json").open("r") as f:
                config_str = f.read()
        return config_str

    @classmethod
    def _load_config(cls) -> Dict[str, Any]:

        if cls._config is None or cls._config == {}:
            config_str = cls.__open_config()

            def replace_env_var(match):
                var_name = match.group(1)
                return os.getenv(var_name, "")

            config_str = re.sub(r"\$\{(\w+)\}", replace_env_var, config_str)
            cls._config = json.loads(config_str)

        return cls._config

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
