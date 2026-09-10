import os
import glob
import json
import logging
from typing import List, Dict, Any, Optional
import numpy as np

from backend.config import settings
from backend.llm.ollama_client import OllamaClient

logger = logging.getLogger("polar_rag")

class ResearchRAG:
    """Local Research Document Retrieval-Augmented Generation (RAG) Engine."""

    _chunks: List[Dict[str, Any]] = []
    _embeddings: Optional[np.ndarray] = None
    _is_indexed: bool = False

    @classmethod
    def load_documents(cls, docs_dir: Optional[str] = None) -> List[Dict[str, str]]:
        target_dir = docs_dir or settings.RESEARCH_DIR
        raw_docs = []

        if not os.path.exists(target_dir):
            os.makedirs(target_dir, exist_ok=True)
            return raw_docs

        # 1. Text and Markdown files
        for ext in ("*.md", "*.txt"):
            for filepath in glob.glob(os.path.join(target_dir, ext)):
                try:
                    with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read().strip()
                        if text:
                            raw_docs.append({
                                "source": os.path.basename(filepath),
                                "content": text
                            })
                except Exception as e:
                    logger.warning(f"Error reading {filepath}: {e}")

        # 2. PDF Documents via pypdf
        for filepath in glob.glob(os.path.join(target_dir, "*.pdf")):
            try:
                import pypdf
                reader = pypdf.PdfReader(filepath)
                pdf_text = []
                for idx, page in enumerate(reader.pages):
                    ptxt = page.extract_text() or ""
                    if ptxt.strip():
                        pdf_text.append(f"[Page {idx+1}]\n{ptxt.strip()}")
                full_text = "\n\n".join(pdf_text)
                if full_text:
                    raw_docs.append({
                        "source": os.path.basename(filepath),
                        "content": full_text
                    })
            except Exception as e:
                logger.warning(f"Error reading PDF {filepath}: {e}")

        return raw_docs

    @classmethod
    def chunk_text(cls, text: str, chunk_size: int = 500, overlap: int = 80) -> List[str]:
        chunks = []
        start = 0
        text_len = len(text)
        while start < text_len:
            end = min(start + chunk_size, text_len)
            chunk = text[start:end].strip()
            if len(chunk) > 40:
                chunks.append(chunk)
            start += (chunk_size - overlap)
        return chunks

    @classmethod
    def index_documents(cls, force: bool = False) -> int:
        """Indexes all research material with local embeddings."""
        if cls._is_indexed and not force and cls._chunks:
            return len(cls._chunks)

        docs = cls.load_documents()
        all_chunks = []

        for doc in docs:
            src = doc["source"]
            chunks = cls.chunk_text(doc["content"])
            for idx, c in enumerate(chunks):
                all_chunks.append({
                    "id": f"{src}_{idx}",
                    "source": src,
                    "text": c
                })

        cls._chunks = all_chunks
        if not all_chunks:
            cls._is_indexed = True
            return 0

        # Check disk cache first to ensure instant startup & prevent repeated heavy embedding runs
        cache_dir = os.path.join(os.path.dirname(__file__), "..", "data")
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(cache_dir, "rag_embeddings_cache.npz")

        if not force and os.path.exists(cache_file):
            try:
                cached = np.load(cache_file, allow_pickle=True)
                if len(cached["embeddings"]) == len(all_chunks):
                    cls._embeddings = cached["embeddings"]
                    cls._is_indexed = True
                    return len(cls._chunks)
            except Exception as e:
                logger.warning(f"Failed to load RAG disk cache: {e}")

        # Try Ollama embeddings
        texts = [c["text"] for c in all_chunks]
        embeddings = OllamaClient.embed(texts)

        if embeddings and len(embeddings) == len(all_chunks) and len(embeddings[0]) > 0:
            cls._embeddings = np.array(embeddings, dtype=np.float32)
        else:
            # Deterministic local TF-IDF vectorizer fallback if Ollama embeddings are unavailable
            from sklearn.feature_extraction.text import TfidfVectorizer
            vec = TfidfVectorizer(max_features=256, stop_words="english")
            mat = vec.fit_transform(texts).toarray()
            cls._embeddings = np.array(mat, dtype=np.float32)

        # Normalize for fast cosine similarity
        norms = np.linalg.norm(cls._embeddings, axis=1, keepdims=True)
        norms[norms == 0.0] = 1.0
        cls._embeddings = cls._embeddings / norms

        # Save to cache
        try:
            np.savez_compressed(cache_file, embeddings=cls._embeddings)
        except Exception as e:
            logger.warning(f"Failed to save RAG disk cache: {e}")

        cls._is_indexed = True
        return len(cls._chunks)

    @classmethod
    def retrieve(cls, query: str, top_k: int = 3) -> List[Dict[str, Any]]:
        """Semantic search against research library."""
        if not cls._is_indexed or cls._embeddings is None:
            cls.index_documents()

        if not cls._chunks or cls._embeddings is None:
            return []

        # Generate query vector
        query_vec = None
        ollama_q = OllamaClient.embed([query])
        if ollama_q and len(ollama_q) > 0 and len(ollama_q[0]) == cls._embeddings.shape[1]:
            query_vec = np.array(ollama_q[0], dtype=np.float32)
        else:
            # Fallback keyword/TF-IDF similarity
            from sklearn.feature_extraction.text import TfidfVectorizer
            texts = [c["text"] for c in cls._chunks] + [query]
            vec = TfidfVectorizer(max_features=cls._embeddings.shape[1], stop_words="english")
            mat = vec.fit_transform(texts).toarray()
            query_vec = mat[-1]

        q_norm = np.linalg.norm(query_vec)
        if q_norm > 0:
            query_vec = query_vec / q_norm

        scores = np.dot(cls._embeddings, query_vec)
        top_indices = np.argsort(scores)[::-1][:top_k]

        results = []
        for idx in top_indices:
            score = float(scores[idx])
            if score > 0.05:
                chunk = cls._chunks[idx]
                results.append({
                    "source": chunk["source"],
                    "text": chunk["text"],
                    "score": round(score, 3)
                })

        return results

    @classmethod
    def format_context_for_prompt(cls, query: str, top_k: int = 3) -> str:
        """
        Formats retrieved literature strictly separated from live telemetry.
        Never allow LLM to hallucinate academic figures as live station readings.
        """
        results = cls.retrieve(query, top_k=top_k)
        if not results:
            return ""

        lines = [
            "=== ACADEMIC RESEARCH CONTEXT (Google Scholar / Literature) ===",
            "[IMPORTANT: The following are scientific research excerpts and theoretical models. "
            "DO NOT present these historical research numbers as current live station telemetry.]"
        ]
        for idx, r in enumerate(results, 1):
            lines.append(f"[{idx}] Source: {r['source']} (Relevance Score: {r['score']})")
            lines.append(f"{r['text']}\n")
        lines.append("=== END OF RESEARCH CONTEXT ===\n")
        return "\n".join(lines)
