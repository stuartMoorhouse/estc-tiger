#!/usr/bin/env python3
"""
Test script to verify Elasticsearch search is working with v2 indices
"""

import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add current directory to path
sys.path.append('.')

from shared.elasticsearch_client import elasticsearch_service

def test_elasticsearch_search():
    print("Testing Elasticsearch connection and search...")
    
    # Test connection
    print(f"Elasticsearch URL: {elasticsearch_service.es_url}")
    print(f"Connected: {elasticsearch_service.is_connected()}")
    
    if not elasticsearch_service.is_connected():
        print("❌ Not connected to Elasticsearch")
        return
    
    # Get cluster info
    cluster_info = elasticsearch_service.get_cluster_info()
    print(f"Cluster: {cluster_info}")
    
    # Test search for analyst data
    print("\n🔍 Testing search for 'analyst target rating'...")
    result = elasticsearch_service.search_estc_data(
        query_type='stock',
        search_terms=['analyst', 'target', 'rating'],
        limit=5
    )
    
    print(f"Search method: {result.get('search_method', 'unknown')}")
    print(f"Indices searched: {result.get('indices_searched', [])}")
    print(f"Results found: {len(result.get('results', []))}")
    print(f"Total hits: {result.get('total', 0)}")
    print(f"ES version: {result.get('es_version', 'unknown')}")
    
    if 'error' in result:
        print(f"❌ Search error: {result['error']}")
        return
    
    if result.get('results'):
        print("\n📋 Search results:")
        for i, doc in enumerate(result['results'][:3]):
            print(f"  {i+1}. Index: {doc['index']}")
            print(f"     Score: {doc['score']:.3f}")
            print(f"     Doc ID: {doc['document_id']}")
            print(f"     Type: {doc['type']}")
            if 'title' in doc['source']:
                print(f"     Title: {doc['source']['title'][:60]}...")
            print()
    
    # Test a different query type
    print("🔍 Testing search for 'revenue growth'...")
    result2 = elasticsearch_service.search_estc_data(
        query_type='financial',
        search_terms=['revenue', 'growth'],
        limit=3
    )
    
    print(f"Financial search - Results: {len(result2.get('results', []))}")
    print(f"Financial search - Indices: {result2.get('indices_searched', [])}")

if __name__ == "__main__":
    test_elasticsearch_search()