"""
Embedding Generator - Creates embeddings for code snippets using OpenAI.
"""

import logging
from typing import Optional

from langchain_openai import OpenAIEmbeddings

from src.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingGenerator:
    """Generates embeddings for code snippets."""
    
    def __init__(self, model: Optional[str] = None):
        """
        Initialize the embedding generator.
        
        Args:
            model: OpenAI embedding model to use
        """
        settings = get_settings()
        self.model = model or settings.openai_embedding_model
        
        self._embeddings = OpenAIEmbeddings(
            api_key=settings.openai_api_key,
            model=self.model
        )
        
    def embed_text(self, text: str) -> list[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed
            
        Returns:
            Embedding vector as list of floats
        """
        return self._embeddings.embed_query(text)
    
    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embedding vectors
        """
        return self._embeddings.embed_documents(texts)
    
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
