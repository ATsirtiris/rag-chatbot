# app/ingest.py
from __future__ import annotations

import os, re, uuid, asyncio

from pathlib import Path

from typing import List, Dict, Iterable



import httpx

from tenacity import retry, wait_exponential_jitter, stop_after_attempt

import chromadb

from chromadb.config import Settings as ChromaSettings

from pypdf import PdfReader



from .settings import settings



WHITESPACE_RE = re.compile(r"\s+")



def normalize_text(x: str) -> str:

    return WHITESPACE_RE.sub(" ", x).strip()



def chunk_text(text: str, chunk_chars: int = 2000, overlap: int = 300) -> List[str]:

    text = normalize_text(text)

    if not text:

        return []

    chunks, start, n = [], 0, len(text)

    while start < n:

        end = min(n, start + chunk_chars)

        chunk = text[start:end]

        if end < n:

            last_period = chunk.rfind(".")

            if last_period > 200:

                end = start + last_period + 1

                chunk = text[start:end]

        chunks.append(chunk)

        start = max(end - overlap, start + 1)

    return chunks



def load_pdf(path: Path) -> List[Dict]:

    reader = PdfReader(str(path))

    docs = []

    for i, page in enumerate(reader.pages, start=1):

        raw = page.extract_text() or ""

        for j, ch in enumerate(chunk_text(raw)):

            docs.append({

                "id": f"{path.name}:{i}:{j}:{uuid.uuid4().hex[:8]}",

                "text": ch,

                "metadata": {"source": str(path), "page": i},

            })

    return docs



def load_txt(path: Path) -> List[Dict]:

    raw = path.read_text(encoding="utf-8", errors="ignore")

    docs = []

    for j, ch in enumerate(chunk_text(raw)):

        docs.append({

            "id": f"{path.name}:{j}:{uuid.uuid4().hex[:8]}",

            "text": ch,

            "metadata": {"source": str(path), "page": None},

        })

    return docs



OPENAI_API_KEY = settings.OPENAI_API_KEY

EMBED_MODEL = settings.EMBED_MODEL

HEADERS = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}



@retry(wait=wait_exponential_jitter(initial=0.5, max=8), stop=stop_after_attempt(6))

async def embed_batch(texts: List[str]) -> List[List[float]]:

    payload = {"model": EMBED_MODEL, "input": texts}

    async with httpx.AsyncClient(timeout=120) as client:

        r = await client.post("https://api.openai.com/v1/embeddings", headers=HEADERS, json=payload)

        r.raise_for_status()

        data = r.json()

        return [d["embedding"] for d in data["data"]]



async def embed_texts_batched(texts: List[str], batch_size: int = 128) -> List[List[float]]:

    out: List[List[float]] = []

    for i in range(0, len(texts), batch_size):

        out.extend(await embed_batch(texts[i:i+batch_size]))

    return out



def main():

    if not OPENAI_API_KEY:

        raise RuntimeError("OPENAI_API_KEY missing in environment/.env")



    data_dir = Path(settings.DATA_DIR)

    data_dir.mkdir(parents=True, exist_ok=True)



    files = list(data_dir.rglob("*.pdf")) + list(data_dir.rglob("*.txt"))

    if not files:

        print(f"No files in {data_dir}. Add PDFs or TXTs and re-run.")

        return



    client = chromadb.PersistentClient(

        path=settings.CHROMA_DIR,

        settings=ChromaSettings(anonymized_telemetry=False),

    )

    coll = client.get_or_create_collection("docs", metadata={"hnsw:space": "cosine"})



    all_ids, all_docs, all_meta = [], [], []

    for fp in files:

        docs = load_pdf(fp) if fp.suffix.lower() == ".pdf" else load_txt(fp)

        if not docs:

            continue

        ids = [d["id"] for d in docs]

        texts = [d["text"] for d in docs]

        metas = [d["metadata"] for d in docs]



        embs = asyncio.run(embed_texts_batched(texts))

        coll.add(ids=ids, embeddings=embs, documents=texts, metadatas=metas)

        all_ids += ids

        print(f"Indexed {len(ids)} chunks from {fp.name}")



    print(f"Done. Total chunks: {len(all_ids)} → store: {settings.CHROMA_DIR}")



if __name__ == "__main__":

    main()
