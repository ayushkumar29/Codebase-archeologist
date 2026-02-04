"""
Agent Workflow - LangGraph-based agent for code analysis.
"""

import logging
from typing import Annotated, TypedDict, Sequence

from langchain_core.messages import BaseMessage, HumanMessage, AIMessage, ToolMessage
from langchain_openai import ChatOpenAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from src.config import get_settings
from src.brain.graph_store import GraphStore
from src.brain.vector_store import VectorStore
from .tools import create_tools

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    """State for the agent graph."""
    messages: Annotated[Sequence[BaseMessage], lambda x, y: list(x) + list(y)]
    
    
class ArchaeologistAgent:
    """
    The Codebase Archaeologist Agent.
    
    Uses LangGraph to orchestrate between semantic search and graph queries
    to answer questions about codebases.
    """
    
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
        """
        Initialize the agent.
        
        Args:
            vector_store: VectorStore instance
            graph_store: GraphStore instance
            model_name: OpenAI model to use
        """
        settings = get_settings()
        self.model_name = model_name or settings.openai_model
        
        self.vector_store = vector_store
        self.graph_store = graph_store
        
        # Create tools
        self.tools = create_tools(vector_store, graph_store)
        
        # Create LLM with tools
        self.llm = ChatOpenAI(
            api_key=settings.openai_api_key,
            model=self.model_name,
            temperature=0
        ).bind_tools(self.tools)
        
        # Build the graph
        self.graph = self._build_graph()
        
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow."""
        
        # Create the graph
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("agent", self._agent_node)
        workflow.add_node("tools", ToolNode(self.tools))
        
        # Set entry point
        workflow.set_entry_point("agent")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "agent",
            self._should_continue,
            {
                "continue": "tools",
                "end": END
            }
        )
        
        # Tools always go back to agent
        workflow.add_edge("tools", "agent")
        
        # Compile
        return workflow.compile()
    
    def _agent_node(self, state: AgentState) -> dict:
        """The main agent node that calls the LLM."""
        messages = state["messages"]
        
        # Add system prompt if this is the first message
        if len(messages) == 1 and isinstance(messages[0], HumanMessage):
            response = self.llm.invoke([
                {"role": "system", "content": self.SYSTEM_PROMPT},
                *messages
            ])
        else:
            response = self.llm.invoke(messages)
            
        return {"messages": [response]}
    
    def _should_continue(self, state: AgentState) -> str:
        """Determine if we should continue to tools or end."""
        last_message = state["messages"][-1]
        
        # If the LLM made tool calls, continue to tools node
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return "continue"
            
        return "end"
    
    def query(self, question: str) -> str:
        """
        Ask a question about the codebase.
        
        Args:
            question: Natural language question
            
        Returns:
            Agent's response
        """
        logger.info(f"Query: {question}")
        
        # Run the graph
        result = self.graph.invoke({
            "messages": [HumanMessage(content=question)]
        })
        
        # Extract final response
        final_message = result["messages"][-1]
        
        if isinstance(final_message, AIMessage):
            return final_message.content
            
        return str(final_message)
    
    def chat(self, messages: list[dict]) -> str:
        """
        Have a multi-turn conversation.
        
        Args:
            messages: List of {"role": "user"|"assistant", "content": str}
            
        Returns:
            Agent's response to the last message
        """
        # Convert to LangChain messages
        lc_messages = []
        for msg in messages:
            if msg["role"] == "user":
                lc_messages.append(HumanMessage(content=msg["content"]))
            else:
                lc_messages.append(AIMessage(content=msg["content"]))
                
        # Run the graph
        result = self.graph.invoke({"messages": lc_messages})
        
        # Extract final response
        final_message = result["messages"][-1]
        
        if isinstance(final_message, AIMessage):
            return final_message.content
            
        return str(final_message)
