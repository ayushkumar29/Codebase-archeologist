import ast
import logging
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

from .parser import ParsedFile, PythonParser

logger = logging.getLogger(__name__)


class RelationType(Enum):
    IMPORTS = "IMPORTS"
    DECLARES = "DECLARES"
    CALLS = "CALLS"
    INHERITS_FROM = "INHERITS_FROM"
    CONTAINS = "CONTAINS"
    USES = "USES"


@dataclass
class CodeNode:
    id: str
    type: str
    name: str
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    properties: dict = field(default_factory=dict)
    
    def __hash__(self):
        return hash(self.id)


@dataclass
class CodeRelationship:
    source_id: str
    target_id: str
    type: RelationType
    properties: dict = field(default_factory=dict)
    
    def __hash__(self):
        return hash((self.source_id, self.target_id, self.type))


@dataclass
class CodeGraph:
    nodes: dict[str, CodeNode] = field(default_factory=dict)
    relationships: list[CodeRelationship] = field(default_factory=list)
    
    def add_node(self, node: CodeNode) -> None:
        self.nodes[node.id] = node
        
    def add_relationship(self, rel: CodeRelationship) -> None:
        self.relationships.append(rel)
        
    def get_node(self, node_id: str) -> Optional[CodeNode]:
        return self.nodes.get(node_id)


class RelationshipExtractor:
    
    def __init__(self):
        self.parser = PythonParser()
        self.graph = CodeGraph()
        self._function_registry: dict[str, str] = {}
        
    def process_codebase(self, root_path: Path | str) -> CodeGraph:
        from .scanner import CodeScanner
        
        root = Path(root_path)
        scanner = CodeScanner(extensions=[".py"])
        
        parsed_files: list[ParsedFile] = []
        
        for file_path in scanner.scan(root):
            parsed = self.parser.parse_file(file_path)
            if parsed:
                parsed_files.append(parsed)
                self._add_file_nodes(parsed)
                
        for parsed in parsed_files:
            self._extract_relationships(parsed, root)
            
        logger.info(
            f"Graph built: {len(self.graph.nodes)} nodes, "
            f"{len(self.graph.relationships)} relationships"
        )
        
        return self.graph
    
    def process_file(self, file_path: Path | str) -> Optional[ParsedFile]:
        parsed = self.parser.parse_file(file_path)
        if parsed:
            self._add_file_nodes(parsed)
        return parsed
    
    def _add_file_nodes(self, parsed: ParsedFile) -> None:
        file_id = self._make_file_id(parsed.file_path)
        
        self.graph.add_node(CodeNode(
            id=file_id,
            type="file",
            name=Path(parsed.file_path).name,
            file_path=parsed.file_path,
            properties={"language": parsed.language}
        ))
        
        for cls in parsed.classes:
            class_id = f"{file_id}:{cls.name}"
            self.graph.add_node(CodeNode(
                id=class_id,
                type="class",
                name=cls.name,
                file_path=parsed.file_path,
                line_number=cls.line_number,
                properties={
                    "docstring": cls.docstring or "",
                    "base_classes": cls.base_classes,
                    "decorators": cls.decorators
                }
            ))
            
            self.graph.add_relationship(CodeRelationship(
                source_id=file_id,
                target_id=class_id,
                type=RelationType.DECLARES,
                properties={"line_number": cls.line_number}
            ))
            
            for method in cls.methods:
                method_id = f"{class_id}.{method.name}"
                self.graph.add_node(CodeNode(
                    id=method_id,
                    type="function",
                    name=method.qualified_name,
                    file_path=parsed.file_path,
                    line_number=method.line_number,
                    properties={
                        "signature": method.signature,
                        "docstring": method.docstring or "",
                        "is_method": True,
                        "class_name": cls.name
                    }
                ))
                
                self._function_registry[method.name] = method_id
                self._function_registry[method.qualified_name] = method_id
                
                self.graph.add_relationship(CodeRelationship(
                    source_id=class_id,
                    target_id=method_id,
                    type=RelationType.CONTAINS
                ))
                
        for func in parsed.functions:
            func_id = f"{file_id}:{func.name}"
            self.graph.add_node(CodeNode(
                id=func_id,
                type="function",
                name=func.name,
                file_path=parsed.file_path,
                line_number=func.line_number,
                properties={
                    "signature": func.signature,
                    "docstring": func.docstring or "",
                    "is_method": False
                }
            ))
            
            self._function_registry[func.name] = func_id
            
            self.graph.add_relationship(CodeRelationship(
                source_id=file_id,
                target_id=func_id,
                type=RelationType.DECLARES,
                properties={"line_number": func.line_number}
            ))
            
    def _extract_relationships(self, parsed: ParsedFile, root: Path) -> None:
        file_id = self._make_file_id(parsed.file_path)
        
        for imp in parsed.imports:
            module_id = f"module:{imp.module}"
            
            if module_id not in self.graph.nodes:
                self.graph.add_node(CodeNode(
                    id=module_id,
                    type="module",
                    name=imp.module,
                    properties={"is_external": True}
                ))
                
            self.graph.add_relationship(CodeRelationship(
                source_id=file_id,
                target_id=module_id,
                type=RelationType.IMPORTS,
                properties={"line_number": imp.line_number}
            ))
            
        for cls in parsed.classes:
            class_id = f"{file_id}:{cls.name}"
            
            for base in cls.base_classes:
                base_id = self._resolve_class(base, parsed.file_path)
                if base_id:
                    self.graph.add_relationship(CodeRelationship(
                        source_id=class_id,
                        target_id=base_id,
                        type=RelationType.INHERITS_FROM
                    ))
                    
        self._extract_calls(parsed)
        
    def _extract_calls(self, parsed: ParsedFile) -> None:
        try:
            source = Path(parsed.file_path).read_text(encoding="utf-8", errors="ignore")
            tree = ast.parse(source)
        except Exception:
            return
            
        file_id = self._make_file_id(parsed.file_path)
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                source_func_id = self._find_function_id(node, file_id, parsed)
                if not source_func_id:
                    continue
                    
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        target_name = self._get_call_name(child)
                        if target_name:
                            target_id = self._function_registry.get(target_name)
                            if target_id and target_id != source_func_id:
                                self.graph.add_relationship(CodeRelationship(
                                    source_id=source_func_id,
                                    target_id=target_id,
                                    type=RelationType.CALLS,
                                    properties={"line_number": child.lineno}
                                ))
                                
    def _find_function_id(
        self, 
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_id: str,
        parsed: ParsedFile
    ) -> Optional[str]:
        for cls in parsed.classes:
            for method in cls.methods:
                if method.name == node.name and method.line_number == node.lineno:
                    return f"{file_id}:{cls.name}.{method.name}"
                    
        for func in parsed.functions:
            if func.name == node.name and func.line_number == node.lineno:
                return f"{file_id}:{func.name}"
                
        return None
    
    def _get_call_name(self, node: ast.Call) -> Optional[str]:
        if isinstance(node.func, ast.Name):
            return node.func.id
        elif isinstance(node.func, ast.Attribute):
            return node.func.attr
        return None
    
    def _resolve_class(self, class_name: str, current_file: str) -> Optional[str]:
        file_id = self._make_file_id(current_file)
        
        local_id = f"{file_id}:{class_name}"
        if local_id in self.graph.nodes:
            return local_id
            
        for node_id, node in self.graph.nodes.items():
            if node.type == "class" and node.name == class_name:
                return node_id
                
        return None
    
    @staticmethod
    def _make_file_id(file_path: str) -> str:
        return f"file:{Path(file_path).as_posix()}"
