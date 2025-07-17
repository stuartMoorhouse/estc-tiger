import json
import re
from typing import Dict, Any

class OutputEvaluator:
    """
    Output Evaluator component of the Evaluator-Optimizer pattern.
    Validates generated responses for security and sensitive data leakage only.
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
        
    
    async def evaluate(self, response: str, original_query: str) -> Dict[str, Any]:
        """
        Evaluate the generated response for security and sensitive data only.
        
        Args:
            response: Generated response from Claude
            original_query: Original user query for context
            
        Returns:
            Dict containing approval status and feedback
        """
        
        # Check for sensitive data exposure (security only)
        sensitive_check = self._check_sensitive_data(response)
        if not sensitive_check["safe"]:
            return {
                "approved": False,
                "feedback": f"Response contains sensitive data: {sensitive_check['reason']}",
                "category": "security"
            }
        
        # If security checks pass, approve the response
        return {
            "approved": True,
            "feedback": "Response passed security validation",
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
    
    def get_evaluation_metrics(self) -> Dict[str, Any]:
        """Get current evaluation metrics for monitoring"""
        return {
            "security_checks": len(self.sensitive_patterns),
            "last_evaluation": "active",
            "categories": ["security"]
        }