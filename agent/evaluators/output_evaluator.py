import json
import re
from typing import Dict, Any

class OutputEvaluator:
    """
    Output Evaluator component of the Evaluator-Optimizer pattern.
    Validates generated responses for quality, safety, and data leakage.
    """
    
    def __init__(self):
        self.sensitive_patterns = [
            r"password\s*[:=]\s*['\"]?[^'\"\s]+",
            r"api[_-]?key\s*[:=]\s*['\"]?[^'\"\s]+",
            r"secret\s*[:=]\s*['\"]?[^'\"\s]+",
            r"token\s*[:=]\s*['\"]?[^'\"\s]+",
            r"private[_-]?key",
            r"ssh[_-]?key",
            r"credit[_-]?card",
            r"ssn\s*[:=]\s*\d{3}-\d{2}-\d{4}",
            r"email\s*[:=]\s*[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}",
            r"phone\s*[:=]\s*\+?1?[-.\s]?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}",
        ]
        
        self.quality_indicators = [
            "step",
            "example",
            "here's",
            "would",
            "can help",
            "let me",
            "i'll",
            "to do this",
            "approach",
            "method",
        ]
    
    async def evaluate(self, response: str, original_query: str) -> Dict[str, Any]:
        """
        Evaluate the generated response for quality and safety.
        
        Args:
            response: Generated response from Claude
            original_query: Original user query for context
            
        Returns:
            Dict containing approval status and feedback
        """
        
        # Check for sensitive data exposure
        sensitive_check = self._check_sensitive_data(response)
        if not sensitive_check["safe"]:
            return {
                "approved": False,
                "feedback": f"Response contains sensitive data: {sensitive_check['reason']}",
                "category": "security"
            }
        
        # Check response quality
        quality_check = self._check_response_quality(response, original_query)
        if not quality_check["sufficient"]:
            return {
                "approved": False,
                "feedback": quality_check["feedback"],
                "category": "quality"
            }
        
        # Check for completeness
        completeness_check = self._check_completeness(response, original_query)
        if not completeness_check["complete"]:
            return {
                "approved": False,
                "feedback": completeness_check["feedback"],
                "category": "completeness"
            }
        
        # Check for Elasticsearch-specific accuracy
        elasticsearch_check = self._check_elasticsearch_accuracy(response)
        if not elasticsearch_check["accurate"]:
            return {
                "approved": False,
                "feedback": elasticsearch_check["feedback"],
                "category": "accuracy"
            }
        
        # If all checks pass
        return {
            "approved": True,
            "feedback": "Response meets all quality and safety standards",
            "category": "approved"
        }
    
    def _check_sensitive_data(self, response: str) -> Dict[str, Any]:
        """Check for sensitive data exposure in response"""
        response_lower = response.lower()
        
        for pattern in self.sensitive_patterns:
            if re.search(pattern, response_lower):
                return {
                    "safe": False,
                    "reason": f"Potential sensitive data pattern detected: {pattern}",
                    "pattern": pattern
                }
        
        # Check for suspicious IP addresses or internal URLs
        ip_pattern = r'\b\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}\b'
        if re.search(ip_pattern, response):
            return {
                "safe": False,
                "reason": "Response contains IP addresses that may be sensitive"
            }
        
        return {"safe": True}
    
    def _check_response_quality(self, response: str, query: str) -> Dict[str, Any]:
        """Check if response quality meets standards"""
        
        # Check minimum length
        if len(response.strip()) < 20:
            return {
                "sufficient": False,
                "feedback": "Response is too short and not informative enough"
            }
        
        # Check for helpfulness indicators
        helpful_score = sum(1 for indicator in self.quality_indicators 
                          if indicator in response.lower())
        
        if helpful_score < 2:
            return {
                "sufficient": False,
                "feedback": "Response lacks helpful explanations or guidance"
            }
        
        # Check for generic responses
        generic_phrases = ["i can help", "let me know", "anything else"]
        generic_score = sum(1 for phrase in generic_phrases 
                           if phrase in response.lower())
        
        if generic_score > 2:
            return {
                "sufficient": False,
                "feedback": "Response is too generic and not specific enough"
            }
        
        return {"sufficient": True}
    
    def _check_completeness(self, response: str, query: str) -> Dict[str, Any]:
        """Check if response addresses the user's query completely"""
        
        query_lower = query.lower()
        response_lower = response.lower()
        
        # Check for query-specific completeness
        if "list" in query_lower and "indices" in query_lower:
            if "list_indices" not in response_lower and "indices" not in response_lower:
                return {
                    "complete": False,
                    "feedback": "Response doesn't address the request to list indices"
                }
        
        if "mapping" in query_lower:
            if "mapping" not in response_lower and "field" not in response_lower:
                return {
                    "complete": False,
                    "feedback": "Response doesn't address the mapping request"
                }
        
        if "search" in query_lower:
            if "search" not in response_lower and "query" not in response_lower:
                return {
                    "complete": False,
                    "feedback": "Response doesn't address the search request"
                }
        
        # Check for question marks in query but no answers
        if "?" in query and "?" not in response and len(response) < 100:
            return {
                "complete": False,
                "feedback": "Query contains questions but response doesn't provide clear answers"
            }
        
        return {"complete": True}
    
    def _check_elasticsearch_accuracy(self, response: str) -> Dict[str, Any]:
        """Check for Elasticsearch-specific accuracy"""
        
        response_lower = response.lower()
        
        # Check for common Elasticsearch misconceptions
        misconceptions = [
            ("elasticsearch is sql", "elasticsearch uses query dsl"),
            ("elasticsearch is nosql", "elasticsearch is a search engine"),
            ("indices are tables", "indices are collections of documents"),
        ]
        
        for misconception, correction in misconceptions:
            if misconception in response_lower:
                return {
                    "accurate": False,
                    "feedback": f"Response contains misconception: {misconception}. {correction}"
                }
        
        # Check for proper Elasticsearch terminology
        if "elasticsearch" in response_lower:
            proper_terms = ["index", "document", "field", "mapping", "cluster", "node", "shard"]
            term_count = sum(1 for term in proper_terms if term in response_lower)
            
            if term_count < 1:
                return {
                    "accurate": False,
                    "feedback": "Response lacks proper Elasticsearch terminology"
                }
        
        return {"accurate": True}
    
    def get_evaluation_metrics(self) -> Dict[str, Any]:
        """Get current evaluation metrics for monitoring"""
        return {
            "security_checks": len(self.sensitive_patterns),
            "quality_indicators": len(self.quality_indicators),
            "last_evaluation": "active",
            "categories": ["security", "quality", "completeness", "accuracy"]
        }