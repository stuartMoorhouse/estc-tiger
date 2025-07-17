import os
import json
from typing import Dict, Any, List, Optional
import logging

# Try to import elasticsearch, but provide fallback if not available
try:
    from elasticsearch import Elasticsearch
    from elasticsearch.exceptions import ElasticsearchException
    ELASTICSEARCH_AVAILABLE = True
except ImportError:
    ELASTICSEARCH_AVAILABLE = False
    print("Elasticsearch library not available. Using fallback mode.")

logger = logging.getLogger(__name__)

class ElasticsearchMCPClient:
    """
    MCP client for Elasticsearch integration.
    Handles real queries to Elasticsearch and retrieves ESTC data.
    """
    
    def __init__(self):
        self.es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
        self.es_username = os.getenv('ELASTICSEARCH_USERNAME', 'elastic')
        self.es_password = os.getenv('ELASTICSEARCH_PASSWORD', '')
        self.es_api_key = os.getenv('ELASTICSEARCH_API_KEY', '')
        
        # Initialize Elasticsearch client
        self.client = None
        if ELASTICSEARCH_AVAILABLE:
            self._init_client()
        
        # Load fallback data from JSON file
        self.fallback_data = self._load_fallback_data()
        
        # ESTC data index mapping
        self.index_mapping = {
            'financial': ['estc-financial-data', 'estc-earnings', 'estc-revenue'],
            'stock': ['estc-stock-data', 'estc-prices', 'estc-analyst-ratings'],
            'competitive': ['estc-competitive-analysis', 'estc-market-comparison'],
            'rsu': ['estc-rsu-data', 'estc-equity-compensation'],
            'general': ['estc-general-data', 'estc-company-info', 'estc-news']
        }
    
    def _load_fallback_data(self) -> List[Dict[str, Any]]:
        """Load ESTC data from JSON file as fallback"""
        try:
            # Try to load from the bulk JSON file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            json_path = os.path.join(current_dir, '..', 'estc_es9_bulk.json')
            
            if os.path.exists(json_path):
                with open(json_path, 'r') as f:
                    lines = f.readlines()
                    
                # Parse NDJSON format (each line is a separate JSON object)
                documents = []
                for i in range(0, len(lines), 2):  # Skip index lines, take document lines
                    if i + 1 < len(lines):
                        try:
                            doc = json.loads(lines[i + 1].strip())
                            # Add metadata from index line
                            index_line = json.loads(lines[i].strip())
                            doc['_index'] = index_line.get('index', {}).get('_index', 'unknown')
                            doc['_id'] = index_line.get('index', {}).get('_id', f'doc_{i}')
                            documents.append(doc)
                        except json.JSONDecodeError:
                            continue
                
                logger.info(f"Loaded {len(documents)} documents from fallback data")
                return documents
            else:
                logger.warning(f"Fallback data file not found at {json_path}")
                return []
                
        except Exception as e:
            logger.error(f"Error loading fallback data: {e}")
            return []
    
    def _search_fallback_data(self, query_type: str, search_terms: List[str], 
                            limit: int = 10) -> Dict[str, Any]:
        """Search fallback data when Elasticsearch is not available"""
        if not self.fallback_data:
            return {
                "error": "No fallback data available",
                "results": [],
                "total": 0
            }
        
        results = []
        
        # Simple text search in fallback data
        for doc in self.fallback_data:
            score = 0
            
            # Search in various fields
            searchable_text = ""
            # Include all text fields from the document
            for field, value in doc.items():
                if isinstance(value, str) and field not in ['_index', '_id']:
                    searchable_text += str(value).lower() + " "
                elif field in ['document_type', 'notes', 'status']:
                    searchable_text += str(value).lower() + " "
            
            # Calculate relevance score with document type diversity
            base_score = 0
            for term in search_terms:
                if term.lower() in searchable_text:
                    base_score += 1
            
            # Add diversity bonus based on document type
            doc_type_bonus = {
                'estc-financial-data': 1.0,      # Financial data is always relevant
                'estc-stock-data': 1.0,          # Stock data is always relevant
                'estc-competitive-data': 0.8,    # Competitive data is important
                'estc-product-milestones': 0.6,  # Product milestones are relevant but not overwhelming
                'estc-partnership-data': 0.7,    # Partnership data is valuable
                'estc-acquisition-history': 0.5, # Acquisition history is supplementary
                'estc-analyst-ratings': 1.0,     # Analyst ratings are highly relevant
                'estc-rsu-data': 0.9,           # RSU data is important for RSU holders
                'estc-news': 0.6,               # News is supplementary
                'estc-earnings': 1.0,           # Earnings data is always relevant
                'estc-revenue': 1.0,            # Revenue data is always relevant
                'estc-prices': 1.0,             # Price data is always relevant
                'estc-general-data': 0.8,       # General data is broadly relevant
                'estc-company-info': 0.7        # Company info is supportive
            }
            
            index_name = doc.get('_index', 'unknown')
            diversity_bonus = doc_type_bonus.get(index_name, 0.5)
            
            # Apply base score with diversity bonus
            score = base_score * diversity_bonus
            
            # Add query type bonus if relevant
            if query_type != 'general':
                type_keywords = {
                    'financial': ['revenue', 'earnings', 'financial', 'growth', 'profit', 'margin'],
                    'stock': ['stock', 'price', 'analyst', 'rating', 'target', 'valuation'],
                    'competitive': ['datadog', 'splunk', 'competitor', 'competitive', 'market share'],
                    'rsu': ['rsu', 'equity', 'compensation', 'vesting', 'shares']
                }
                
                type_terms = type_keywords.get(query_type, [])
                type_bonus = 0
                for term in type_terms:
                    if term in searchable_text:
                        type_bonus += 0.3
                
                score += type_bonus
            
            if score > 0:
                results.append({
                    "index": doc.get('_index', 'fallback'),
                    "document_id": doc.get('_id', 'unknown'),
                    "score": score,
                    "source": doc,
                    "type": doc.get('type', 'unknown')
                })
        
        # Sort by score and limit results with diversity
        results.sort(key=lambda x: x["score"], reverse=True)
        
        # Apply diversity filtering to ensure we get different types of documents
        diverse_results = []
        seen_indices = set()
        
        # First pass: get top results from different indices
        for result in results:
            index_name = result["index"]
            if index_name not in seen_indices:
                diverse_results.append(result)
                seen_indices.add(index_name)
                if len(diverse_results) >= min(limit, 6):  # Ensure diversity in top 6
                    break
        
        # Second pass: fill remaining slots with highest scoring documents
        for result in results:
            if result not in diverse_results:
                diverse_results.append(result)
                if len(diverse_results) >= limit:
                    break
        
        results = diverse_results
        
        return {
            "results": results,
            "total": len(results),
            "query_type": query_type,
            "search_terms": search_terms,
            "indices_searched": ["fallback_data"],
            "fallback_mode": True
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
        """Check if Elasticsearch client is connected or fallback data is available"""
        if self.client:
            try:
                return self.client.ping()
            except:
                pass
        
        # Return True if we have fallback data available
        return bool(self.fallback_data)
    
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
            # Use fallback data
            return self._search_fallback_data(query_type, search_terms, limit)
        
        try:
            if not self.client.ping():
                # Use fallback data
                return self._search_fallback_data(query_type, search_terms, limit)
        except:
            # Use fallback data
            return self._search_fallback_data(query_type, search_terms, limit)
        
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
elasticsearch_client = ElasticsearchMCPClient()