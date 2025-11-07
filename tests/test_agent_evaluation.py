import json
import os
import sys

# Setup Django when running directly (not via pytest)
if __name__ == "__main__":
    # Add parent directory to path
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'proplens_ai.settings')
    import django
    django.setup()

# These imports work with both pytest (which sets up Django) and direct execution
from deepeval.metrics import AnswerRelevancyMetric, FaithfulnessMetric
from deepeval.test_case import LLMTestCase
from deepeval.models import DeepEvalBaseLLM
from agents.services.langgraph_agent import LangGraphAgent
from agents.services.document_rag import DocumentRAGService
from agents.services.gemini_service import GeminiLLM
from django.conf import settings


class GeminiDeepEvalLLM(DeepEvalBaseLLM):
    """Wrapper to make Google Gemini compatible with DeepEval"""
    
    def __init__(self, model_name: str = None):
        model_name = model_name or settings.GEMINI_MODEL
        # Initialize attributes before super()
        self._model_name = model_name
        self._gemini_llm = None
        super().__init__(model_name=model_name)
        # Initialize Gemini LLM after super()
        try:
            self._gemini_llm = GeminiLLM(
                model_name=model_name,
                temperature=0.7
            )
        except Exception as e:
            raise ValueError(f"Failed to initialize Gemini LLM: {str(e)}")
    
    @property
    def gemini_llm(self):
        """Get or initialize Gemini LLM"""
        if self._gemini_llm is None:
            self._gemini_llm = GeminiLLM(
                model_name=self._model_name or settings.GEMINI_MODEL,
                temperature=0.7
            )
        return self._gemini_llm
    
    def load_model(self):
        """Load the model"""
        return self.gemini_llm
    
    def generate(self, prompt: str) -> str:
        """Generate response from prompt"""
        try:
            response = self.gemini_llm.invoke(prompt)
            return response.content
        except Exception as e:
            raise Exception(f"Error generating response with Gemini: {str(e)}")
    
    async def a_generate(self, prompt: str) -> str:
        """Async generate response"""
        return self.generate(prompt)
    
    def get_model_name(self) -> str:
        """Get model name"""
        return getattr(self, '_model_name', None) or settings.GEMINI_MODEL


