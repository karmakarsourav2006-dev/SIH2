import json
import logging
from typing import List, Dict, Any, Optional
import httpx
from backend.config import settings

logger = logging.getLogger("polar_ollama")

class OllamaClient:
    """Client interface for local Ollama daemon on Windows."""

    @classmethod
    def get_base_url(cls) -> str:
        return settings.OLLAMA_URL.rstrip('/')

    @classmethod
    def check_health(cls) -> Dict[str, Any]:
        """Check if Ollama is running and query available models."""
        url = f"{cls.get_base_url()}/api/tags"
        try:
            with httpx.Client(timeout=3.0) as client:
                res = client.get(url)
                if res.status_code == 200:
                    data = res.json()
                    models = [m.get("name") for m in data.get("models", [])]
                    return {
                        "status": "online",
                        "available_models": models,
                        "configured_model": settings.OLLAMA_MODEL,
                        "configured_embed_model": settings.OLLAMA_EMBED_MODEL,
                        "url": cls.get_base_url()
                    }
                return {"status": "error", "code": res.status_code, "message": res.text}
        except Exception as e:
            return {"status": "offline", "error": str(e), "url": cls.get_base_url()}

    @classmethod
    def chat(
        cls,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        temperature: float = 0.2
    ) -> Optional[str]:
        """Execute multi-turn chat with Ollama."""
        target_model = model or settings.OLLAMA_MODEL
        url = f"{cls.get_base_url()}/api/chat"
        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096
            }
        }
        try:
            with httpx.Client(timeout=settings.OLLAMA_TIMEOUT) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    msg = data.get("message", {})
                    return msg.get("content", "").strip()
                elif target_model != settings.OLLAMA_FALLBACK_MODEL:
                    payload["model"] = settings.OLLAMA_FALLBACK_MODEL
                    res_fb = client.post(url, json=payload)
                    if res_fb.status_code == 200:
                        return res_fb.json().get("message", {}).get("content", "").strip()
        except Exception as e:
            logger.warning(f"Ollama chat failed ({e}). Falling back.")
        return None

    @classmethod
    def generate(
        cls,
        prompt: str,
        system: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2
    ) -> Optional[str]:
        """Prompt generation with Ollama."""
        target_model = model or settings.OLLAMA_MODEL
        url = f"{cls.get_base_url()}/api/generate"
        payload = {
            "model": target_model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_ctx": 4096
            }
        }
        if system:
            payload["system"] = system

        try:
            with httpx.Client(timeout=settings.OLLAMA_TIMEOUT) as client:
                res = client.post(url, json=payload)
                if res.status_code == 200:
                    return res.json().get("response", "").strip()
                elif target_model != settings.OLLAMA_FALLBACK_MODEL:
                    payload["model"] = settings.OLLAMA_FALLBACK_MODEL
                    res_fb = client.post(url, json=payload)
                    if res_fb.status_code == 200:
                        return res_fb.json().get("response", "").strip()
        except Exception as e:
            logger.warning(f"Ollama generate failed ({e}). Falling back.")
        return None

    @classmethod
    def embed(cls, text_or_texts: Any, model: Optional[str] = None) -> List[List[float]]:
        """Generate embeddings for text chunks via Ollama."""
        target_model = model or settings.OLLAMA_EMBED_MODEL
        if isinstance(text_or_texts, str):
            texts = [text_or_texts]
        else:
            texts = list(text_or_texts)

        if not texts:
            return []

        url_embed = f"{cls.get_base_url()}/api/embed"
        # Try batching in chunks of 16 to avoid overflowing Ollama server context
        batch_size = 16
        batched_results = []
        try:
            with httpx.Client(timeout=settings.OLLAMA_TIMEOUT) as client:
                for i in range(0, len(texts), batch_size):
                    batch = texts[i:i + batch_size]
                    res = client.post(url_embed, json={"model": target_model, "input": batch})
                    if res.status_code == 200:
                        data = res.json()
                        embeddings = data.get("embeddings", [])
                        if embeddings and len(embeddings) == len(batch):
                            batched_results.extend(embeddings)
                        else:
                            break
                    else:
                        break
            if len(batched_results) == len(texts):
                return batched_results
        except Exception:
            pass

        # Fallback to single endpoint only if few texts (e.g. <= 5)
        if len(texts) <= 5:
            url_single = f"{cls.get_base_url()}/api/embeddings"
            results = []
            try:
                with httpx.Client(timeout=settings.OLLAMA_TIMEOUT) as client:
                    for t in texts:
                        res = client.post(url_single, json={"model": target_model, "prompt": t})
                        if res.status_code == 200:
                            vec = res.json().get("embedding", [])
                            results.append(vec)
                        else:
                            break
            except Exception as e:
                logger.warning(f"Ollama embed error: {e}")
            if len(results) == len(texts):
                return results

        return []
