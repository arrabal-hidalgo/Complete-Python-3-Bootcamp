from itertools import cycle
from typing import Any, Optional

from langchain_core.language_models import GenericFakeChatModel
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI


class FakeLLM:

    FAKE_MSG = """if you want use a real LLM model you have to set the below environment variables:
                    CHAT_MODEL=segittur_commons.app.infrastructure.ai.llm.chat_open_ai_factory.ChatOpenAIFactory
                    OPENAI_API_KEY=sk-your-llm-api-key
                """

    CHAT = GenericFakeChatModel(
        messages=cycle([AIMessage(content=f"{FAKE_MSG} v1"), AIMessage(content=f"{FAKE_MSG} v2")])
    )


class FakeOpenAI(ChatOpenAI):

    def invoke(
        self,
        input: LanguageModelInput,
        config: Optional[RunnableConfig] = None,
        stop: Optional[list[str]] = None,
        **kwargs: Any,
    ) -> BaseMessage:
        return FakeLLM.CHAT.invoke("random")
