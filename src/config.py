from pathlib import Path
from typing import Optional

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )
    
    ollama_base_url: str = Field(default="http://localhost:11434", description="Ollama server URL")
    ollama_model: str = Field(default="llama3.2", description="Ollama model name")
    
    embedding_model: str = Field(default="all-MiniLM-L6-v2", description="Sentence transformer model")
    
    neo4j_uri: str = Field(default="bolt://localhost:7687", description="Neo4j connection URI")
    neo4j_user: str = Field(default="neo4j", description="Neo4j username")
    neo4j_password: str = Field(default="archaeologist123", description="Neo4j password")
    
    chroma_persist_dir: Path = Field(default=Path("./data/chroma"), description="ChromaDB persistence directory")
    chroma_collection_name: str = Field(default="codebase", description="ChromaDB collection name")
    
    log_level: str = Field(default="INFO", description="Logging level")
    supported_extensions: list[str] = Field(
        default=[".py", ".js", ".ts", ".jsx", ".tsx"],
        description="Supported file extensions for parsing"
    )


_settings: Optional[Settings] = None


def get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
