from abc import ABC, abstractmethod
from langchain_core.language_models import BaseChatModel
from langchain_core.embeddings import Embeddings


class AIFactory(ABC):
    @abstractmethod
    def create(
        self, model_name, temperature=0.5, max_tokens=None, model_config={}, model_kwargs={}
    ) -> BaseChatModel | Embeddings:
        pass
