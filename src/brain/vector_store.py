import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings as ChromaSettings

from src.config import get_settings
from src.ingestion.extractor import CodeGraph, CodeNode

from .embeddings import EmbeddingGenerator

logger = logging.getLogger(__name__)


class VectorStore:
    
    def __init__(
        self,
        persist_dir: Optional[Path] = None,
        collection_name: Optional[str] = None
    ):
        settings = get_settings()
        self.persist_dir = persist_dir or settings.chroma_persist_dir
        self.collection_name = collection_name or settings.chroma_collection_name
        
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        
        self._client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=ChromaSettings(anonymized_telemetry=False)
        )
        
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        self._embedder = EmbeddingGenerator()
        
        logger.info(f"Vector store initialized at {self.persist_dir}")
        
    def index_graph(self, graph: CodeGraph) -> int:
        documents = []
        metadatas = []
        ids = []
        
        for node_id, node in graph.nodes.items():
            if node.type not in ("function", "class"):
                continue
                
            doc_text = self._build_document_text(node)
            
            documents.append(doc_text)
            metadatas.append({
                "node_id": node_id,
                "type": node.type,
                "name": node.name,
                "file_path": node.file_path or "",
                "line_number": node.line_number or 0,
                "docstring": node.properties.get("docstring", "")[:500]
            })
            ids.append(node_id)
            
        if not documents:
            logger.warning("No documents to index")
            return 0
            
        batch_size = 100
        indexed = 0
        
        for i in range(0, len(documents), batch_size):
            batch_docs = documents[i:i + batch_size]
            batch_metas = metadatas[i:i + batch_size]
            batch_ids = ids[i:i + batch_size]
            
            embeddings = self._embedder.embed_texts(batch_docs)
            
            self._collection.add(
                documents=batch_docs,
                embeddings=embeddings,
                metadatas=batch_metas,
                ids=batch_ids
            )
            
            indexed += len(batch_docs)
            logger.debug(f"Indexed {indexed}/{len(documents)} documents")
            
        logger.info(f"Indexed {indexed} code elements into vector store")
        return indexed
    
    def search(
        self,
        query: str,
        n_results: int = 5,
        filter_type: Optional[str] = None
    ) -> list[dict]:
        where = None
        if filter_type:
            where = {"type": filter_type}
            
        query_embedding = self._embedder.embed_text(query)
        
        results = self._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
            include=["documents", "metadatas", "distances"]
        )
        
        formatted = []
        if results["ids"] and results["ids"][0]:
            for i, doc_id in enumerate(results["ids"][0]):
                formatted.append({
                    "id": doc_id,
                    "document": results["documents"][0][i] if results["documents"] else "",
                    "metadata": results["metadatas"][0][i] if results["metadatas"] else {},
                    "distance": results["distances"][0][i] if results["distances"] else 0.0,
                    "similarity": 1 - (results["distances"][0][i] if results["distances"] else 0.0)
                })
                
        return formatted
    
    def get_by_id(self, node_id: str) -> Optional[dict]:
        result = self._collection.get(
            ids=[node_id],
            include=["documents", "metadatas"]
        )
        
        if result["ids"]:
            return {
                "id": result["ids"][0],
                "document": result["documents"][0] if result["documents"] else "",
                "metadata": result["metadatas"][0] if result["metadatas"] else {}
            }
        return None
    
    def clear(self) -> None:
        self._client.delete_collection(self.collection_name)
        self._collection = self._client.create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        logger.info("Vector store cleared")
        
    def count(self) -> int:
        return self._collection.count()
    
    def _build_document_text(self, node: CodeNode) -> str:
        parts = []
        
        parts.append(f"# {node.type.title()}: {node.name}")
        
        docstring = node.properties.get("docstring", "")
        if docstring:
            parts.append(f"# {docstring}")
            
        signature = node.properties.get("signature", "")
        if signature:
            parts.append(signature)
            
        if node.file_path:
            parts.append(f"# File: {node.file_path}")
            
        return "\n".join(parts)