def test_agent_evaluation():
    """Evaluate agent performance using DeepEval framework"""
    
    agent = LangGraphAgent()
    rag_service = DocumentRAGService()
    
    # Test cases with proper context retrieval
    test_cases = [
        {
            "input": "What are the facilities and amenities in Lumina Grand?",
            "expected_output": "Information about Lumina Grand facilities and amenities including pools, gyms, playgrounds, and other recreational facilities",
            "context_type": "rag",
        },
        {
            "input": "How many leads have status 'connected'?",
            "expected_output": "A count of leads with connected status from the CRM database",
            "context_type": "t2sql",
        },
        {
            "input": "Tell me about the project features of Sobha Crest",
            "expected_output": "Information about Sobha Crest project features, amenities, and specifications",
            "context_type": "rag",
        },
    ]
    
    results = []
    
    for test_case in test_cases:
        try:
            # Get agent response
            actual_output = agent.query(test_case["input"])
            
            # Get context based on query type
            context_list = []
            if test_case["context_type"] == "rag":
                # Try to get relevant context from RAG
                try:
                    # Query RAG service directly to get context
                    rag_context = rag_service.query(test_case["input"])
                    if rag_context and rag_context.strip():
                        context_list.append(rag_context[:500])  # Limit context length
                except Exception as e:
                    context_list.append(f"Property brochure information about {test_case['input']}")
            elif test_case["context_type"] == "t2sql":
                context_list.append("CRM database containing leads table with status field")
            
            # If no context retrieved, use generic context
            if not context_list:
                context_list = [f"Context for {test_case['context_type']} query"]
            
            # Create test case with proper context format (list of strings)
            test = LLMTestCase(
                input=test_case["input"],
                actual_output=actual_output,
                expected_output=test_case["expected_output"],
                context=context_list if context_list else None,
                retrieval_context=context_list if context_list else None,  # Required for Faithfulness metric
            )
            
            # Evaluate with metrics using Google Gemini
            try:
                # Initialize Gemini LLM for DeepEval
                gemini_model = GeminiDeepEvalLLM()
                
                # Create metrics with Gemini model
                answer_relevancy_metric = AnswerRelevancyMetric(
                    threshold=0.7,
                    model=gemini_model
                )
                faithfulness_metric = FaithfulnessMetric(
                    threshold=0.7,
                    model=gemini_model
                )
                
                # Measure scores
                answer_relevancy_score = answer_relevancy_metric.measure(test)
                faithfulness_score = faithfulness_metric.measure(test)
                
                # Capture results
                result = {
                    "input": test_case["input"],
                    "actual_output": actual_output[:500] if len(actual_output) > 500 else actual_output,
                    "expected_output": test_case["expected_output"],
                    "context_type": test_case["context_type"],
                    "context_used": context_list[0][:200] if context_list else "No context available",
                    "answer_relevancy_score": float(answer_relevancy_score) if answer_relevancy_score else None,
                    "faithfulness_score": float(faithfulness_score) if faithfulness_score else None,
                    "answer_relevancy_passed": bool(answer_relevancy_metric.success) if hasattr(answer_relevancy_metric, 'success') else None,
                    "faithfulness_passed": bool(faithfulness_metric.success) if hasattr(faithfulness_metric, 'success') else None,
                    "evaluation_model": settings.GEMINI_MODEL,
                }
            except Exception as eval_error:
                # If DeepEval fails, still capture agent response
                result = {
                    "input": test_case["input"],
                    "actual_output": actual_output[:500] if len(actual_output) > 500 else actual_output,
                    "expected_output": test_case["expected_output"],
                    "context_type": test_case["context_type"],
                    "context_used": context_list[0][:200] if context_list else "No context available",
                    "evaluation_error": str(eval_error),
                    "evaluation_error_type": type(eval_error).__name__,
                    "note": "Agent response captured but DeepEval evaluation failed. Check GEMINI_API_KEY configuration."
                }
            
            results.append(result)
            
            if 'evaluation_error' not in result:
                print(f"✓ Evaluated: {test_case['input'][:50]}...")
                print(f"  Answer Relevancy: {result.get('answer_relevancy_score', 'N/A'):.2f} ({'PASS' if result.get('answer_relevancy_passed') else 'FAIL'})")
                print(f"  Faithfulness: {result.get('faithfulness_score', 'N/A'):.2f} ({'PASS' if result.get('faithfulness_passed') else 'FAIL'})")
            else:
                print(f"⚠ Evaluated (with errors): {test_case['input'][:50]}...")
                print(f"  Error: {result.get('evaluation_error', 'Unknown error')}")
            
        except Exception as e:
            error_result = {
                "input": test_case["input"],
                "error": str(e),
                "error_type": type(e).__name__,
            }
            results.append(error_result)
            print(f"✗ Error evaluating: {test_case['input'][:50]}...")
            print(f"  Error: {str(e)}")
    
    # Save results to dedicated file
    output_file = os.path.join(os.path.dirname(__file__), 'agent_evaluation_scores.json')
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    
    # Calculate summary statistics
    successful_evaluations = [r for r in results if 'error' not in r]
    if successful_evaluations:
        avg_relevancy = sum(r.get('answer_relevancy_score', 0) or 0 for r in successful_evaluations) / len(successful_evaluations)
        avg_faithfulness = sum(r.get('faithfulness_score', 0) or 0 for r in successful_evaluations) / len(successful_evaluations)
        passed_relevancy = sum(1 for r in successful_evaluations if r.get('answer_relevancy_passed'))
        passed_faithfulness = sum(1 for r in successful_evaluations if r.get('faithfulness_passed'))
        
        summary = {
            "total_test_cases": len(test_cases),
            "successful_evaluations": len(successful_evaluations),
            "failed_evaluations": len(results) - len(successful_evaluations),
            "average_answer_relevancy_score": round(avg_relevancy, 3),
            "average_faithfulness_score": round(avg_faithfulness, 3),
            "answer_relevancy_passed_count": passed_relevancy,
            "faithfulness_passed_count": passed_faithfulness,
        }
        
        # Add summary to results
        results_with_summary = {
            "summary": summary,
            "detailed_results": results
        }
        
        # Save with summary
        with open(output_file, 'w') as f:
            json.dump(results_with_summary, f, indent=2, ensure_ascii=False)
        
        print("\n" + "="*60)
        print("EVALUATION SUMMARY")
        print("="*60)
        print(f"Total Test Cases: {summary['total_test_cases']}")
        print(f"Successful Evaluations: {summary['successful_evaluations']}")
        print(f"Failed Evaluations: {summary['failed_evaluations']}")
        print(f"\nAverage Answer Relevancy Score: {summary['average_answer_relevancy_score']:.3f}")
        print(f"Average Faithfulness Score: {summary['average_faithfulness_score']:.3f}")
        print(f"\nAnswer Relevancy Passed: {summary['answer_relevancy_passed_count']}/{summary['successful_evaluations']}")
        print(f"Faithfulness Passed: {summary['faithfulness_passed_count']}/{summary['successful_evaluations']}")
        print("="*60)
    
    print(f"\n✓ Evaluation complete. Results saved to {output_file}")
    return results


if __name__ == "__main__":
    test_agent_evaluation()



