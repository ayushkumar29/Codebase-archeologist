import streamlit as st
from streamlit_agraph import agraph, Node, Edge, Config


def render_graph_visualization(graph_data: dict):
    nodes = []
    edges = []
    
    colors = {
        "file": "#4A90D9",
        "class": "#50C878",
        "function": "#FFB347",
        "module": "#DDA0DD"
    }
    
    sizes = {
        "file": 25,
        "class": 20,
        "function": 15,
        "module": 20
    }
    
    for node in graph_data.get("nodes", []):
        node_type = node.get("type", "unknown")
        nodes.append(Node(
            id=node["id"],
            label=node.get("name", node["id"])[:30],
            size=sizes.get(node_type, 15),
            color=colors.get(node_type, "#888888"),
            title=f"{node_type}: {node.get('name', '')}\n{node.get('file_path', '')}"
        ))
        
    for edge in graph_data.get("edges", []):
        edges.append(Edge(
            source=edge["source"],
            target=edge["target"],
            label=edge.get("type", ""),
            color="#666666"
        ))
        
    config = Config(
        width=800,
        height=500,
        directed=True,
        physics=True,
        hierarchical=False,
        nodeHighlightBehavior=True,
        highlightColor="#F7A7A6",
        collapsible=False
    )
    
    return agraph(nodes=nodes, edges=edges, config=config)


def render_code_result(result: dict):
    node_type = result.get("type", "unknown")
    name = result.get("name", "Unknown")
    file_path = result.get("file", "Unknown")
    line = result.get("line", 0)
    similarity = result.get("similarity", 0)
    docstring = result.get("docstring", "")
    
    type_colors = {
        "function": "🟠",
        "class": "🟢",
        "file": "🔵",
        "module": "🟣"
    }
    
    badge = type_colors.get(node_type, "⚪")
    
    with st.container():
        col1, col2 = st.columns([3, 1])
        
        with col1:
            st.markdown(f"### {badge} `{name}`")
            
        with col2:
            if similarity:
                st.metric("Similarity", f"{similarity:.1%}")
                
        st.caption(f"📁 `{file_path}` : Line {line}")
        
        if docstring:
            st.markdown(f"> {docstring}")
            
        st.divider()


def render_stats_cards(stats: dict):
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric("📁 Files", stats.get("files", 0))
        
    with col2:
        st.metric("📦 Classes", stats.get("classes", 0))
        
    with col3:
        st.metric("⚡ Functions", stats.get("functions", 0))
        
    with col4:
        st.metric("📚 Modules", stats.get("modules", 0))
        
    col5, col6, col7, col8 = st.columns(4)
    
    with col5:
        st.metric("📥 Imports", stats.get("imports", 0))
        
    with col6:
        st.metric("📞 Calls", stats.get("calls", 0))
        
    with col7:
        st.metric("🔗 Inheritance", stats.get("inheritance", 0))
        
    with col8:
        st.metric("🧠 Embeddings", stats.get("vector_store_count", 0))


def render_chat_message(role: str, content: str):
    if role == "user":
        st.chat_message("user").markdown(content)
    else:
        st.chat_message("assistant").markdown(content)


def render_sidebar_ingestion(on_ingest_callback):
    with st.sidebar:
        st.header("🏛️ Codebase Ingestion")
        
        codebase_path = st.text_input(
            "Codebase Path",
            placeholder="C:/path/to/your/codebase",
            help="Enter the absolute path to the codebase you want to analyze"
        )
        
        language_filter = st.multiselect(
            "Languages",
            options=["Python", "JavaScript", "TypeScript"],
            default=["Python"],
            help="Select which languages to parse"
        )
        
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button("🔍 Ingest", type="primary", use_container_width=True):
                if codebase_path:
                    on_ingest_callback(codebase_path, language_filter)
                else:
                    st.error("Please enter a codebase path")
                    
        with col2:
            if st.button("🗑️ Clear", use_container_width=True):
                if "messages" in st.session_state:
                    st.session_state.messages = []
                st.rerun()
                
        st.divider()
        
        if "ingestion_status" in st.session_state:
            status = st.session_state.ingestion_status
            if status.get("success"):
                st.success(f"✅ Indexed {status.get('files', 0)} files")
            elif status.get("error"):
                st.error(f"❌ {status.get('error')}")
                
        st.divider()
        st.caption("💡 Example queries:")
        st.markdown("""
        - *"What does function X do?"*
        - *"Who calls authenticate_user?"*
        - *"Show the class hierarchy for BaseModel"*
        - *"Trace the path from login to database"*
        """)

        return codebase_path, language_filter
