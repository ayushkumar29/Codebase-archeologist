import json
from typing import Optional

from langchain_core.tools import tool

from src.brain.graph_store import GraphStore
from src.brain.vector_store import VectorStore


def create_tools(vector_store: VectorStore, graph_store: GraphStore) -> list:
    
    @tool
    def semantic_search(query: str, n_results: int = 5) -> str:
        results = vector_store.search(query, n_results=n_results)
        
        formatted = []
        for r in results:
            formatted.append({
                "name": r["metadata"].get("name", "Unknown"),
                "type": r["metadata"].get("type", "Unknown"),
                "file": r["metadata"].get("file_path", "Unknown"),
                "line": r["metadata"].get("line_number", 0),
                "similarity": round(r.get("similarity", 0), 3),
                "docstring": r["metadata"].get("docstring", "")[:200]
            })
            
        return json.dumps(formatted, indent=2)
    
    @tool
    def find_function_callers(function_name: str) -> str:
        results = graph_store.find_callers(function_name)
        
        formatted = []
        for r in results:
            formatted.append({
                "caller": r.get("caller_name", "Unknown"),
                "file": r.get("caller_file", "Unknown"),
                "calls": r.get("target_name", function_name),
                "at_line": r.get("line_number", 0)
            })
            
        if not formatted:
            return f"No callers found for function '{function_name}'"
            
        return json.dumps(formatted, indent=2)
    
    @tool
    def find_function_calls(function_name: str) -> str:
        results = graph_store.find_callees(function_name)
        
        formatted = []
        for r in results:
            formatted.append({
                "calls": r.get("target_name", "Unknown"),
                "file": r.get("target_file", "Unknown"),
                "from": r.get("caller_name", function_name),
                "at_line": r.get("line_number", 0)
            })
            
        if not formatted:
            return f"No outgoing calls found from function '{function_name}'"
            
        return json.dumps(formatted, indent=2)
    
    @tool
    def find_class_inheritance(class_name: str) -> str:
        results = graph_store.find_class_hierarchy(class_name)
        
        if not results:
            return f"No inheritance information found for class '{class_name}'"
            
        formatted = []
        for r in results:
            formatted.append({
                "class": r.get("class_name", class_name),
                "file": r.get("file_path", "Unknown"),
                "hierarchy": r.get("hierarchy", [])
            })
            
        return json.dumps(formatted, indent=2)
    
    @tool
    def trace_dependency_path(from_element: str, to_element: str) -> str:
        results = graph_store.trace_dependency_path(from_element, to_element)
        
        if not results:
            return f"No path found between '{from_element}' and '{to_element}'"
            
        formatted = []
        for r in results:
            formatted.append({
                "path": r.get("path", []),
                "relationships": r.get("relationships", []),
                "depth": r.get("depth", 0)
            })
            
        return json.dumps(formatted, indent=2)
    
    @tool
    def get_file_imports(file_path: str) -> str:
        results = graph_store.find_imports(file_path)
        
        if not results:
            return f"No imports found for file '{file_path}'"
            
        return json.dumps(results, indent=2)
    
    @tool
    def get_file_structure(file_path: str) -> str:
        result = graph_store.get_file_structure(file_path)
        
        if not result:
            return f"No structure found for file '{file_path}'"
            
        return json.dumps(result, indent=2)
    
    @tool
    def get_codebase_statistics() -> str:
        stats = graph_store.get_statistics()
        stats["vector_store_count"] = vector_store.count()
        
        return json.dumps(stats, indent=2)
    
    return [
        semantic_search,
        find_function_callers,
        find_function_calls,
        find_class_inheritance,
        trace_dependency_path,
        get_file_imports,
        get_file_structure,
        get_codebase_statistics
    ]
