import json
import time
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import os

class ECSLogger:
    """
    Logger that writes events in Elastic Common Schema (ECS) format.
    Tracks function calls, API interactions, and security events.
    """
    
    def __init__(self, log_file: str = "estc-tiger.json"):
        self.log_file = log_file
        self.session_id = str(uuid.uuid4())
        
    def _create_base_event(self, event_type: str, message: str) -> Dict[str, Any]:
        """Create base ECS event structure"""
        return {
            "@timestamp": datetime.utcnow().isoformat() + "Z",
            "ecs": {
                "version": "8.0.0"
            },
            "event": {
                "type": [event_type],
                "category": ["application"],
                "action": event_type,
                "outcome": "unknown",
                "duration": 0
            },
            "service": {
                "name": "estc-tiger",
                "type": "chatbot",
                "version": "1.0.0"
            },
            "process": {
                "pid": os.getpid()
            },
            "host": {
                "hostname": os.uname().nodename,
                "os": {
                    "type": os.uname().sysname
                }
            },
            "session": {
                "id": self.session_id
            },
            "message": message,
            "labels": {
                "application": "estc-tiger",
                "environment": "development"
            }
        }
    
    def log_user_query(self, query: str, user_id: str = "anonymous") -> str:
        """Log initial user query"""
        query_id = str(uuid.uuid4())
        
        event = self._create_base_event("user_query", f"User query received: {query[:100]}...")
        event["event"]["outcome"] = "success"
        event["user"] = {
            "id": user_id,
            "name": user_id
        }
        event["estc_tiger"] = {
            "query_id": query_id,
            "query": query,
            "query_length": len(query),
            "stage": "input"
        }
        
        self._write_event(event)
        return query_id
    
    def log_security_evaluation(self, query_id: str, query: str, result: Dict[str, Any], 
                              duration_ms: int, patterns_matched: Optional[List[str]] = None):
        """Log security evaluation results"""
        event = self._create_base_event("security_evaluation", 
                                       f"Security evaluation: {'BLOCKED' if not result.get('safe', True) else 'ALLOWED'}")
        
        event["event"]["outcome"] = "failure" if not result.get("safe", True) else "success"
        event["event"]["duration"] = duration_ms * 1000000  # Convert to nanoseconds
        
        event["estc_tiger"] = {
            "query_id": query_id,
            "stage": "security_evaluation",
            "function_called": "SecurityEvaluator.evaluate",
            "result": result,
            "patterns_matched": patterns_matched or [],
            "blocked": not result.get("safe", True)
        }
        
        if not result.get("safe", True):
            event["security"] = {
                "threat": {
                    "type": "jailbreak_attempt",
                    "description": result.get("reason", "Unknown security threat")
                }
            }
        
        self._write_event(event)
    
    def log_elasticsearch_generation(self, query_id: str, query: str, response: str, 
                                   duration_ms: int, api_calls: Optional[List[Dict[str, Any]]] = None):
        """Log Elasticsearch generation with API call details"""
        event = self._create_base_event("elasticsearch_generation", 
                                       f"Generated response using Claude + Elasticsearch")
        
        event["event"]["outcome"] = "success"
        event["event"]["duration"] = duration_ms * 1000000  # Convert to nanoseconds
        
        event["estc_tiger"] = {
            "query_id": query_id,
            "stage": "generation",
            "function_called": "ElasticsearchGenerator.generate",
            "response_length": len(response),
            "api_calls": api_calls or []
        }
        
        # Add Elasticsearch-specific data if API calls were made
        if api_calls:
            event["elasticsearch"] = {
                "calls": []
            }
            
            for call in api_calls:
                es_call = {
                    "index": call.get("index", "unknown"),
                    "operation": call.get("operation", "search"),
                    "document_count": call.get("document_count", 0),
                    "documents": call.get("documents", [])
                }
                event["elasticsearch"]["calls"].append(es_call)
        
        self._write_event(event)
    
    def log_output_evaluation(self, query_id: str, response: str, result: Dict[str, Any], 
                            duration_ms: int):
        """Log output evaluation results"""
        event = self._create_base_event("output_evaluation", 
                                       f"Output evaluation: {'BLOCKED' if not result.get('approved', True) else 'APPROVED'}")
        
        event["event"]["outcome"] = "failure" if not result.get("approved", True) else "success"
        event["event"]["duration"] = duration_ms * 1000000  # Convert to nanoseconds
        
        event["estc_tiger"] = {
            "query_id": query_id,
            "stage": "output_evaluation", 
            "function_called": "OutputEvaluator.evaluate",
            "result": result,
            "response_length": len(response),
            "approved": result.get("approved", True)
        }
        
        if not result.get("approved", True):
            event["security"] = {
                "threat": {
                    "type": "sensitive_data_exposure",
                    "description": result.get("feedback", "Output contains sensitive data")
                }
            }
        
        self._write_event(event)
    
    def log_final_response(self, query_id: str, response: str, blocked: bool, 
                         total_duration_ms: int):
        """Log final response to user"""
        event = self._create_base_event("final_response", 
                                       f"Final response: {'BLOCKED' if blocked else 'DELIVERED'}")
        
        event["event"]["outcome"] = "failure" if blocked else "success"
        event["event"]["duration"] = total_duration_ms * 1000000  # Convert to nanoseconds
        
        event["estc_tiger"] = {
            "query_id": query_id,
            "stage": "final_response",
            "response_length": len(response),
            "blocked": blocked,
            "total_duration_ms": total_duration_ms
        }
        
        self._write_event(event)
    
    def log_error(self, query_id: str, error: str, stage: str, duration_ms: int = 0):
        """Log errors that occur during processing"""
        event = self._create_base_event("error", f"Error in {stage}: {error}")
        
        event["event"]["outcome"] = "failure"
        event["event"]["duration"] = duration_ms * 1000000  # Convert to nanoseconds
        
        event["error"] = {
            "message": error,
            "type": "processing_error"
        }
        
        event["estc_tiger"] = {
            "query_id": query_id,
            "stage": stage,
            "error": error
        }
        
        self._write_event(event)
    
    def _write_event(self, event: Dict[str, Any]):
        """Write event to log file in JSON format"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(event, ensure_ascii=False) + '\n')
        except Exception as e:
            print(f"Failed to write to log file: {e}")

# Global logger instance
logger = ECSLogger()