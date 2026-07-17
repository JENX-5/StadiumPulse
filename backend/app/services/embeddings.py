"""
Embedding generation for Tournament Memory.

`agents/memory.py`'s docstring documents that "the agent that writes/queries
[the pgvector embedding column] ... is explicitly a future module" -- this is
that module, kept intentionally small.

Tries the configured provider's real embedding model first (currently only
Gemini's is wired, since `google-genai` is already a project dependency for
`GeminiLLMClient`); falls back to a deterministic, dependency-free hashed
embedding if no provider is configured, the call fails, or the returned
vector's dimension doesn't match the `tournament_memory.embedding` column.
This mirrors the same "LLM unavailable -> deterministic fallback" contract
every agent in `agents/implementations/` already follows: an embedding
failure must never block or crash incident creation.
"""

from __future__ import annotations

import hashlib
import math

import structlog

from app.core.config import Settings
from app.db.models.tournament_memory import EMBEDDING_DIMENSION

logger = structlog.get_logger(__name__)


def _deterministic_embedding(text: str, dimension: int = EMBEDDING_DIMENSION) -> list[float]:
    """A dependency-free, hashed bag-of-words embedding.

    Not semantically rich the way a real embedding model's output is, but it
    IS deterministic, unit-normalized, and dimensionally correct -- enough to
    exercise pgvector's cosine-similarity index end-to-end (near-duplicate
    incident text lands in the same neighborhood) without depending on
    network access or any provider being configured. Used only as a fallback.
    """
    tokens = text.lower().split()
    vector = [0.0] * dimension
    if not tokens:
        return vector
    for token in tokens:
        digest = hashlib.sha256(token.encode("utf-8")).digest()
        index = int.from_bytes(digest[:4], "big") % dimension
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign
    norm = math.sqrt(sum(v * v for v in vector))
    if norm == 0:
        return vector
    return [v / norm for v in vector]


async def generate_embedding(text: str, settings: Settings) -> list[float]:
    """Best-effort real embedding; deterministic fallback on any failure."""
    if settings.llm_provider == "gemini" and settings.gemini_api_key:
        try:
            return await _gemini_embedding(text, settings)
        except Exception as exc:  # noqa: BLE001 - any provider/SDK failure degrades gracefully
            logger.warning("embedding_generation_failed_using_fallback", error=str(exc))
    return _deterministic_embedding(text)


async def _gemini_embedding(text: str, settings: Settings) -> list[float]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.gemini_api_key)
    response = await client.aio.models.embed_content(
        model=settings.gemini_embedding_model,
        contents=text,
        config=types.EmbedContentConfig(output_dimensionality=EMBEDDING_DIMENSION),
    )
    values = list(response.embeddings[0].values)
    if len(values) != EMBEDDING_DIMENSION:
        raise ValueError(
            f"Gemini returned a {len(values)}-dim embedding, expected {EMBEDDING_DIMENSION}"
        )
    return values
