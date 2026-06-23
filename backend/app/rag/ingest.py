"""
Run once to load knowledge/northshop_policies.md into pgvector.
Usage: cd backend && uv run python -m app.rag.ingest
"""
import asyncio
from pathlib import Path
import voyageai
from sqlalchemy import text
from app.database import engine
from app.config import settings

CHUNK_SIZE = 500
CHUNK_OVERLAP = 100
POLICIES_PATH = Path(__file__).parents[3] / "knowledge" / "northshop_policies.md"
EMBEDDING_MODEL = "voyage-3-lite"  # 512-dim, free tier

client = voyageai.AsyncClient(api_key=settings.voyage_api_key)


def _chunk(text: str) -> list[str]:
    words = text.split()
    chunks, i = [], 0
    while i < len(words):
        chunks.append(" ".join(words[i : i + CHUNK_SIZE]))
        i += CHUNK_SIZE - CHUNK_OVERLAP
    return chunks


async def ingest():
    content = POLICIES_PATH.read_text()
    chunks = _chunk(content)

    async with engine.begin() as conn:
        await conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.execute(text("DROP TABLE IF EXISTS documents"))
        await conn.execute(text("""
            CREATE TABLE documents (
                id SERIAL PRIMARY KEY,
                content TEXT,
                embedding vector(512),
                metadata JSONB DEFAULT '{}'
            )
        """))

    for i, chunk in enumerate(chunks):
        result = await client.embed([chunk], model=EMBEDDING_MODEL, input_type="document")
        embedding = result.embeddings[0]
        async with engine.begin() as conn:
            await conn.execute(
                text("INSERT INTO documents (content, embedding) VALUES (:c, :e)"),
                {"c": chunk, "e": str(embedding)},
            )
        print(f"Ingested chunk {i + 1}/{len(chunks)}")

    print("Done.")


if __name__ == "__main__":
    asyncio.run(ingest())
