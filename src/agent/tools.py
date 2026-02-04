"""
Agent Tools - Search tools for the Archaeologist agent.
"""

import json
from typing import Optional

from langchain_core.tools import tool

from src.brain.graph_store import GraphStore
from src.brain.vector_store import VectorStore


def create_tools(vector_store: VectorStore, graph_store: GraphStore) -> list:
    """
    Create the agent tools with injected dependencies.
    
    Args:
        vector_store: VectorStore instance
        graph_store: GraphStore instance
        
    Returns:
        List of LangChain tools
    """
    
    @tool
    def semantic_search(query: str, n_results: int = 5) -> str:
        """
        Search for code based on semantic meaning.
        Use this when the user asks "what does X do?" or "find code that handles Y".
        
        Args:
            query: Natural language description of what to find
            n_results: Number of results to return (default 5)
            
        Returns:
            JSON string with search results including code snippets and locations
        """
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
        """
        Find all functions that call a specific function.
        Use this when asked "who calls X?" or "what depends on X?".
        
        Args:
            function_name: Name of the function to find callers for
            
        Returns:
            JSON string with list of calling functions
        """
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
        """
        Find all functions that a specific function calls.
        Use this when asked "what does X call?" or "what are the dependencies of X?".
        
        Args:
            function_name: Name of the function to analyze
            
        Returns:
            JSON string with list of called functions
        """
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
        """
        Find the inheritance hierarchy for a class.
        Use this when asked about class hierarchy, parent classes, or inheritance.
        
        Args:
            class_name: Name of the class to analyze
            
        Returns:
            JSON string with inheritance hierarchy
        """
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
        """
        Find the dependency path between two code elements.
        Use this when asked "how does X connect to Y?" or "trace the path from X to Y".
        
        Args:
            from_element: Starting function or class name
            to_element: Target function or class name
            
        Returns:
            JSON string with the dependency path
        """
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
        """
        Get all imports for a specific file.
        Use this when asked about a file's dependencies or imports.
        
        Args:
            file_path: Path or partial path of the file
            
        Returns:
            JSON string with list of imports
        """
        results = graph_store.find_imports(file_path)
        
        if not results:
            return f"No imports found for file '{file_path}'"
            
        return json.dumps(results, indent=2)
    
    @tool
    def get_file_structure(file_path: str) -> str:
        """
        Get the complete structure of a file (classes, functions).
        Use this when asked "what's in this file?" or "show me the structure of X".
        
        Args:
            file_path: Path or partial path of the file
            
        Returns:
            JSON string with file structure
        """
        result = graph_store.get_file_structure(file_path)
        
        if not result:
            return f"No structure found for file '{file_path}'"
            
        return json.dumps(result, indent=2)
    
    @tool
    def get_codebase_statistics() -> str:
        """
        Get statistics about the indexed codebase.
        Use this when asked about the size or scope of the codebase.
        
        Returns:
            JSON string with codebase statistics
        """
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
