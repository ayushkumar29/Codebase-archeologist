"""
Tests for the Python AST parser.
"""

import pytest
from pathlib import Path

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingestion.parser import PythonParser, FunctionInfo, ClassInfo


@pytest.fixture
def parser():
    """Create a parser instance."""
    return PythonParser()


@pytest.fixture
def sample_code():
    """Sample Python code for testing."""
    return '''
class MyClass:
    """A sample class."""
    
    def __init__(self, value: int):
        """Initialize with a value."""
        self.value = value
        
    def get_value(self) -> int:
        """Return the value."""
        return self.value
        
        
def standalone_function(x: str, y: int = 0) -> str:
    """A standalone function."""
    return f"{x}: {y}"
    

import os
from typing import Optional, List
from pathlib import Path
'''


class TestPythonParser:
    """Tests for the PythonParser class."""
    
    def test_parse_class(self, parser, sample_code):
        """Test that classes are correctly parsed."""
        result = parser.parse_source(sample_code, "test.py")
        
        assert result is not None
        assert len(result.classes) == 1
        
        cls = result.classes[0]
        assert cls.name == "MyClass"
        assert cls.docstring == "A sample class."
        assert len(cls.methods) == 2
        
    def test_parse_methods(self, parser, sample_code):
        """Test that methods are correctly parsed."""
        result = parser.parse_source(sample_code, "test.py")
        
        cls = result.classes[0]
        method_names = [m.name for m in cls.methods]
        
        assert "__init__" in method_names
        assert "get_value" in method_names
        
    def test_parse_function(self, parser, sample_code):
        """Test that standalone functions are parsed."""
        result = parser.parse_source(sample_code, "test.py")
        
        assert len(result.functions) == 1
        
        func = result.functions[0]
        assert func.name == "standalone_function"
        assert "x" in func.parameters
        assert "y" in func.parameters
        
    def test_parse_imports(self, parser, sample_code):
        """Test that imports are correctly parsed."""
        result = parser.parse_source(sample_code, "test.py")
        
        assert len(result.imports) >= 3
        
        import_modules = [i.module for i in result.imports]
        assert "os" in import_modules
        assert "typing" in import_modules
        assert "pathlib" in import_modules
        
    def test_parse_file(self, parser, tmp_path):
        """Test parsing an actual file."""
        test_file = tmp_path / "test_module.py"
        test_file.write_text("""
def hello(name: str) -> str:
    return f"Hello, {name}!"
""")
        
        result = parser.parse_file(test_file)
        
        assert result is not None
        assert len(result.functions) == 1
        assert result.functions[0].name == "hello"
        
    def test_parse_syntax_error(self, parser):
        """Test handling of syntax errors."""
        bad_code = "def broken(:\n    pass"
        
        result = parser.parse_source(bad_code, "bad.py")
        
        assert result is None
        
    def test_parse_inheritance(self, parser):
        """Test parsing class inheritance."""
        code = """
class Child(Parent):
    pass
"""
        result = parser.parse_source(code, "test.py")
        
        assert len(result.classes) == 1
        assert "Parent" in result.classes[0].base_classes
        
    def test_parse_decorators(self, parser):
        """Test parsing decorators."""
        code = """
@dataclass
class Config:
    value: int
    
@property
def get_config(self):
    return self._config
"""
        result = parser.parse_source(code, "test.py")
        
        assert "dataclass" in result.classes[0].decorators
