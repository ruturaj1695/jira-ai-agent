from pathlib import Path

from langchain_text_splitters import RecursiveCharacterTextSplitter

from .rag import RAGService


def ingest_text_file(path: str) -> int:
    """Chunk a text/markdown document and persist embeddings to Chroma."""
    source = Path(path)
    text = source.read_text(encoding="utf-8")
    splitter = RecursiveCharacterTextSplitter(chunk_size=800, chunk_overlap=120)
    chunks = splitter.split_text(text)
    metadatas = [{"source": str(source), "chunk": index} for index, _ in enumerate(chunks)]
    RAGService().add_documents(chunks, metadatas)
    return len(chunks)
