from langgraph.graph import StateGraph, END
from agents.services.gemini_service import GeminiLLM
from typing import TypedDict, Literal
from agents.services.vanna_t2sql import VannaT2SQLService
from agents.services.document_rag import DocumentRAGService
from django.conf import settings
import logging

logger = logging.getLogger(__name__)


class AgentState(TypedDict):
    query: str
    task_type: Literal["t2sql", "rag", "unknown"]
    sql_result: str
    rag_result: str
    final_response: str
    error: str


class LangGraphAgent:
    """LangGraph agent that routes between T2SQL and Document RAG"""
    
    def __init__(self):
        self.llm = GeminiLLM(
            model_name=settings.GEMINI_MODEL,
            temperature=0,
        )
        self.t2sql_service = VannaT2SQLService()
        self.rag_service = DocumentRAGService()
        self.graph = self._build_graph()
    
    def _build_graph(self) -> StateGraph:
        """Build the LangGraph workflow"""
        workflow = StateGraph(AgentState)
        
        # Add nodes
        workflow.add_node("router", self._route_query)
        workflow.add_node("t2sql", self._handle_t2sql)
        workflow.add_node("rag", self._handle_rag)
        workflow.add_node("synthesize", self._synthesize_response)
        
        # Set entry point
        workflow.set_entry_point("router")
        
        # Add conditional edges
        workflow.add_conditional_edges(
            "router",
            self._should_use_t2sql,
            {
                "t2sql": "t2sql",
                "rag": "rag",
            }
        )
        
        # Add edges from task nodes to synthesize
        workflow.add_edge("t2sql", "synthesize")
        workflow.add_edge("rag", "synthesize")
        
        # End after synthesis
        workflow.add_edge("synthesize", END)
        
        return workflow.compile()
    
    def _route_query(self, state: AgentState) -> AgentState:
        """Route query to appropriate handler"""
        query = state["query"].lower()
        
        # Simple keyword-based routing
        sql_keywords = [
            "count", "select", "how many", "list", "show", "find", "filter",
            "leads", "campaigns", "database", "query", "statistics"
        ]
        
        rag_keywords = [
            "features", "amenities", "facilities", "property", "project",
            "brochure", "details", "information", "what", "tell me about"
        ]
        
        sql_score = sum(1 for keyword in sql_keywords if keyword in query)
        rag_score = sum(1 for keyword in rag_keywords if keyword in query)
        
        if sql_score > rag_score:
            state["task_type"] = "t2sql"
        elif rag_score > 0:
            state["task_type"] = "rag"
        else:
            # Use LLM to determine
            prompt = f"""
            Determine if this query should use Text-to-SQL (database queries) or Document RAG (brochure information):
            
            Query: {state['query']}
            
            Respond with only "t2sql" or "rag"
            """
            try:
                response = self.llm.invoke(prompt)
                state["task_type"] = response.content.strip().lower()
            except:
                state["task_type"] = "rag"  # Default to RAG
        
        return state
    
    def _should_use_t2sql(self, state: AgentState) -> str:
        """Determine which path to take"""
        return state.get("task_type", "rag")
    
    def _handle_t2sql(self, state: AgentState) -> AgentState:
        """Handle Text-to-SQL query"""
        try:
            response = self.t2sql_service.generate_response(state["query"])
            state["sql_result"] = response
            state["final_response"] = response
        except Exception as e:
            state["error"] = str(e)
            state["final_response"] = f"I encountered an error processing your database query: {str(e)}"
        return state
    
    def _handle_rag(self, state: AgentState) -> AgentState:
        """Handle Document RAG query"""
        try:
            rag_result = self.rag_service.query(state["query"])
            
            # Use LLM to synthesize a natural response
            prompt = f"""
            Based on the following information from project brochures, provide a clear and helpful answer to the user's question.
            
            User Question: {state['query']}
            
            Retrieved Information:
            {rag_result}
            
            Provide a natural, conversational response that directly answers the question.
            """
            
            response = self.llm.invoke(prompt)
            state["rag_result"] = rag_result
            state["final_response"] = response.content
        except Exception as e:
            state["error"] = str(e)
            state["final_response"] = f"I encountered an error retrieving information: {str(e)}"
        return state
    
    def _synthesize_response(self, state: AgentState) -> AgentState:
        """Synthesize final response"""
        # Response is already set in task handlers
        return state
    
    def query(self, user_query: str) -> str:
        """Process a user query"""
        initial_state = {
            "query": user_query,
            "task_type": "unknown",
            "sql_result": "",
            "rag_result": "",
            "final_response": "",
            "error": "",
        }
        
        try:
            result = self.graph.invoke(initial_state)
            return result.get("final_response", "I'm sorry, I couldn't process your query.")
        except Exception as e:
            logger.error(f"Error in agent query: {str(e)}")
            return f"I encountered an error: {str(e)}"

