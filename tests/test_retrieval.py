import pytest

from agent_ready_python.contracts import EmbeddingResult
from agent_ready_python.features.documents import Document, DocumentSettings, TextChunker
from agent_ready_python.features.retrieval import KeywordRetriever
from agent_ready_python.features.retrieval.semantic import SemanticRetriever


def chunks_for(text: str, chunk_size: int = 50) -> tuple:
    document = Document.from_text("source.txt", text)
    return TextChunker(
        DocumentSettings(chunk_size=chunk_size, chunk_overlap=0)
    ).split(document)


def test_keyword_retrieval_ranks_overlap() -> None:
    chunks = chunks_for(
        "Python modules are reusable.\n" + "RAG retrieves documents.",
        chunk_size=100,
    )
    retriever = KeywordRetriever(chunks)

    matches = retriever.search("RAG documents", top_k=1)

    assert len(matches) == 1
    assert "RAG retrieves documents" in matches[0].chunk.text
    assert matches[0].score == 1.0


@pytest.mark.parametrize("top_k", [0, -1, 21, True, 1.5])
def test_top_k_is_bounded(top_k: object) -> None:
    retriever = KeywordRetriever(chunks_for("searchable text"))

    with pytest.raises(ValueError, match="top_k"):
        retriever.search("searchable", top_k=top_k)  # type: ignore[arg-type]


class FixedEmbeddingProvider:
    def __init__(self) -> None:
        self.calls = 0

    def embed(self, texts: tuple[str, ...]) -> EmbeddingResult:
        self.calls += 1
        vectors = tuple(
            (1.0, 0.0) if "alpha" in text else (0.0, 1.0)
            for text in texts
        )
        return EmbeddingResult(vectors=vectors, provider="fixed", model="fixed")


def test_semantic_retrieval_depends_only_on_embedding_contract() -> None:
    chunks = chunks_for("alpha concept.\n" + "beta concept.", chunk_size=50)
    provider = FixedEmbeddingProvider()
    retriever = SemanticRetriever(chunks, provider)

    matches = retriever.search("alpha", top_k=1)

    assert matches[0].score == 1.0
    assert provider.calls == 2


class WrongCountProvider:
    def embed(self, texts: tuple[str, ...]) -> EmbeddingResult:
        return EmbeddingResult(vectors=((1.0,),), provider="wrong", model="wrong")


def test_semantic_index_rejects_wrong_vector_count() -> None:
    chunks = chunks_for("a" * 100, chunk_size=50)

    with pytest.raises(ValueError, match="vector count"):
        SemanticRetriever(chunks, WrongCountProvider())
