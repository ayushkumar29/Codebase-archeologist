"""
Graph Store - Neo4j storage for code relationships.
"""

import logging
from typing import Optional

from neo4j import GraphDatabase, Driver

from src.config import get_settings
from src.ingestion.extractor import CodeGraph, CodeNode, CodeRelationship, RelationType

logger = logging.getLogger(__name__)


class GraphStore:
    """Neo4j-based graph store for code relationships."""
    
    def __init__(
        self,
        uri: Optional[str] = None,
        user: Optional[str] = None,
        password: Optional[str] = None
    ):
        """
        Initialize the graph store.
        
        Args:
            uri: Neo4j connection URI
            user: Neo4j username
            password: Neo4j password
        """
        settings = get_settings()
        self.uri = uri or settings.neo4j_uri
        self.user = user or settings.neo4j_user
        self.password = password or settings.neo4j_password
        
        self._driver: Optional[Driver] = None
        
    def connect(self) -> None:
        """Establish connection to Neo4j."""
        self._driver = GraphDatabase.driver(
            self.uri,
            auth=(self.user, self.password)
        )
        # Verify connection
        self._driver.verify_connectivity()
        logger.info(f"Connected to Neo4j at {self.uri}")
        
        # Create indexes for better performance
        self._create_indexes()
        
    def close(self) -> None:
        """Close the Neo4j connection."""
        if self._driver:
            self._driver.close()
            logger.info("Neo4j connection closed")
            
    def _create_indexes(self) -> None:
        """Create indexes for common queries."""
        indexes = [
            "CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.id)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.id)",
            "CREATE INDEX IF NOT EXISTS FOR (fn:Function) ON (fn.id)",
            "CREATE INDEX IF NOT EXISTS FOR (m:Module) ON (m.id)",
            "CREATE INDEX IF NOT EXISTS FOR (f:File) ON (f.name)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.name)",
            "CREATE INDEX IF NOT EXISTS FOR (fn:Function) ON (fn.name)",
        ]
        
        with self._driver.session() as session:
            for index_query in indexes:
                try:
                    session.run(index_query)
                except Exception as e:
                    logger.debug(f"Index creation: {e}")
                    
    def index_graph(self, graph: CodeGraph) -> tuple[int, int]:
        """
        Index all nodes and relationships from a CodeGraph.
        
        Args:
            graph: CodeGraph to index
            
        Returns:
            Tuple of (nodes_created, relationships_created)
        """
        nodes_created = 0
        rels_created = 0
        
        with self._driver.session() as session:
            # Create nodes
            for node_id, node in graph.nodes.items():
                if self._create_node(session, node):
                    nodes_created += 1
                    
            # Create relationships
            for rel in graph.relationships:
                if self._create_relationship(session, rel):
                    rels_created += 1
                    
        logger.info(f"Created {nodes_created} nodes and {rels_created} relationships")
        return nodes_created, rels_created
    
    def _create_node(self, session, node: CodeNode) -> bool:
        """Create a single node in Neo4j."""
        label = self._type_to_label(node.type)
        
        query = f"""
        MERGE (n:{label} {{id: $id}})
        SET n.name = $name,
            n.file_path = $file_path,
            n.line_number = $line_number
        """
        
        # Add properties
        for key, value in node.properties.items():
            if isinstance(value, (str, int, float, bool)):
                query += f", n.{key} = ${key}"
            elif isinstance(value, list):
                query += f", n.{key} = ${key}"
                
        params = {
            "id": node.id,
            "name": node.name,
            "file_path": node.file_path or "",
            "line_number": node.line_number or 0,
            **{k: v for k, v in node.properties.items() 
               if isinstance(v, (str, int, float, bool, list))}
        }
        
        try:
            session.run(query, params)
            return True
        except Exception as e:
            logger.error(f"Failed to create node {node.id}: {e}")
            return False
            
    def _create_relationship(self, session, rel: CodeRelationship) -> bool:
        """Create a relationship in Neo4j."""
        query = f"""
        MATCH (a {{id: $source_id}})
        MATCH (b {{id: $target_id}})
        MERGE (a)-[r:{rel.type.value}]->(b)
        """
        
        # Add properties
        if rel.properties:
            set_clauses = []
            for key, value in rel.properties.items():
                if isinstance(value, (str, int, float, bool)):
                    set_clauses.append(f"r.{key} = ${key}")
            if set_clauses:
                query += " SET " + ", ".join(set_clauses)
                
        params = {
            "source_id": rel.source_id,
            "target_id": rel.target_id,
            **{k: v for k, v in rel.properties.items()
               if isinstance(v, (str, int, float, bool))}
        }
        
        try:
            session.run(query, params)
            return True
        except Exception as e:
            logger.error(f"Failed to create relationship: {e}")
            return False
            
    def find_callers(self, function_name: str) -> list[dict]:
        """
        Find all functions that call a given function.
        
        Args:
            function_name: Name of the target function
            
        Returns:
            List of caller information
        """
        query = """
        MATCH (caller:Function)-[r:CALLS]->(target:Function)
        WHERE target.name CONTAINS $name
        RETURN caller.id as caller_id, 
               caller.name as caller_name,
               caller.file_path as caller_file,
               target.name as target_name,
               r.line_number as line_number
        """
        
        with self._driver.session() as session:
            result = session.run(query, {"name": function_name})
            return [dict(record) for record in result]
            
    def find_callees(self, function_name: str) -> list[dict]:
        """
        Find all functions called by a given function.
        
        Args:
            function_name: Name of the source function
            
        Returns:
            List of callee information
        """
        query = """
        MATCH (caller:Function)-[r:CALLS]->(target:Function)
        WHERE caller.name CONTAINS $name
        RETURN target.id as target_id,
               target.name as target_name,
               target.file_path as target_file,
               caller.name as caller_name,
               r.line_number as line_number
        """
        
        with self._driver.session() as session:
            result = session.run(query, {"name": function_name})
            return [dict(record) for record in result]
            
    def find_class_hierarchy(self, class_name: str) -> list[dict]:
        """
        Find the inheritance hierarchy for a class.
        
        Args:
            class_name: Name of the class
            
        Returns:
            List of classes in the hierarchy
        """
        query = """
        MATCH path = (c:Class)-[:INHERITS_FROM*0..10]->(parent:Class)
        WHERE c.name CONTAINS $name
        RETURN c.name as class_name,
               c.file_path as file_path,
               [node in nodes(path) | node.name] as hierarchy
        """
        
        with self._driver.session() as session:
            result = session.run(query, {"name": class_name})
            return [dict(record) for record in result]
            
    def find_imports(self, file_path: str) -> list[dict]:
        """
        Find all imports for a file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            List of imported modules
        """
        query = """
        MATCH (f:File)-[r:IMPORTS]->(m:Module)
        WHERE f.file_path CONTAINS $path
        RETURN m.name as module_name,
               r.line_number as line_number
        ORDER BY r.line_number
        """
        
        with self._driver.session() as session:
            result = session.run(query, {"path": file_path})
            return [dict(record) for record in result]
            
    def get_file_structure(self, file_path: str) -> dict:
        """
        Get the complete structure of a file (classes, functions).
        
        Args:
            file_path: Path to the file
            
        Returns:
            Dictionary with file structure
        """
        query = """
        MATCH (f:File)
        WHERE f.file_path CONTAINS $path
        OPTIONAL MATCH (f)-[:DECLARES]->(c:Class)
        OPTIONAL MATCH (c)-[:CONTAINS]->(m:Function)
        OPTIONAL MATCH (f)-[:DECLARES]->(fn:Function)
        WHERE NOT (fn)<-[:CONTAINS]-(:Class)
        RETURN f.name as file_name,
               f.file_path as file_path,
               collect(DISTINCT {name: c.name, methods: collect(m.name)}) as classes,
               collect(DISTINCT fn.name) as functions
        """
        
        with self._driver.session() as session:
            result = session.run(query, {"path": file_path})
            record = result.single()
            return dict(record) if record else {}
            
    def trace_dependency_path(
        self, 
        from_name: str, 
        to_name: str,
        max_depth: int = 5
    ) -> list[dict]:
        """
        Find the dependency path between two code elements.
        
        Args:
            from_name: Starting element name
            to_name: Target element name
            max_depth: Maximum path length
            
        Returns:
            List of paths found
        """
        query = f"""
        MATCH path = shortestPath((a)-[*1..{max_depth}]->(b))
        WHERE (a:Function OR a:Class) AND a.name CONTAINS $from_name
          AND (b:Function OR b:Class) AND b.name CONTAINS $to_name
        RETURN [node in nodes(path) | {{name: node.name, type: labels(node)[0]}}] as path,
               [rel in relationships(path) | type(rel)] as relationships,
               length(path) as depth
        """
        
        with self._driver.session() as session:
            result = session.run(query, {"from_name": from_name, "to_name": to_name})
            return [dict(record) for record in result]
            
    def get_statistics(self) -> dict:
        """Get statistics about the graph."""
        queries = {
            "files": "MATCH (n:File) RETURN count(n) as count",
            "classes": "MATCH (n:Class) RETURN count(n) as count",
            "functions": "MATCH (n:Function) RETURN count(n) as count",
            "modules": "MATCH (n:Module) RETURN count(n) as count",
            "imports": "MATCH ()-[r:IMPORTS]->() RETURN count(r) as count",
            "calls": "MATCH ()-[r:CALLS]->() RETURN count(r) as count",
            "inheritance": "MATCH ()-[r:INHERITS_FROM]->() RETURN count(r) as count"
        }
        
        stats = {}
        with self._driver.session() as session:
            for key, query in queries.items():
                result = session.run(query)
                record = result.single()
                stats[key] = record["count"] if record else 0
                
        return stats
        
    def clear(self) -> None:
        """Clear all data from the graph."""
        with self._driver.session() as session:
            session.run("MATCH (n) DETACH DELETE n")
        logger.info("Graph store cleared")
        
    @staticmethod
    def _type_to_label(node_type: str) -> str:
        """Convert node type to Neo4j label."""
        mapping = {
            "file": "File",
            "class": "Class",
            "function": "Function",
            "module": "Module"
        }
        return mapping.get(node_type, "Unknown")
    
    def __enter__(self):
        self.connect()
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
