import ast
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class FunctionInfo:
    name: str
    file_path: str
    line_number: int
    end_line: int
    signature: str
    docstring: Optional[str] = None
    parameters: list[str] = field(default_factory=list)
    return_annotation: Optional[str] = None
    decorators: list[str] = field(default_factory=list)
    is_method: bool = False
    class_name: Optional[str] = None
    
    @property
    def qualified_name(self) -> str:
        if self.class_name:
            return f"{self.class_name}.{self.name}"
        return self.name


@dataclass
class ClassInfo:
    name: str
    file_path: str
    line_number: int
    end_line: int
    docstring: Optional[str] = None
    base_classes: list[str] = field(default_factory=list)
    decorators: list[str] = field(default_factory=list)
    methods: list[FunctionInfo] = field(default_factory=list)


@dataclass
class ImportInfo:
    module: str
    name: Optional[str] = None
    alias: Optional[str] = None
    line_number: int = 0
    is_from_import: bool = False


@dataclass
class ParsedFile:
    file_path: str
    language: str
    classes: list[ClassInfo] = field(default_factory=list)
    functions: list[FunctionInfo] = field(default_factory=list)
    imports: list[ImportInfo] = field(default_factory=list)
    global_variables: list[str] = field(default_factory=list)


class PythonParser:
    
    def parse_file(self, file_path: Path | str) -> Optional[ParsedFile]:
        file_path = Path(file_path)
        
        try:
            source = file_path.read_text(encoding="utf-8", errors="ignore")
            return self.parse_source(source, str(file_path.absolute()))
        except Exception as e:
            logger.error(f"Failed to read file {file_path}: {e}")
            return None
    
    def parse_source(self, source: str, file_path: str = "<string>") -> Optional[ParsedFile]:
        try:
            tree = ast.parse(source)
        except SyntaxError as e:
            logger.error(f"Syntax error in {file_path}: {e}")
            return None
            
        parsed = ParsedFile(file_path=file_path, language="python")
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                parsed.imports.extend(self._parse_import(node))
            elif isinstance(node, ast.ImportFrom):
                parsed.imports.extend(self._parse_from_import(node))
        
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                parsed.classes.append(self._parse_class(node, file_path))
            elif isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
                parsed.functions.append(self._parse_function(node, file_path))
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        parsed.global_variables.append(target.id)
                        
        return parsed
    
    def _parse_import(self, node: ast.Import) -> list[ImportInfo]:
        imports = []
        for alias in node.names:
            imports.append(ImportInfo(
                module=alias.name,
                alias=alias.asname,
                line_number=node.lineno,
                is_from_import=False
            ))
        return imports
    
    def _parse_from_import(self, node: ast.ImportFrom) -> list[ImportInfo]:
        imports = []
        module = node.module or ""
        
        for alias in node.names:
            imports.append(ImportInfo(
                module=module,
                name=alias.name,
                alias=alias.asname,
                line_number=node.lineno,
                is_from_import=True
            ))
        return imports
    
    def _parse_class(self, node: ast.ClassDef, file_path: str) -> ClassInfo:
        bases = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                bases.append(base.id)
            elif isinstance(base, ast.Attribute):
                bases.append(self._get_attribute_name(base))
                
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        class_info = ClassInfo(
            name=node.name,
            file_path=file_path,
            line_number=node.lineno,
            end_line=node.end_lineno or node.lineno,
            docstring=ast.get_docstring(node),
            base_classes=bases,
            decorators=decorators
        )
        
        for item in node.body:
            if isinstance(item, ast.FunctionDef | ast.AsyncFunctionDef):
                method = self._parse_function(item, file_path, class_name=node.name)
                class_info.methods.append(method)
                
        return class_info
    
    def _parse_function(
        self, 
        node: ast.FunctionDef | ast.AsyncFunctionDef,
        file_path: str,
        class_name: Optional[str] = None
    ) -> FunctionInfo:
        params = []
        for arg in node.args.args:
            param_name = arg.arg
            if arg.annotation:
                param_name += f": {self._get_annotation_str(arg.annotation)}"
            params.append(param_name)
            
        return_ann = None
        if node.returns:
            return_ann = self._get_annotation_str(node.returns)
            
        async_prefix = "async " if isinstance(node, ast.AsyncFunctionDef) else ""
        signature = f"{async_prefix}def {node.name}({', '.join(params)})"
        if return_ann:
            signature += f" -> {return_ann}"
            
        decorators = [self._get_decorator_name(d) for d in node.decorator_list]
        
        return FunctionInfo(
            name=node.name,
            file_path=file_path,
            line_number=node.lineno,
            end_line=node.end_lineno or node.lineno,
            signature=signature,
            docstring=ast.get_docstring(node),
            parameters=[arg.arg for arg in node.args.args],
            return_annotation=return_ann,
            decorators=decorators,
            is_method=class_name is not None,
            class_name=class_name
        )
    
    def _get_attribute_name(self, node: ast.Attribute) -> str:
        if isinstance(node.value, ast.Name):
            return f"{node.value.id}.{node.attr}"
        elif isinstance(node.value, ast.Attribute):
            return f"{self._get_attribute_name(node.value)}.{node.attr}"
        return node.attr
    
    def _get_decorator_name(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Attribute):
            return self._get_attribute_name(node)
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name):
                return node.func.id
            elif isinstance(node.func, ast.Attribute):
                return self._get_attribute_name(node.func)
        return "<unknown>"
    
    def _get_annotation_str(self, node: ast.expr) -> str:
        if isinstance(node, ast.Name):
            return node.id
        elif isinstance(node, ast.Constant):
            return repr(node.value)
        elif isinstance(node, ast.Subscript):
            base = self._get_annotation_str(node.value)
            if isinstance(node.slice, ast.Tuple):
                args = ", ".join(self._get_annotation_str(e) for e in node.slice.elts)
            else:
                args = self._get_annotation_str(node.slice)
            return f"{base}[{args}]"
        elif isinstance(node, ast.Attribute):
            return self._get_attribute_name(node)
        elif isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr):
            left = self._get_annotation_str(node.left)
            right = self._get_annotation_str(node.right)
            return f"{left} | {right}"
        return "Any"
