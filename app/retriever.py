# app/retriever.py

from __future__ import annotations

from typing import List, Dict

import httpx

from tenacity import retry, wait_exponential_jitter, stop_after_attempt

import chromadb

from chromadb.config import Settings as ChromaSettings

from .settings import settings

OPENAI_API_KEY = settings.OPENAI_API_KEY

EMBED_MODEL = settings.EMBED_MODEL

HEADERS = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}

@retry(wait=wait_exponential_jitter(initial=0.5, max=8), stop=stop_after_attempt(6))

async def embed_query(text: str) -> list[float]:

    payload = {"model": EMBED_MODEL, "input": [text]}

    async with httpx.AsyncClient(timeout=60) as client:

        r = await client.post("https://api.openai.com/v1/embeddings", headers=HEADERS, json=payload)

        r.raise_for_status()

        data = r.json()

        return data["data"][0]["embedding"]

class RAG:

    def __init__(self):

        self.client = chromadb.PersistentClient(

            path=settings.CHROMA_DIR,

            settings=ChromaSettings(anonymized_telemetry=False),

        )

        self.coll = self.client.get_or_create_collection("docs", metadata={"hnsw:space": "cosine"})

    async def retrieve(self, query: str, k: int = 4) -> List[Dict]:

        q_emb = await embed_query(query)

        # Request more results to filter out tiny fragments and prefer larger chunks
        out = self.coll.query(query_embeddings=[q_emb], n_results=min(k * 20, 100), include=["documents","metadatas","distances"])  # type: ignore

        candidates = []

        for i in range(len(out["ids"][0])):

            text = out["documents"][0][i]

            # Filter out very small chunks (less than 200 chars) - likely fragments

            if len(text.strip()) < 200:

                continue

            candidates.append({

                "id": out["ids"][0][i],

                "text": text,

                "metadata": out["metadatas"][0][i],

                "score": 1 - out["distances"][0][i],  # cosine similarity approx

                "length": len(text.strip()),

            })

        # Sort by score first, then by length (prefer larger chunks with similar scores)
        candidates.sort(key=lambda x: (x["score"], x["length"]), reverse=True)

        # Return top k chunks
        return candidates[:k]

rag = RAG()
