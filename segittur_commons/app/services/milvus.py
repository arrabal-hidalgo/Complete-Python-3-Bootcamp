import os
from typing import Callable, List, Type, Union

from langchain_core.documents import Document
from langchain_milvus import Milvus
from langchain_openai import AzureOpenAIEmbeddings
from langchain_text_splitters.base import TS, TextSplitter
from pymilvus import MilvusClient

DEFAULT_DATABASE = "SEGITTUR_AVC"
DEFAULT_COLLECTION = "general_vectorstore"


class MilvusHandler:
    """
    Creates a connection to Milvus service
    """

    def __init__(
        self,
        uri: str,
        token: str | None = None,
        model_embeddings: str = "text-embedding-3-small",
        **kwargs,
    ):
        self.uri = uri or os.environ["MILVUS_URL"]
        if token is None:
            self.token = os.getenv("MILVUS_TOKEN", "")
        else:
            self.token = token
        self.client = MilvusClient(uri=self.uri, token=self.token, **kwargs)
        self.embeddings_fn = AzureOpenAIEmbeddings(model=model_embeddings)

    def _use_database(self, db_name: str, **kwargs_db):
        if db_name not in self.client.list_databases():
            self.client.create_database(db_name, **kwargs_db)
            print(f"Database '{db_name}' created successfully.")
        self.client.use_database(db_name)

    def _connection_args(self, db_name: str):
        self._use_database(db_name)
        return {"uri": self.uri, "token": self.token, "db_name": db_name}

    def _split_text(
        self,
        texts: Union[list[str], list[Document]],
        text_splitter_fn: Type[TS],
        metadatas: list[dict] = None,
        **kwargs_splitter,
    ) -> list[Document]:
        text_splitter: TextSplitter = text_splitter_fn(**kwargs_splitter)
        if isinstance(texts[0], str):
            splitted_docs = text_splitter.create_documents(texts, metadatas)
        else:  # list[Document]
            splitted_docs = text_splitter.split_documents(texts)
        return splitted_docs

    def create_vector_store_from_texts(
        self,
        texts: Union[list[str], list[Document]],
        metadatas: list[dict] = None,
        collection_name: str = DEFAULT_COLLECTION,
        db_name: str = DEFAULT_DATABASE,
        text_splitter_fn: Type[TS] = None,
        kwargs_splitter: dict = {},
        kwargs_store: dict = {},
    ) -> Milvus:
        if text_splitter_fn:
            documents = self._split_text(texts, text_splitter_fn, metadatas, **kwargs_splitter)
        elif isinstance(texts[0], str):
            _metadatas = (metadatas or [{}]) * len(texts)
            documents = [
                Document(page_content=text, metadata=metadata)
                for text, metadata in zip(texts, _metadatas)
            ]

        return Milvus.from_documents(
            documents,
            self.embeddings_fn,
            collection_name=collection_name,
            connection_args=self._connection_args(db_name),
            auto_id=kwargs_store.pop("auto_id", True),
            # # TODO: Study other kwargs
            # consistency_level="Strong",
            # index_params={"index_type": "FLAT", "metric_type": "L2"},
            # drop_old=False,  # set to True if seeking to drop the collection with that name if it exists
            **kwargs_store,
        )

    def get_vector_store(
        self, collection_name: str = DEFAULT_COLLECTION, db_name: str = DEFAULT_DATABASE
    ) -> Milvus:
        return Milvus(
            embedding_function=self.embeddings_fn,
            collection_name=collection_name,
            connection_args=self._connection_args(db_name),
            index_params=self.client.describe_index(DEFAULT_COLLECTION, "vector"),
        )

    def exists_collection(self, collection_name: str = DEFAULT_COLLECTION):
        return self.client.has_collection(collection_name)

    def remove_collection(self, collection_name: str = DEFAULT_COLLECTION):
        self.client.drop_collection(collection_name)

    def remove_database(self, db_name: str = DEFAULT_DATABASE):
        self._use_database(db_name)
        for collection in self.client.list_collections():
            self.remove_collection(collection)
        self.client.drop_database(db_name)

    @classmethod
    def remove_vectors(self, vector_store: Milvus, **kwargs):
        vector_store.delete(**kwargs)

    def query(
        self,
        query: str,
        search_fun: str = "similarity_search_with_relevance_scores",
        threshold=0.8,
        vector_store: Milvus = None,
        kwargs_search: dict = {},
        kwargs_store: dict = {},
    ) -> list[Document]:
        search_method: Callable[[str, dict], List[tuple[Document, float]]] = getattr(
            vector_store or self.get_vector_store(**kwargs_store), search_fun
        )
        docs_scores = search_method(query, **kwargs_search)
        print(docs_scores)

        return [doc for doc, score in docs_scores if score >= threshold]
