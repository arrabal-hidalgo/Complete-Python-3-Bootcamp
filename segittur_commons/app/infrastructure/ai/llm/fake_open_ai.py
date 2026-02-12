from itertools import cycle
from typing import Any

from langchain_core.language_models import GenericFakeChatModel
from langchain_core.language_models.base import LanguageModelInput
from langchain_core.messages import AIMessage, BaseMessage
from langchain_core.runnables import RunnableConfig
from langchain_openai import ChatOpenAI


class FakeLLM:

    FAKE_MSG = "if you want use a real LLM model you have to set the models config file: MODEL_CONFIG_FILE=segittur_commons/config/models_[env].json, OPENAI_API_KEY=sk-your-llm-api-key"

    CHAT = GenericFakeChatModel(
        messages=cycle(
            [
                AIMessage(
                    content=f"{FAKE_MSG} v1",
                    additional_kwargs={
                        "audio": {
                            "id": "audio_68dc6f2db4c88190a6ea238a373dcfd0",
                            "data": "",
                            "transcript": f"{FAKE_MSG} v1",
                        }
                    },
                ),
                AIMessage(
                    content=f"{FAKE_MSG} v2",
                    additional_kwargs={
                        "audio": {
                            "id": "audio_68dc6f2db4c88190a6ea238a373dcfd0",
                            "data": "",
                            "transcript": f"{FAKE_MSG} v2",
                        }
                    },
                ),
            ]
        )
    )


class FakeOpenAI(ChatOpenAI):

    class Transcription:

        @property
        def text(self) -> str:
            return FakeLLM.FAKE_MSG

    def invoke(
        self,
        input: LanguageModelInput,
        config: RunnableConfig | None = None,
        stop: list[str] | None = None,
        **kwargs: Any,
    ) -> AIMessage:
        return FakeLLM.CHAT.invoke("random")

    def create(self, model, file):
        return self.Transcription()
