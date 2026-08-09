from __future__ import annotations

from pathlib import Path

from .config import get_settings


class RAGService:
    """Chroma-backed knowledge store using the configured Ollama embedding model."""

    def __init__(self) -> None:
        self._store = None

    def available(self) -> bool:
        settings = get_settings()
        if settings.llm_provider.lower() == "ollama":
            return bool(settings.ollama_base_url)
        return bool(settings.openai_api_key)

    def _ensure_store(self):
        if self._store is not None:
            return self._store
        if not self.available():
            raise RuntimeError("RAG provider is not configured")

        from langchain_chroma import Chroma

        settings = get_settings()
        if settings.llm_provider.lower() == "ollama":
            from langchain_ollama import OllamaEmbeddings

            embeddings = OllamaEmbeddings(
                model=settings.ollama_embedding_model,
                base_url=settings.ollama_base_url,
            )
        else:
            from langchain_openai import OpenAIEmbeddings

            embeddings = OpenAIEmbeddings(api_key=settings.openai_api_key)

        Path(settings.chroma_persist_directory).mkdir(parents=True, exist_ok=True)
        self._store = Chroma(
            collection_name="jira_knowledge",
            embedding_function=embeddings,
            persist_directory=settings.chroma_persist_directory,
        )
        return self._store

    def add_documents(self, texts: list[str], metadatas: list[dict] | None = None) -> list[str]:
        if not texts:
            return []
        return self._ensure_store().add_texts(texts=texts, metadatas=metadatas)

    def search(self, query: str, k: int = 4) -> list[dict]:
        if not query.strip() or not self.available():
            return []
        store = self._ensure_store()
        return [
            {"content": doc.page_content, "metadata": doc.metadata}
            for doc in store.similarity_search(query, k=k)
        ]
