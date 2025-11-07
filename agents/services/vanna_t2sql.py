import vanna as vn
from vanna.base import VannaBase
import chromadb
from chromadb.config import Settings
from django.conf import settings
from django.db import connection
from agents.services.gemini_service import GeminiEmbeddings, GeminiLLM
import logging
from typing import List, Optional
import os

logger = logging.getLogger(__name__)

# Disable ChromaDB telemetry to prevent errors
os.environ.setdefault('ANONYMIZED_TELEMETRY', 'False')
os.environ.setdefault('CHROMA_TELEMETRY_DISABLED', 'True')


class ChromaDBVanna(VannaBase):
    """Custom Vanna implementation using ChromaDB for training data storage"""
    
    def __init__(self, config=None):
        super().__init__(config=config)
        # Initialize ChromaDB client with telemetry disabled
        chroma_settings = Settings(
            anonymized_telemetry=False,
            allow_reset=True,
        )
        
        self.chroma_client = chromadb.PersistentClient(
            path=str(settings.CHROMA_DB_PATH / 'vanna'),
            settings=chroma_settings
        )
        self.collection_name = "vanna_training_data"
        
        # Initialize embeddings for semantic search
        try:
            self.embeddings = GeminiEmbeddings(model_name=settings.GEMINI_EMBEDDING_MODEL)
            self.llm = GeminiLLM(model_name=settings.GEMINI_MODEL, temperature=0)
        except Exception as e:
            logger.warning(f"Could not initialize Gemini for Vanna: {str(e)}")
            self.embeddings = None
            self.llm = None
        
        # Get or create collection
        try:
            self.collection = self.chroma_client.get_collection(name=self.collection_name)
        except:
            self.collection = self.chroma_client.create_collection(name=self.collection_name)
    
    def train(self, **kwargs) -> str:
        """Train Vanna with DDL, documentation, or SQL examples"""
        if 'ddl' in kwargs:
            return self.train_ddl(kwargs['ddl'])
        elif 'documentation' in kwargs:
            return self.train_documentation(kwargs['documentation'])
        elif 'sql' in kwargs:
            return self.train_sql(kwargs['sql'])
        else:
            raise ValueError("Must provide 'ddl', 'documentation', or 'sql'")
    
    def train_ddl(self, ddl: str) -> str:
        """Store DDL in ChromaDB with embeddings"""
        try:
            existing_ids = self.collection.get()['ids']
            doc_id = f"ddl_{len(existing_ids)}"
            
            # Generate embedding if available
            embeddings = None
            if self.embeddings:
                try:
                    embeddings = [self.embeddings.embed_query(ddl)]
                except:
                    pass
            
            if embeddings:
                self.collection.add(
                    documents=[ddl],
                    metadatas=[{"type": "ddl"}],
                    ids=[doc_id],
                    embeddings=embeddings
                )
            else:
                self.collection.add(
                    documents=[ddl],
                    metadatas=[{"type": "ddl"}],
                    ids=[doc_id]
                )
            logger.info(f"Stored DDL in ChromaDB: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error storing DDL: {str(e)}")
            raise
    
    def train_documentation(self, documentation: str) -> str:
        """Store documentation in ChromaDB with embeddings"""
        try:
            existing_ids = self.collection.get()['ids']
            doc_id = f"doc_{len(existing_ids)}"
            
            # Generate embedding if available
            embeddings = None
            if self.embeddings:
                try:
                    embeddings = [self.embeddings.embed_query(documentation)]
                except:
                    pass
            
            if embeddings:
                self.collection.add(
                    documents=[documentation],
                    metadatas=[{"type": "documentation"}],
                    ids=[doc_id],
                    embeddings=embeddings
                )
            else:
                self.collection.add(
                    documents=[documentation],
                    metadatas=[{"type": "documentation"}],
                    ids=[doc_id]
                )
            logger.info(f"Stored documentation in ChromaDB: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error storing documentation: {str(e)}")
            raise
    
    def train_sql(self, sql: str, question: Optional[str] = None) -> str:
        """Store SQL example in ChromaDB with embeddings"""
        try:
            existing_ids = self.collection.get()['ids']
            doc_id = f"sql_{len(existing_ids)}"
            metadata = {"type": "sql"}
            if question:
                metadata["question"] = question
            
            # Use question for embedding if available, otherwise use SQL
            embedding_text = question if question else sql
            
            # Generate embedding if available
            embeddings = None
            if self.embeddings:
                try:
                    embeddings = [self.embeddings.embed_query(embedding_text)]
                except:
                    pass
            
            if embeddings:
                self.collection.add(
                    documents=[sql],
                    metadatas=[metadata],
                    ids=[doc_id],
                    embeddings=embeddings
                )
            else:
                self.collection.add(
                    documents=[sql],
                    metadatas=[metadata],
                    ids=[doc_id]
                )
            logger.info(f"Stored SQL example in ChromaDB: {doc_id}")
            return doc_id
        except Exception as e:
            logger.error(f"Error storing SQL: {str(e)}")
            raise
    
    def get_training_data(self) -> dict:
        """Retrieve all training data from ChromaDB"""
        try:
            results = self.collection.get()
            return {
                'ddl': [doc for doc, meta in zip(results['documents'], results['metadatas']) if meta.get('type') == 'ddl'],
                'documentation': [doc for doc, meta in zip(results['documents'], results['metadatas']) if meta.get('type') == 'documentation'],
                'sql': [doc for doc, meta in zip(results['documents'], results['metadatas']) if meta.get('type') == 'sql'],
            }
        except Exception as e:
            logger.error(f"Error retrieving training data: {str(e)}")
            return {'ddl': [], 'documentation': [], 'sql': []}
    
    # Abstract method implementations required by VannaBase
    def add_ddl(self, ddl: str) -> str:
        """Add DDL - alias for train_ddl"""
        return self.train_ddl(ddl)
    
    def add_documentation(self, documentation: str) -> str:
        """Add documentation - alias for train_documentation"""
        return self.train_documentation(documentation)
    
    def add_question_sql(self, question: str, sql: str) -> str:
        """Add question-SQL pair - alias for train_sql"""
        return self.train_sql(sql, question)
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text"""
        if self.embeddings:
            try:
                return self.embeddings.embed_query(text)
            except Exception as e:
                logger.error(f"Error generating embedding: {str(e)}")
        return []
    
    def get_related_ddl(self, question: str, **kwargs) -> List[str]:
        """Get related DDL based on question"""
        try:
            if self.embeddings:
                query_embedding = self.generate_embedding(question)
                if query_embedding:
                    results = self.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=kwargs.get('n_results', 3),
                        where={"type": "ddl"}
                    )
                    if results['documents'] and len(results['documents'][0]) > 0:
                        return results['documents'][0]
            # Fallback: return all DDL
            training_data = self.get_training_data()
            return training_data.get('ddl', [])
        except Exception as e:
            logger.error(f"Error getting related DDL: {str(e)}")
            return []
    
    def get_related_documentation(self, question: str, **kwargs) -> List[str]:
        """Get related documentation based on question"""
        try:
            if self.embeddings:
                query_embedding = self.generate_embedding(question)
                if query_embedding:
                    results = self.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=kwargs.get('n_results', 3),
                        where={"type": "documentation"}
                    )
                    if results['documents'] and len(results['documents'][0]) > 0:
                        return results['documents'][0]
            # Fallback: return all documentation
            training_data = self.get_training_data()
            return training_data.get('documentation', [])
        except Exception as e:
            logger.error(f"Error getting related documentation: {str(e)}")
            return []
    
    def get_similar_question_sql(self, question: str, **kwargs) -> List[dict]:
        """Get similar question-SQL pairs"""
        try:
            if self.embeddings:
                query_embedding = self.generate_embedding(question)
                if query_embedding:
                    results = self.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=kwargs.get('n_results', 3),
                        where={"type": "sql"}
                    )
                    if results['documents'] and len(results['documents'][0]) > 0:
                        pairs = []
                        documents = results['documents'][0]
                        metadatas = results.get('metadatas', [[]])[0] if results.get('metadatas') else []
                        for i, doc in enumerate(documents):
                            meta = metadatas[i] if i < len(metadatas) else {}
                            pairs.append({
                                'question': meta.get('question', '') if isinstance(meta, dict) else '',
                                'sql': doc
                            })
                        return pairs
            # Fallback: return all SQL examples
            training_data = self.get_training_data()
            return [{'question': '', 'sql': sql} for sql in training_data.get('sql', [])]
        except Exception as e:
            logger.error(f"Error getting similar question SQL: {str(e)}")
            return []
    
    def remove_training_data(self, id: str) -> bool:
        """Remove training data by ID"""
        try:
            self.collection.delete(ids=[id])
            return True
        except Exception as e:
            logger.error(f"Error removing training data: {str(e)}")
            return False
    
    def submit_prompt(self, prompt: str, **kwargs) -> str:
        """Submit prompt to LLM"""
        if self.llm:
            try:
                response = self.llm.invoke(prompt)
                return response.content if hasattr(response, 'content') else str(response)
            except Exception as e:
                logger.error(f"Error submitting prompt: {str(e)}")
                return ""
        return ""
    
    def system_message(self, message: str) -> str:
        """System message - returns the message"""
        return message
    
    def user_message(self, message: str) -> str:
        """User message - returns the message"""
        return message
    
    def assistant_message(self, message: str) -> str:
        """Assistant message - returns the message"""
        return message


class VannaT2SQLService:
    """Vanna Text-to-SQL service using ChromaDB for training data"""
    
    def __init__(self):
        # Initialize Vanna with ChromaDB backend
        self.vanna_model = ChromaDBVanna()
        
        # Set up database connection method
        self.vanna_model.run_sql = self._run_sql
        
        # Initialize training data if needed
        self._initialize_training_data()
    
    def _run_sql(self, sql: str):
        """Execute SQL query against Django database"""
        try:
            with connection.cursor() as cursor:
                cursor.execute(sql)
                if sql.strip().upper().startswith('SELECT'):
                    columns = [col[0] for col in cursor.description] if cursor.description else []
                    rows = cursor.fetchall()
                    return [dict(zip(columns, row)) for row in rows] if columns else rows
                else:
                    return {"rows_affected": cursor.rowcount}
        except Exception as e:
            logger.error(f"Error executing SQL: {str(e)}")
            raise
    
    def _initialize_training_data(self):
        """Initialize Vanna with DDL and example queries stored in ChromaDB"""
        try:
            # Check if training data already exists
            training_data = self.vanna_model.get_training_data()
            if training_data['ddl'] or training_data['sql']:
                logger.info("Training data already exists in ChromaDB")
                return
            
            # Get DDL from database
            ddl = self._get_ddl()
            if ddl:
                self.vanna_model.train_ddl(ddl)
            
            # Add example SQL queries
            examples = [
                ("SELECT * FROM crm_leads WHERE lead_status = 'connected'", 
                 "Show all leads with connected status"),
                ("SELECT COUNT(*) as count FROM crm_leads WHERE project_name = 'Lumina Grand'", 
                 "How many leads are interested in Lumina Grand?"),
                ("SELECT lead_name, email FROM crm_leads WHERE min_budget > 5000000", 
                 "List leads with minimum budget above 5 million"),
                ("SELECT project_name, COUNT(*) as count FROM crm_leads GROUP BY project_name", 
                 "Count leads by project name"),
            ]
            
            for sql, question in examples:
                try:
                    self.vanna_model.train_sql(sql, question)
                except Exception as e:
                    logger.warning(f"Could not train SQL example: {str(e)}")
                    
        except Exception as e:
            logger.warning(f"Could not initialize Vanna training data: {str(e)}")
    
    def _get_ddl(self) -> str:
        """Get DDL from SQLite database"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT sql FROM sqlite_master WHERE type='table'")
                tables = cursor.fetchall()
                ddl = "\n".join([table[0] for table in tables if table[0]])
                return ddl
        except Exception as e:
            logger.error(f"Error getting DDL: {str(e)}")
            return ""
    
    def generate_sql(self, natural_language_query: str) -> str:
        """Generate SQL from natural language query using semantic search in ChromaDB"""
        try:
            # Get training data from ChromaDB
            training_data = self.vanna_model.get_training_data()
            
            # If we have embeddings, use semantic search
            if self.vanna_model.embeddings:
                try:
                    # Generate query embedding
                    query_embedding = self.vanna_model.embeddings.embed_query(natural_language_query)
                    
                    # Search for similar SQL examples
                    results = self.vanna_model.collection.query(
                        query_embeddings=[query_embedding],
                        n_results=3,
                        where={"type": "sql"}
                    )
                    
                    if results['documents'] and len(results['documents'][0]) > 0:
                        # Use LLM to generate SQL based on similar examples
                        similar_sql = "\n".join(results['documents'][0])
                        ddl = "\n".join(training_data['ddl']) if training_data['ddl'] else ""
                        
                        prompt = f"""
                        Based on the database schema and similar SQL examples, generate SQL for this query:
                        
                        Database Schema (DDL):
                        {ddl}
                        
                        Similar SQL Examples:
                        {similar_sql}
                        
                        User Query: {natural_language_query}
                        
                        Generate only the SQL query, no explanation.
                        """
                        
                        if self.vanna_model.llm:
                            response = self.vanna_model.llm.invoke(prompt)
                            sql = response.content.strip()
                            # Clean up SQL (remove markdown code blocks if present)
                            if sql.startswith("```"):
                                sql = sql.split("```")[1]
                                if sql.startswith("sql"):
                                    sql = sql[3:]
                            return sql.strip()
                except Exception as e:
                    logger.warning(f"Semantic search failed, using pattern matching: {str(e)}")
            
            # Fallback to pattern matching
            query_lower = natural_language_query.lower()
            
            if 'count' in query_lower and 'lead' in query_lower:
                if 'connected' in query_lower:
                    return "SELECT COUNT(*) FROM crm_leads WHERE lead_status = 'connected'"
                elif 'project' in query_lower:
                    return "SELECT project_name, COUNT(*) as count FROM crm_leads GROUP BY project_name"
                else:
                    return "SELECT COUNT(*) FROM crm_leads"
            elif 'list' in query_lower or 'show' in query_lower:
                if 'budget' in query_lower:
                    return "SELECT lead_name, email, min_budget, max_budget FROM crm_leads"
                else:
                    return "SELECT * FROM crm_leads LIMIT 10"
            else:
                # Fallback to a simple query
                return "SELECT * FROM crm_leads LIMIT 10"
                
        except Exception as e:
            logger.error(f"Error generating SQL: {str(e)}")
            raise
    
    def run_sql(self, sql: str):
        """Execute SQL query"""
        return self._run_sql(sql)
    
    def generate_response(self, natural_language_query: str) -> str:
        """Generate natural language response from query"""
        try:
            # Generate SQL
            sql = self.generate_sql(natural_language_query)
            
            # Execute SQL
            results = self.run_sql(sql)
            
            # Format response
            if isinstance(results, list) and len(results) > 0:
                if len(results) == 1 and 'count' in str(results[0]).lower():
                    count = list(results[0].values())[0] if isinstance(results[0], dict) else results[0][0]
                    return f"The query returned {count} result(s)."
                else:
                    return f"Query executed successfully. Found {len(results)} result(s)."
            else:
                return "Query executed successfully, but no results were returned."
                
        except Exception as e:
            logger.error(f"Error generating response: {str(e)}")
            return f"I encountered an error processing your query: {str(e)}"
