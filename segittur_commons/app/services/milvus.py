import os
from typing import List, Type, cast

from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_milvus import Milvus
from langchain_text_splitters.base import TS, TextSplitter

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
        kwargs_model: dict = {},
        **kwargs_store,
    ):
        self.uri = uri or os.environ["MILVUS_URL"]
        self.token = token or os.getenv("MILVUS_TOKEN", "")
        self.db = db or os.getenv("MILVUS_DATABASE", "SEGITTUR_AVC")
        self.collection = collection or os.getenv("MILVUS_COLLECTION", "general_vectorstore")
        self.embeddings_fn = cast(
            Embeddings, LlmProvider.create_llm(model=model_embeddings, **kwargs_model)
        )

        self.vector_store = Milvus(
            embedding_function=self.embeddings_fn,
            collection_name=self.collection,
            connection_args={"uri": self.uri, "token": self.token, "db_name": self.db},
            auto_id=kwargs_store.pop("auto_id", True),
            **kwargs_store,
        )

    @property
    def client(self):
        return self.vector_store.client

    @property
    def aclient(self):
        return self.vector_store.aclient

    def _split_text(
        self,
        texts: List[str] | List[Document],
        text_splitter_fn: Type[TS],
        metadatas: List[dict] = None,
        **kwargs_splitter,
    ) -> List[Document]:
        text_splitter: TextSplitter = text_splitter_fn(**kwargs_splitter)
        docs: List[Document] = (
            text_splitter.create_documents(cast(List[str], texts), metadatas)
            if isinstance(texts[0], str)
            else text_splitter.split_documents(cast(List[Document], texts))
        )
        return docs

    def _prepare_documents(
        self,
        texts: List[str] | List[Document] = [],
        metadatas: List[dict] = None,
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
            return cast(List[Document], texts)

        # If a splitter is provided, delegate the processing.
        if text_splitter_fn:
            return self._split_text(texts, text_splitter_fn, metadatas, **kwargs_splitter)

        # Just a list of strings that needs conversion to Document objects.
        _metadatas = (metadatas or [{}]) * len(texts)
        return [
            Document(page_content=text, metadata=metadata)
            for text, metadata in zip(cast(List[str], texts), _metadatas)
        ]

    async def aadd_documents(
        self,
        texts: List[str] | List[Document] = [],
        metadatas: List[dict] = None,
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

        docs_ids: List[str] = await self.vector_store.aadd_documents(documents)
        return docs_ids

    async def aremove_documents(self, **kwargs_delete):
        if not await self.vector_store.adelete(**kwargs_delete):
            raise Exception(f"Error deleting documents ({kwargs_delete})")

    async def aget_records(self, limit: int = 10, **kwargs):
        return await self.vector_store.aclient.query(self.collection, limit=limit, **kwargs)

    async def asearch_with_scores(
        self, query: str, score_threshold=0.8, **kwargs_search
    ) -> List[Document]:
        docs_scores: List[tuple[Document, float]] = await self.vector_store.asearch(
            query,
            search_type="similarity_score_threshold",
            score_threshold=score_threshold,
            **kwargs_search,
        )
        return [doc for doc, _ in docs_scores]
