import os
from typing import Dict, List, Type

from langchain_core.documents import Document
from langchain_milvus import Milvus
from langchain_text_splitters.base import TS, TextSplitter
from pymilvus import AsyncMilvusClient, MilvusClient

from segittur_commons.app.infrastructure.ai.llm.llm_provider import LlmProvider


class MilvusHandler:
    """
    Creates a connection to Milvus service
    """

    def __init__(
        self,
        uri: str = None,
        token: str = None,
        db: str = None,
        collection: str = None,
        model_embeddings: str = "embedding-mini",
        kwargs_model: Dict = {},
        **kwargs_store,
    ):
        self.uri = uri or os.environ["MILVUS_URL"]
        self.token = token or os.getenv("MILVUS_TOKEN", "")
        self.db = db or os.getenv("MILVUS_DATABASE", "SEGITTUR_AVC")
        self.collection = collection or os.getenv("MILVUS_COLLECTION", "general_vectorstore")

        self.embeddings_fn = LlmProvider.create_llm(model=model_embeddings, **kwargs_model)

        self.vector_store = Milvus(
            embedding_function=self.embeddings_fn,
            collection_name=self.collection,
            connection_args={"uri": self.uri, "token": self.token, "db_name": self.db},
            auto_id=kwargs_store.pop("auto_id", True),
            **kwargs_store,
        )

    @property
    def client(self) -> MilvusClient:
        return self.vector_store.client

    @property
    def aclient(self) -> AsyncMilvusClient:
        return self.vector_store.aclient

    def _split_text(
        self,
        texts: List[str] | List[Document],
        text_splitter_fn: Type[TS],
        metadatas: List[Dict] = None,
        **kwargs_splitter,
    ) -> List[Document]:
        text_splitter: TextSplitter = text_splitter_fn(**kwargs_splitter)
        docs: List[Document] = (
            text_splitter.create_documents(texts, metadatas)
            if isinstance(texts[0], str)
            else text_splitter.split_documents(texts)
        )
        return docs

    def _prepare_documents(
        self,
        texts: List[str] | List[Document],
        metadatas: List[Dict] = None,
        text_splitter_fn: Type[TS] = None,
        **kwargs_splitter,
    ) -> List[Document]:
        """
        Converts a list of texts or Documents into a list of Documents,
        optionally splitting them.

        Args:
            texts: A list of strings or LangChain Document objects.
            metadatas: Optional list of metadatas. Only used if `texts` is
                a list of strings and no splitter is provided.
            text_splitter_fn: Optional text splitter class from LangChain.
            kwargs_splitter: Optional keyword arguments for the text splitter.

        Returns:
            A list of LangChain Document objects.
        """
        if not texts:
            return []

        # If texts are in the desired format (Document objects)
        # and no splitting is required, we can return them directly.
        if not text_splitter_fn and isinstance(texts[0], Document):
            return texts

        # If a splitter is provided, delegate the processing.
        if text_splitter_fn:
            return self._split_text(texts, text_splitter_fn, metadatas, **kwargs_splitter)

        # Just a list of strings that needs conversion to Document objects.
        _metadatas = (metadatas or [{}]) * len(texts)
        return [
            Document(page_content=text, metadata=metadata)
            for text, metadata in zip(texts, _metadatas)
        ]

    def add_documents(
        self,
        texts: List[str] | List[Document],
        metadatas: List[Dict] = None,
        text_splitter_fn: Type[TS] = None,
        **kwargs_splitter,
    ) -> List[str]:
        """
        Adds documents to an existing collection in Milvus.

        If the input `texts` are strings, they will be converted to
        LangChain Document objects. If a `text_splitter_fn` is provided,
        the documents will be split before being added.

        Args:
            texts: A list of strings or LangChain Document objects to add.
            metadatas: Optional list of metadatas for the texts. Only used if
                `texts` is a list of strings.
            collection_name: The name of the collection to add documents to.
            db_name: The name of the database where the collection resides.
            text_splitter_fn: Optional text splitter class from LangChain.
            kwargs_splitter: Optional keyword arguments for the text splitter.

        Returns:
            A list of IDs of the inserted documents.
        """
        documents = self._prepare_documents(texts, metadatas, text_splitter_fn, **kwargs_splitter)
        if not documents:
            return []
        docs: List[str] = self.vector_store.add_documents(documents)
        return docs

    async def aadd_documents(
        self,
        texts: List[str] | List[Document],
        metadatas: List[Dict] = None,
        text_splitter_fn: Type[TS] = None,
        **kwargs_splitter,
    ) -> List[str]:
        """
        Adds documents to an existing collection in Milvus asynchronously.

        If the input `texts` are strings, they will be converted to
        LangChain Document objects. If a `text_splitter_fn` is provided,
        the documents will be split before being added.

        Args:
            texts: A list of strings or LangChain Document objects to add.
            metadatas: Optional list of metadatas for the texts. Only used if
                `texts` is a list of strings.
            collection_name: The name of the collection to add documents to.
            db_name: The name of the database where the collection resides.
            text_splitter_fn: Optional text splitter class from LangChain.
            kwargs_splitter: Optional keyword arguments for the text splitter.

        Returns:
            A list of IDs of the inserted documents.
        """
        documents = self._prepare_documents(texts, metadatas, text_splitter_fn, **kwargs_splitter)
        if not documents:
            return []
        docs: List[str] = await self.vector_store.aadd_documents(documents)
        return docs

    def remove_documents(self, **kwargs_delete):
        if not self.vector_store.delete(**kwargs_delete):
            raise Exception(f"Error deleting documents ({kwargs_delete})")

    async def aremove_documents(self, **kwargs_delete):
        if not await self.vector_store.adelete(**kwargs_delete):
            raise Exception(f"Error deleting documents ({kwargs_delete})")

    def get_records(self, offset: int = 0, limit: int = 10, **kwargs) -> List[Dict]:
        records: List[Dict] = self.vector_store.client.query(
            self.collection, offset=offset, limit=limit, **kwargs
        )
        return records

    async def aget_records_with_retry(
        self, offset: int = 0, limit: int = 10, retries: int = 1, **kwargs
    ):
        if retries == 0:
            raise Exception(f"Information not found {kwargs}")
        records: dict = self.aget_records(self.collection, offset=offset, limit=limit, **kwargs)
        if records is None or len(records) == 0:
            sleep(0.1)
            return await self.aget_records_with_retry(
                offset=offset, limit=limit, retries=retries - 1
            )
        return records

    async def aget_records(self, offset: int = 0, limit: int = 10, **kwargs) -> List[Dict]:
        records: List[Dict] = await self.vector_store.aclient.query(
            self.collection, offset=offset, limit=limit, **kwargs
        )
        return records

    def search(self, query: str, search_type: str, **kwargs_search) -> List[Document]:
        docs: List[Document] = self.vector_store.search(query, search_type, **kwargs_search)
        return docs

    async def asearch(self, query: str, search_type: str, **kwargs_search) -> List[Document]:
        docs: List[Document] = await self.vector_store.asearch(query, search_type, **kwargs_search)
        return docs
