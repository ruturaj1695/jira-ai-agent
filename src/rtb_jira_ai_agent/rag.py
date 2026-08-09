from __future__ import annotations

from pathlib import Path

from .config import get_settings


class RAGService:
    """Optional Chroma-backed knowledge store for Jira documentation and metadata."""

    def __init__(self) -> None:
        self._store = None

    def _ensure_store(self):
        if self._store is not None:
            return self._store
        from langchain_chroma import Chroma
        from langchain_openai import OpenAIEmbeddings

        settings = get_settings()
        if not settings.openai_api_key:
            raise RuntimeError("OPENAI_API_KEY is required for RAG embeddings")
        Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
        self._store = Chroma(
            collection_name="jira_knowledge",
            embedding_function=OpenAIEmbeddings(api_key=settings.openai_api_key),
            persist_directory=settings.chroma_persist_directory,
        )
        return self._store

    def add_documents(self, texts: list[str], metadatas: list[dict] | None = None) -> list[str]:
        store = self._ensure_store()
        return store.add_texts(texts=texts, metadatas=metadatas)

    def search(self, query: str, k: int = 4) -> list[dict]:
        store = self._ensure_store()
        return [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in store.similarity_search(query, k=k)
        ]
