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
        texts: Union[List[str], List[Document]],
        text_splitter_fn: Type[TS],
        metadatas: List[dict] = None,
        **kwargs_splitter,
    ) -> List[Document]:
        text_splitter: TextSplitter = text_splitter_fn(**kwargs_splitter)
        if isinstance(texts[0], str):
            splitted_docs = text_splitter.create_documents(texts, metadatas)
        else:  # List[Document]
            splitted_docs = text_splitter.split_documents(texts)
        return splitted_docs

    def _prepare_documents(
        self,
        texts: Union[List[str], List[Document]] = [],
        metadatas: List[dict] = None,
        text_splitter_fn: Type[TS] = None,
        kwargs_splitter: dict = None,
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
            kwargs_splitter = kwargs_splitter or {}
            return self._split_text(texts, text_splitter_fn, metadatas, **kwargs_splitter)

        # Just a list of strings that needs conversion to Document objects.
        _metadatas = (metadatas or [{}]) * len(texts)
        return [
            Document(page_content=text, metadata=metadata)
            for text, metadata in zip(texts, _metadatas)
        ]

    def create_vector_store_from_texts(
        self,
        texts: Union[List[str], List[Document]] = [],
        metadatas: List[dict] = None,
        collection_name: str = DEFAULT_COLLECTION,
        db_name: str = DEFAULT_DATABASE,
        text_splitter_fn: Type[TS] = None,
        kwargs_splitter: dict = {},
        kwargs_store: dict = {},
    ) -> Milvus:
        documents = self._prepare_documents(
            texts=texts,
            metadatas=metadatas,
            text_splitter_fn=text_splitter_fn,
            kwargs_splitter=kwargs_splitter,
        )
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

    def add_documents(
        self,
        texts: Union[List[str], List[Document]] = [],
        metadatas: List[dict] = None,
        collection_name: str = DEFAULT_COLLECTION,
        db_name: str = DEFAULT_DATABASE,
        text_splitter_fn: Type[TS] = None,
        kwargs_splitter: dict = {},
        **kwargs_store: dict,
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
        documents = self._prepare_documents(
            texts=texts,
            metadatas=metadatas,
            text_splitter_fn=text_splitter_fn,
            kwargs_splitter=kwargs_splitter,
        )
        if not documents:
            return []

        vector_store = self.get_vector_store(
            collection_name=collection_name, db_name=db_name, **kwargs_store
        )
        return vector_store.add_documents(documents)

    def get_vector_store(
        self,
        collection_name: str = DEFAULT_COLLECTION,
        db_name: str = DEFAULT_DATABASE,
        **kwargs_store: dict,
    ) -> Milvus:
        return Milvus(
            embedding_function=self.embeddings_fn,
            collection_name=collection_name,
            connection_args=self._connection_args(db_name),
            index_params=self.client.describe_index(DEFAULT_COLLECTION, "vector"),
            **kwargs_store,
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
    ) -> List[Document]:
        search_method: Callable[[str, dict], List[tuple[Document, float]]] = getattr(
            vector_store or self.get_vector_store(**kwargs_store), search_fun
        )
        docs_scores = search_method(query, **kwargs_search)
        print(docs_scores)

        return [doc for doc, score in docs_scores if score >= threshold]
