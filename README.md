# 🏛️ The Codebase Archaeologist

> An AI Agent that maps, traces, and documents legacy codebases automatically.

![Architecture](https://img.shields.io/badge/Architecture-Hybrid_Search-blue)
![Python](https://img.shields.io/badge/Python-3.10+-green)
![Local](https://img.shields.io/badge/100%25-Local-orange)

## 🎯 What is this?

Most "Chat with Code" tools just dump file contents into a vector database. If you ask, "Where is the user validated?", they look for the word "validate."

**The Archaeologist is smarter.** It parses the code into a **Dependency Graph**. It knows that `login.py` imports `auth.py`, which calls `db_connector.py`. It "thinks" like a Senior Engineer tracing a bug.

### Primary Use Case

Onboarding new developers to a massive, undocumented 10-year-old codebase.

### 🔒 100% Local - No API Keys Needed!

- **LLM**: Ollama (runs locally)
- **Embeddings**: sentence-transformers (local)
- **Databases**: Neo4j + ChromaDB (local)

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Streamlit UI                              │
│              (Chat + Graph Visualization)                    │
└────────────────────────┬────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────┐
│              LangGraph Agent + Ollama (Local)                │
│         (Query Router + Tool Orchestration)                  │
└───────────┬─────────────────────────────────┬───────────────┘
            │                                 │
┌───────────▼───────────┐        ┌───────────▼───────────┐
│    Vector Store       │        │     Graph Store       │
│     (ChromaDB)        │        │      (Neo4j)          │
│  Local Embeddings     │        │                       │
│  "What does X do?"    │        │  "Who calls X?"       │
└───────────────────────┘        └───────────────────────┘
```

## 🚀 Quick Start

### 1. Prerequisites

- Python 3.10+
- Docker (for Neo4j)
- **Ollama** (for local LLM): https://ollama.com/download

### 2. Install Ollama & Download Model

```bash
# After installing Ollama, download a model
ollama pull llama3.2
```

### 3. Installation

```bash
# Clone the repo
git clone <repo-url>
cd codebase-archaeologist

# Create virtual environment
python -m venv .venv
.venv\Scripts\activate  # Windows
# source .venv/bin/activate  # Linux/Mac

# Install dependencies
pip install -r requirements.txt
```

### 4. Configuration

```bash
# Copy environment template (no API keys needed!)
copy .env.example .env
```

### 5. Start Neo4j

```bash
docker-compose up -d
```

### 6. Run the App

```bash
streamlit run src/ui/app.py
```

## 💬 Example Queries

| Query Type | Example |
|------------|---------|
| **Semantic** | "What does the authentication module do?" |
| **Callers** | "Who calls the `validate_user` function?" |
| **Callees** | "What functions does `process_order` call?" |
| **Inheritance** | "Show the class hierarchy for `BaseModel`" |
| **Trace** | "How does `login` connect to `database`?" |
| **Structure** | "What's in the `utils.py` file?" |

## 📁 Project Structure

```
codebase-archaeologist/
├── src/
│   ├── ingestion/       # Code parsing & relationship extraction
│   │   ├── scanner.py   # File discovery
│   │   ├── parser.py    # AST parsing (Python)
│   │   └── extractor.py # Relationship extraction
│   │
│   ├── brain/           # Database layer
│   │   ├── embeddings.py    # OpenAI embeddings
│   │   ├── vector_store.py  # ChromaDB operations
│   │   └── graph_store.py   # Neo4j operations
│   │
│   ├── agent/           # LangGraph agent
│   │   ├── tools.py     # Search tools
│   │   └── workflow.py  # Agent workflow
│   │
│   └── ui/              # Streamlit interface
│       ├── app.py       # Main app
│       └── components.py
│
├── tests/               # Test suite
├── docker-compose.yml   # Neo4j container
└── requirements.txt
```

## 🔧 How It Works

### 1. Ingestion Engine

The **Scanner** finds all source files, the **Parser** extracts classes/functions/imports using AST, and the **Extractor** identifies relationships:

- `IMPORTS` - file imports a module
- `CALLS` - function calls another function
- `INHERITS_FROM` - class extends another
- `DECLARES` - file declares a class/function
- `CONTAINS` - class contains a method

### 2. Dual Database Storage

- **ChromaDB (Vector)**: Stores embeddings of code snippets for semantic similarity search
- **Neo4j (Graph)**: Stores the dependency graph for structural queries

### 3. LangGraph Agent

The agent routes queries to the appropriate tool:

- Semantic questions → Vector search
- Structural questions → Graph queries
- Complex questions → Hybrid approach

## 🧪 Testing

```bash
# Run all tests
pytest tests/ -v

# Test parser only
pytest tests/test_parser.py -v
```

## 📝 License

MIT

## 🤝 Contributing

Contributions welcome! Please read our contributing guidelines first.
