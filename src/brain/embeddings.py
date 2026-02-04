"""
Embedding Generator - Creates embeddings using local sentence-transformers.
No API keys required!
"""

import logging
from typing import Optional

from sentence_transformers import SentenceTransformer

from src.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings using local sentence-transformers models."""
    
    def __init__(self, model_name: Optional[str] = None):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: HuggingFace model name (default: all-MiniLM-L6-v2)
        """
        settings = get_settings()
        self.model_name = model_name or settings.embedding_model
        
        logger.info(f"Loading local embedding model: {self.model_name}")
        self._model = SentenceTransformer(self.model_name)
        logger.info("Embedding model loaded successfully")
        
    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        embedding = self._model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        embeddings = self._model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()
    
    def embed_code(self, code: str, docstring: Optional[str] = None) -> list[float]:
        """
        Generate embedding for code, optionally including docstring.
        
        Args:
            code: Source code to embed
            docstring: Optional docstring to prepend
            
        Returns:
            Embedding vector
        """
        if docstring:
            text = f"# {docstring}\n\n{code}"
        else:
            text = code
            
        return self.embed_text(text)
