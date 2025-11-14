from abc import ABC, abstractmethod
from typing import Any, Generic, TypeVar

from langchain_core.runnables import RunnableSerializable
from pydantic import BaseModel

from segittur_commons.app.agents.agent import Agent
from segittur_commons.app.entities.graph import NodeType
from segittur_commons.app.services.llm_model import load_llm_model

TAgent = TypeVar("TAgent", bound=Agent)


class Node(ABC, Generic[TAgent]):
    name: NodeType
    agent_class: type[TAgent]

    def __init__(self, model: str, model_params: dict = {}, agent_params: dict = {}):
        self.model: str = model
        self.llm = self._get_llm(self.model, **model_params)
        self.agent: TAgent = self.agent_class(self.llm, **agent_params)

    @property
    def chain(self) -> RunnableSerializable:
        return self.agent.chain

    def _get_llm(self, model: str, **model_params) -> Any:
        return load_llm_model(model, **model_params)

    def get_router(self, state: BaseModel) -> NodeType:
        raise NotImplementedError

    def get_path(self, state: BaseModel) -> str:
        return self.get_router(state).value  # type: ignore[no-any-return]

    @abstractmethod
    def call(self, state: BaseModel):
        raise NotImplementedError
