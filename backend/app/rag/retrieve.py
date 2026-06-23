import voyageai
from sqlalchemy import text
from app.database import engine
from app.config import settings

EMBEDDING_MODEL = "voyage-3-lite"
TOP_K = 3

client = voyageai.AsyncClient(api_key=settings.voyage_api_key)


async def retrieve_context(query: str) -> str:
    result = await client.embed([query], model=EMBEDDING_MODEL, input_type="query")
    embedding = result.embeddings[0]

    async with engine.connect() as conn:
        rows = await conn.execute(
            text("""
                SELECT content
                FROM documents
                ORDER BY embedding <-> CAST(:e AS vector)
                LIMIT :k
            """),
            {"e": str(embedding), "k": TOP_K},
        )

    return "\n\n---\n\n".join(row[0] for row in rows)
