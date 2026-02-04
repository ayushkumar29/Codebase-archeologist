import logging
from typing import Annotated, TypedDict, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_ollama import ChatOllama
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from src.config import get_settings
from src.brain.graph_store import GraphStore
from src.brain.vector_store import VectorStore
from .tools import create_tools

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], lambda x, y: list(x) + list(y)]
    
    
class ArchaeologistAgent:
    
    SYSTEM_PROMPT = """You are The Codebase Archaeologist, an AI expert at understanding 
and explaining legacy codebases. You have access to two types of search capabilities:

1. **Semantic Search** (vector-based): Find code by meaning. Use when asked 
   "what does X do?" or "find code that handles Y".

2. **Graph Search** (relationship-based): Find structural relationships. Use when asked:
   - "Who calls function X?" → use find_function_callers
   - "What does function X call?" → use find_function_calls
   - "What's the class hierarchy?" → use find_class_inheritance
   - "How does X connect to Y?" → use trace_dependency_path
   - "What does this file import?" → use get_file_imports
   - "What's in this file?" → use get_file_structure

When answering questions:
1. First, determine if this is a semantic question (about meaning) or structural (about relationships)
2. Use the appropriate tool(s) to gather information
3. Synthesize a clear, helpful response that includes:
   - Direct answer to the question
   - Relevant code locations (file paths and line numbers)
   - Context about how pieces connect

Be thorough but concise. If you can't find something, say so clearly.
"""
    
    def __init__(
        self,
        vector_store: VectorStore,
        graph_store: GraphStore,
        model_name: str = None
    ):
        settings = get_settings()
        self.model_name = model_name or settings.ollama_model
        
        self.vector_store = vector_store
        self.graph_store = graph_store
        
        self.tools = create_tools(vector_store, graph_store)
        
        self.llm = ChatOllama(
            base_url=settings.ollama_base_url,
            model=self.model_name,
            temperature=0
        ).bind_tools(self.tools)
        
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        
        workflow = StateGraph(AgentState)
        
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        
        workflow.set_entry_point("agent")
        
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        
        workflow.add_edge("tools", "agent")
        
        return workflow.compile()
    
    def _agent_node(self, state: AgentState) -> dict:
        messages = state["messages"]
        
        if len(messages) == 1 and isinstance(messages[0], HumanMessage):
            response = self.llm.invoke([
                {"role": "system", "content": self.SYSTEM_PROMPT},
                *messages
            ])
        else:
            response = self.llm.invoke(messages)
            
        return {"messages": [response]}
    
    def _should_continue(self, state: AgentState) -> str:
        last_message = state["messages"][-1]
        
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
            
        return "end"
    
    def query(self, question: str) -> str:
        logger.info(f"Query: {question}")
        
        result = self.graph.invoke({
            "messages": [HumanMessage(content=question)]
        })
        
        final_message = result["messages"][-1]
        
        if isinstance(final_message, AIMessage):
            return final_message.content
            
        return str(final_message)
    
    def chat(self, messages: list[dict]) -> str:
        lc_messages = []
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            else:
                lc_messages.append(AIMessage(content=msg["content"]))
                
        result = self.graph.invoke({"messages": lc_messages})
        
        final_message = result["messages"][-1]
        
        if isinstance(final_message, AIMessage):
            return final_message.content
            
        return str(final_message)
