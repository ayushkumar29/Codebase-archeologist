"""
Tests for the relationship extractor.
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.extractor import (
    RelationshipExtractor, 
    CodeGraph, 
    CodeNode, 
    RelationType
)


@pytest.fixture
def extractor():
    """Create an extractor instance."""
    return RelationshipExtractor()


@pytest.fixture
def sample_codebase_path():
    """Get the path to the sample codebase."""
    return Path(__file__).parent / "sample_codebase"


class TestRelationshipExtractor:
    """Tests for the RelationshipExtractor class."""
    
    def test_process_single_file(self, extractor, sample_codebase_path):
        """Test processing a single file."""
        models_path = sample_codebase_path / "models.py"
        
        if not models_path.exists():
            pytest.skip("Sample codebase not available")
            
        parsed = extractor.process_file(models_path)
        
        assert parsed is not None
        assert parsed.language == "python"
        assert len(parsed.classes) >= 2  # BaseRepository, UserRepository
        
    def test_process_codebase(self, extractor, sample_codebase_path):
        """Test processing the entire sample codebase."""
        if not sample_codebase_path.exists():
            pytest.skip("Sample codebase not available")
            
        graph = extractor.process_codebase(sample_codebase_path)
        
        assert len(graph.nodes) > 0
        assert len(graph.relationships) > 0
        
    def test_file_nodes_created(self, extractor, sample_codebase_path):
        """Test that file nodes are created."""
        if not sample_codebase_path.exists():
            pytest.skip("Sample codebase not available")
            
        graph = extractor.process_codebase(sample_codebase_path)
        
        file_nodes = [n for n in graph.nodes.values() if n.type == "file"]
        assert len(file_nodes) >= 2  # models.py, auth.py
        
    def test_class_nodes_created(self, extractor, sample_codebase_path):
        """Test that class nodes are created."""
        if not sample_codebase_path.exists():
            pytest.skip("Sample codebase not available")
            
        graph = extractor.process_codebase(sample_codebase_path)
        
        class_nodes = [n for n in graph.nodes.values() if n.type == "class"]
        class_names = [n.name for n in class_nodes]
        
        assert "BaseRepository" in class_names
        assert "UserRepository" in class_names
        assert "User" in class_names
        
    def test_inheritance_relationships(self, extractor, sample_codebase_path):
        """Test that inheritance relationships are detected."""
        if not sample_codebase_path.exists():
            pytest.skip("Sample codebase not available")
            
        graph = extractor.process_codebase(sample_codebase_path)
        
        inheritance_rels = [
            r for r in graph.relationships 
            if r.type == RelationType.INHERITS_FROM
        ]
        
        # UserRepository should inherit from BaseRepository
        assert len(inheritance_rels) >= 1
        
    def test_import_relationships(self, extractor, sample_codebase_path):
        """Test that import relationships are detected."""
        if not sample_codebase_path.exists():
            pytest.skip("Sample codebase not available")
            
        graph = extractor.process_codebase(sample_codebase_path)
        
        import_rels = [
            r for r in graph.relationships 
            if r.type == RelationType.IMPORTS
        ]
        
        assert len(import_rels) >= 1
        
    def test_declares_relationships(self, extractor, sample_codebase_path):
        """Test that DECLARES relationships are created."""
        if not sample_codebase_path.exists():
            pytest.skip("Sample codebase not available")
            
        graph = extractor.process_codebase(sample_codebase_path)
        
        declares_rels = [
            r for r in graph.relationships 
            if r.type == RelationType.DECLARES
        ]
        
        # Files should declare their classes and functions
        assert len(declares_rels) >= 3


class TestCodeGraph:
    """Tests for the CodeGraph class."""
    
    def test_add_node(self):
        """Test adding nodes to the graph."""
        graph = CodeGraph()
        node = CodeNode(
            id="test:node",
            type="function",
            name="test_function",
            file_path="/path/to/file.py"
        )
        
        graph.add_node(node)
        
        assert "test:node" in graph.nodes
        assert graph.get_node("test:node") == node
        
    def test_add_relationship(self):
        """Test adding relationships to the graph."""
        from src.ingestion.extractor import CodeRelationship
        
        graph = CodeGraph()
        rel = CodeRelationship(
            source_id="node1",
            target_id="node2",
            type=RelationType.CALLS
        )
        
        graph.add_relationship(rel)
        
        assert len(graph.relationships) == 1
        assert graph.relationships[0].type == RelationType.CALLS
