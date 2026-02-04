import logging
from typing import Optional

from sentence_transformers import SentenceTransformer

from src.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    
    def __init__(self, model_name: Optional[str] = None):
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        
        logger.info(f"Loading local embedding model: {self.model_name}")
        self._model = SentenceTransformer(self.model_name)
        logger.info("Embedding model loaded successfully")
        
    def embed_text(self, text: str) -> list[float]:
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def embed_code(self, code: str, docstring: Optional[str] = None) -> list[float]:
        if docstring:
            text = f"# {docstring}\n\n{code}"
        else:
            text = code
            
        return self.embed_text(text)
