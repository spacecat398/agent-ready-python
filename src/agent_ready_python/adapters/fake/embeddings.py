"""Deterministic local embedding provider for tests and composition checks."""

from hashlib import sha256

from agent_ready_python.contracts import EmbeddingResult


class FakeEmbeddingProvider:
    def embed(self, texts: tuple[str, ...]) -> EmbeddingResult:
        if not texts or any(not text.strip() for text in texts):
            raise ValueError("embedding input must contain non-empty text")

        vectors = []
        for text in texts:
            digest = sha256(text.encode()).digest()
            vectors.append(tuple(byte / 255.0 for byte in digest[:8]))
        return EmbeddingResult(
            vectors=tuple(vectors),
            provider="fake",
            model="sha256-8",
        )
