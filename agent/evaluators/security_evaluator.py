import json
import re
from typing import Dict, Any

class SecurityEvaluator:
    """
    Security Evaluator component of the Evaluator-Optimizer pattern.
    Validates user queries for jailbreak attempts and malicious behavior.
    """
    
    def __init__(self):
        self.jailbreak_patterns = [
            r"ignore.*previous.*instructions",
            r"forget.*you.*are",
            r"pretend.*you.*are",
            r"act.*as.*if",
            r"bypass.*safety",
            r"override.*guidelines",
            r"disregard.*rules",
            r"sql.*injection",
            r"drop.*table",
            r"delete.*from",
            r"truncate.*table",
            r"'; --",
            r"1=1.*--",
            r"union.*select",
            r"script.*alert",
            r"<script>",
            r"javascript:",
            r"eval\(",
            r"exec\(",
        ]
        
        self.suspicious_elasticsearch_patterns = [
            r"_cluster.*settings",
            r"_nodes.*shutdown",
            r"_cluster.*health.*force",
            r"delete.*index",
            r"/_template/",
            r"/_ingest/",
            r"/_security/",
            r"password.*admin",
            r"authentication.*bypass",
        ]
    
    async def evaluate(self, user_query: str) -> Dict[str, Any]:
        """
        Evaluate user query for security threats.
        
        Args:
            user_query: The user's input query
            
        Returns:
            Dict containing safety assessment and reason
        """
        
        # Convert to lowercase for pattern matching
        query_lower = user_query.lower()
        
        # Check for jailbreak patterns
        for pattern in self.jailbreak_patterns:
            if re.search(pattern, query_lower):
                return {
                    "safe": False,
                    "reason": "Query contains potential jailbreak attempt or malicious pattern",
                    "pattern_matched": pattern
                }
        
        # Check for suspicious Elasticsearch operations
        for pattern in self.suspicious_elasticsearch_patterns:
            if re.search(pattern, query_lower):
                return {
                    "safe": False,
                    "reason": "Query contains potentially dangerous Elasticsearch operations",
                    "pattern_matched": pattern
                }
        
        # Check for excessively long queries (potential DoS)
        if len(user_query) > 1000:
            return {
                "safe": False,
                "reason": "Query is excessively long and may be malicious"
            }
        
        # Check for multiple special characters (potential injection)
        special_char_count = sum(1 for char in user_query if char in "';\"(){}[]<>")
        if special_char_count > 10:
            return {
                "safe": False,
                "reason": "Query contains suspicious number of special characters"
            }
        
        # Additional semantic analysis could be added here
        # For now, if it passes basic checks, consider it safe
        return {
            "safe": True,
            "reason": "Query passed security validation"
        }
    
    def get_safe_query_examples(self) -> list:
        """Return examples of safe queries for user guidance"""
        return [
            "Show me all indices in my Elasticsearch cluster",
            "What are the field mappings for the products index?",
            "Search for orders with status 'completed'",
            "Find documents containing 'error' in the last 24 hours",
            "Show me the health status of my cluster",
            "List all indices starting with 'logs-'",
            "What's the document count for each index?",
        ]