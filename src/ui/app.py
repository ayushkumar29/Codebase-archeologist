import json
import logging
import os
import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.config import get_settings
from src.ingestion import CodeScanner, RelationshipExtractor
from src.brain import VectorStore, GraphStore
from src.agent import ArchaeologistAgent
from src.ui.components import (
    render_stats_cards,
    render_sidebar_ingestion,
    render_graph_visualization
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


st.set_page_config(
    page_title="Codebase Archaeologist",
    page_icon="🏛️",
    layout="wide",
    initial_sidebar_state="expanded"
)

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
    .main-header {
        background: linear-gradient(90deg, #4A90D9, #50C878);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 2.5rem;
        font-weight: bold;
        text-align: center;
        padding: 1rem 0;
    }
    .subtitle {
        text-align: center;
        color: #888;
        margin-bottom: 2rem;
    }
    .stChatMessage {
        background: rgba(255, 255, 255, 0.05);
        border-radius: 10px;
        padding: 1rem;
    }
</style>
""", unsafe_allow_html=True)


def init_session_state():
    if "messages" not in st.session_state:
        st.session_state.messages = []
        
    if "ingestion_status" not in st.session_state:
        st.session_state.ingestion_status = {}
        
    if "agent" not in st.session_state:
        st.session_state.agent = None
        
    if "vector_store" not in st.session_state:
        st.session_state.vector_store = None
        
    if "graph_store" not in st.session_state:
        st.session_state.graph_store = None
        
    if "stats" not in st.session_state:
        st.session_state.stats = {}


def ingest_codebase(path: str, languages: list[str]):
    with st.spinner("🔍 Scanning codebase..."):
        try:
            ext_map = {
                "Python": [".py"],
                "JavaScript": [".js", ".jsx"],
                "TypeScript": [".ts", ".tsx"]
            }
            
            extensions = []
            for lang in languages:
                extensions.extend(ext_map.get(lang, []))
                
            extractor = RelationshipExtractor()
            graph = extractor.process_codebase(path)
            
            st.session_state.ingestion_status = {
                "success": True,
                "files": len([n for n in graph.nodes.values() if n.type == "file"]),
                "scanning": "complete"
            }
            
        except Exception as e:
            st.session_state.ingestion_status = {
                "error": str(e)
            }
            st.error(f"Failed to scan codebase: {e}")
            return
            
    with st.spinner("🧠 Indexing into vector store..."):
        try:
            vector_store = VectorStore()
            vector_store.index_graph(graph)
            st.session_state.vector_store = vector_store
            
        except Exception as e:
            st.session_state.ingestion_status = {
                "error": f"Vector indexing failed: {e}"
            }
            st.error(f"Failed to index vectors: {e}")
            return
            
    with st.spinner("🔗 Building knowledge graph..."):
        try:
            graph_store = GraphStore()
            graph_store.connect()
            graph_store.clear()
            graph_store.index_graph(graph)
            st.session_state.graph_store = graph_store
            
            st.session_state.stats = graph_store.get_statistics()
            st.session_state.stats["vector_store_count"] = vector_store.count()
            
        except Exception as e:
            st.session_state.ingestion_status = {
                "error": f"Graph indexing failed: {e}"
            }
            st.error(f"Failed to build graph: {e}")
            return
            
    with st.spinner("🤖 Initializing agent..."):
        try:
            agent = ArchaeologistAgent(
                vector_store=vector_store,
                graph_store=graph_store
            )
            st.session_state.agent = agent
            
        except Exception as e:
            st.session_state.ingestion_status = {
                "error": f"Agent initialization failed: {e}"
            }
            st.error(f"Failed to initialize agent: {e}")
            return
            
    st.session_state.ingestion_status = {
        "success": True,
        "files": len([n for n in graph.nodes.values() if n.type == "file"])
    }
    st.success("✅ Codebase successfully indexed!")


def main():
    init_session_state()
    
    st.markdown('<h1 class="main-header">🏛️ The Codebase Archaeologist</h1>', unsafe_allow_html=True)
    st.markdown('<p class="subtitle">AI-powered code exploration using Knowledge Graphs</p>', unsafe_allow_html=True)
    
    render_sidebar_ingestion(ingest_codebase)
    
    tab1, tab2, tab3 = st.tabs(["💬 Chat", "📊 Graph", "📈 Stats"])
    
    with tab1:
        render_chat_tab()
        
    with tab2:
        render_graph_tab()
        
    with tab3:
        render_stats_tab()


def render_chat_tab():
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])
            
    if prompt := st.chat_input("Ask about the codebase...", key="chat_input"):
        if st.session_state.agent is None:
            st.warning("⚠️ Please ingest a codebase first using the sidebar.")
            return
            
        st.session_state.messages.append({"role": "user", "content": prompt})
        
        with st.chat_message("user"):
            st.markdown(prompt)
            
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    response = st.session_state.agent.query(prompt)
                    st.markdown(response)
                    st.session_state.messages.append({"role": "assistant", "content": response})
                except Exception as e:
                    error_msg = f"Error: {str(e)}"
                    st.error(error_msg)
                    st.session_state.messages.append({"role": "assistant", "content": error_msg})


def render_graph_tab():
    if st.session_state.graph_store is None:
        st.info("📊 Ingest a codebase to see the dependency graph.")
        return
        
    st.subheader("Dependency Graph Visualization")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        focus_element = st.text_input(
            "Focus on element (optional)",
            placeholder="Enter function or class name",
            help="Filter the graph to show relationships for a specific element"
        )
        
    with col2:
        max_depth = st.slider("Max depth", 1, 5, 2)
        
    st.info("🚧 Interactive graph visualization coming soon!")
    st.markdown("""
    The graph will show:
    - **Blue nodes**: Files
    - **Green nodes**: Classes  
    - **Orange nodes**: Functions
    - **Purple nodes**: External modules
    
    **Edges** represent:
    - IMPORTS
    - CALLS
    - INHERITS_FROM
    - CONTAINS
    """)


def render_stats_tab():
    if not st.session_state.stats:
        st.info("📈 Ingest a codebase to see statistics.")
        return
        
    st.subheader("Codebase Statistics")
    render_stats_cards(st.session_state.stats)
    
    st.divider()
    st.subheader("Quick Insights")
    
    stats = st.session_state.stats
    
    if stats.get("functions", 0) > 0:
        avg_calls = stats.get("calls", 0) / stats.get("functions", 1)
        st.metric("Avg calls per function", f"{avg_calls:.1f}")
        
    if stats.get("classes", 0) > 0:
        st.metric("Classes with inheritance", stats.get("inheritance", 0))


if __name__ == "__main__":
    main()
