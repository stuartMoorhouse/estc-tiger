import os
import json
from typing import Dict, Any, List, Optional
import logging

from elasticsearch import Elasticsearch
from elasticsearch.exceptions import ApiError, TransportError

logger = logging.getLogger(__name__)

class ElasticsearchService:
    """
    Client for Elasticsearch integration.
    Handles real queries to Elasticsearch and retrieves ESTC data.
    """
    
    def __init__(self):
        self.es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
        self.es_username = os.getenv('ELASTICSEARCH_USERNAME', 'elastic')
        self.es_password = os.getenv('ELASTICSEARCH_PASSWORD', '')
        self.es_api_key = os.getenv('ELASTICSEARCH_API_KEY', '')
        
        # Initialize Elasticsearch client
        self.client = None
        self._init_client()
        
        # ESTC data index mapping
        self.index_mapping = {
            'financial': ['estc-financial-data', 'estc-earnings', 'estc-revenue'],
            'stock': ['estc-stock-data', 'estc-prices', 'estc-analyst-ratings'],
            'competitive': ['estc-competitive-analysis', 'estc-market-comparison'],
            'rsu': ['estc-rsu-data', 'estc-equity-compensation'],
            'general': ['estc-general-data', 'estc-company-info', 'estc-news']
        }
    
    
    
    def _init_client(self):
        """Initialize Elasticsearch client with authentication"""
        try:
            if self.es_api_key:
                # Use API key authentication
                self.client = Elasticsearch(
                    [self.es_url],
                    api_key=self.es_api_key,
                    verify_certs=False,
                    ssl_show_warn=False
                )
            elif self.es_username and self.es_password:
                # Use basic authentication
                self.client = Elasticsearch(
                    [self.es_url],
                    basic_auth=(self.es_username, self.es_password),
                    verify_certs=False,
                    ssl_show_warn=False
                )
            else:
                # No authentication
                self.client = Elasticsearch(
                    [self.es_url],
                    verify_certs=False,
                    ssl_show_warn=False
                )
                
            # Test connection
            if self.client.ping():
                logger.info(f"Connected to Elasticsearch at {self.es_url}")
            else:
                logger.error(f"Failed to connect to Elasticsearch at {self.es_url}")
                self.client = None
                
        except Exception as e:
            logger.error(f"Error initializing Elasticsearch client: {e}")
            self.client = None
    
    def is_connected(self) -> bool:
        """Check if Elasticsearch client is connected"""
        if self.client:
            try:
                return self.client.ping()
            except:
                pass
        return False
    
    def get_cluster_info(self) -> Dict[str, Any]:
        """Get basic cluster information"""
        if not self.is_connected():
            return {"error": "Not connected to Elasticsearch"}
        
        try:
            cluster_info = self.client.info()
            return {
                "cluster_name": cluster_info.get("cluster_name", "unknown"),
                "version": cluster_info.get("version", {}).get("number", "unknown"),
                "status": "connected"
            }
        except Exception as e:
            return {"error": str(e)}
    
    def search_estc_data(self, query_type: str, search_terms: List[str], 
                        limit: int = 10) -> Dict[str, Any]:
        """
        Search ESTC data based on query type and search terms
        
        Args:
            query_type: Type of data to search (financial, stock, competitive, rsu, general)
            search_terms: List of terms to search for
            limit: Maximum number of results to return
            
        Returns:
            Dictionary containing search results and metadata
        """
        if not self.client:
            return {
                "error": "Elasticsearch client not available",
                "results": [],
                "total": 0
            }
        
        try:
            if not self.client.ping():
                return {
                    "error": "Elasticsearch cluster not reachable",
                    "results": [],
                    "total": 0
                }
        except Exception as e:
            return {
                "error": f"Elasticsearch connection error: {str(e)}",
                "results": [],
                "total": 0
            }
        
        # Get indices for the query type
        indices = self.index_mapping.get(query_type, self.index_mapping['general'])
        
        # Build search query
        search_query = {
            "query": {
                "bool": {
                    "should": [
                        {
                            "multi_match": {
                                "query": " ".join(search_terms),
                                "fields": ["title^2", "content", "description", "summary"],
                                "type": "best_fields",
                                "fuzziness": "AUTO"
                            }
                        },
                        {
                            "terms": {
                                "keywords": search_terms
                            }
                        }
                    ],
                    "minimum_should_match": 1
                }
            },
            "sort": [
                {"_score": {"order": "desc"}},
                {"date": {"order": "desc", "missing": "_last"}}
            ],
            "size": limit,
            "_source": {
                "excludes": ["raw_data", "full_text"]  # Exclude large fields
            }
        }
        
        results = []
        total_hits = 0
        
        # Search across all relevant indices
        for index in indices:
            try:
                response = self.client.search(
                    index=index,
                    body=search_query,
                    ignore_unavailable=True
                )
                
                hits = response.get("hits", {})
                total_hits += hits.get("total", {}).get("value", 0)
                
                for hit in hits.get("hits", []):
                    results.append({
                        "index": index,
                        "document_id": hit["_id"],
                        "score": hit["_score"],
                        "source": hit["_source"],
                        "type": hit["_source"].get("type", "unknown")
                    })
                    
            except Exception as e:
                logger.warning(f"Error searching index {index}: {e}")
                continue
        
        # Sort results by score and limit
        results.sort(key=lambda x: x["score"], reverse=True)
        results = results[:limit]
        
        return {
            "results": results,
            "total": total_hits,
            "query_type": query_type,
            "search_terms": search_terms,
            "indices_searched": indices
        }
    
    def get_document_by_id(self, index: str, doc_id: str) -> Dict[str, Any]:
        """Get a specific document by ID"""
        if not self.is_connected():
            return {"error": "Not connected to Elasticsearch"}
        
        try:
            response = self.client.get(
                index=index,
                id=doc_id,
                ignore=404
            )
            
            if response.get("found", False):
                return {
                    "document_id": doc_id,
                    "index": index,
                    "source": response["_source"]
                }
            else:
                return {"error": "Document not found"}
                
        except Exception as e:
            return {"error": str(e)}
    
    def get_available_indices(self) -> List[str]:
        """Get list of available ESTC indices"""
        if not self.is_connected():
            return []
        
        try:
            # Get all indices that start with 'estc-'
            response = self.client.indices.get_alias(index="estc-*", ignore_unavailable=True)
            return list(response.keys())
        except Exception as e:
            logger.error(f"Error getting indices: {e}")
            return []
    
    def analyze_query_intent(self, user_query: str) -> Dict[str, Any]:
        """
        Analyze user query to determine what type of data to search for
        
        Args:
            user_query: The user's natural language query
            
        Returns:
            Dictionary with query analysis results
        """
        query_lower = user_query.lower()
        
        # Keywords for different data types
        financial_keywords = ['revenue', 'earnings', 'profit', 'margin', 'growth', 'financial', 'income', 'sales']
        stock_keywords = ['stock', 'price', 'analyst', 'rating', 'target', 'valuation', 'market cap']
        competitive_keywords = ['datadog', 'splunk', 'competitor', 'competitive', 'market share', 'comparison']
        rsu_keywords = ['rsu', 'equity', 'compensation', 'vesting', 'stock options', 'shares']
        
        # Score each category
        scores = {
            'financial': sum(1 for keyword in financial_keywords if keyword in query_lower),
            'stock': sum(1 for keyword in stock_keywords if keyword in query_lower),
            'competitive': sum(1 for keyword in competitive_keywords if keyword in query_lower),
            'rsu': sum(1 for keyword in rsu_keywords if keyword in query_lower)
        }
        
        # Determine primary query type
        primary_type = max(scores, key=scores.get) if max(scores.values()) > 0 else 'general'
        
        # Extract search terms
        search_terms = []
        for word in query_lower.split():
            if len(word) > 3 and word not in ['what', 'how', 'when', 'where', 'why', 'the', 'and', 'or', 'but']:
                search_terms.append(word)
        
        # Add 'estc' and 'elastic' as default terms
        search_terms.extend(['estc', 'elastic'])
        
        return {
            'primary_type': primary_type,
            'scores': scores,
            'search_terms': list(set(search_terms))  # Remove duplicates
        }

# Global instance
elasticsearch_service = ElasticsearchService()