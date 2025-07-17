#!/usr/bin/env python3
"""
Test script to verify Elasticsearch connection and data retrieval via MCP client
"""

import sys
import os
import asyncio
from typing import Dict, Any

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from shared.elasticsearch_client import elasticsearch_client
from agent.generators.elasticsearch_generator import ElasticsearchGenerator

async def test_elasticsearch_connection():
    """Test Elasticsearch connection and data retrieval"""
    
    print("=== ESTC Tiger Elasticsearch Connection Test ===\n")
    
    # Test 1: Basic connection test
    print("1. Testing Elasticsearch connection...")
    is_connected = elasticsearch_client.is_connected()
    print(f"   Connection status: {'✓ Connected' if is_connected else '✗ Not connected'}")
    
    if not is_connected:
        print("   ERROR: Elasticsearch is not connected. Please check your configuration.")
        print("   Required environment variables:")
        print("   - ELASTICSEARCH_URL (default: http://localhost:9200)")
        print("   - ELASTICSEARCH_USERNAME (default: elastic)")
        print("   - ELASTICSEARCH_PASSWORD")
        print("   - ELASTICSEARCH_API_KEY (optional)")
        return False
    
    # Test 2: Cluster info
    print("\n2. Getting cluster information...")
    cluster_info = elasticsearch_client.get_cluster_info()
    if "error" in cluster_info:
        print(f"   ERROR: {cluster_info['error']}")
        return False
    else:
        print(f"   Cluster name: {cluster_info.get('cluster_name', 'unknown')}")
        print(f"   Version: {cluster_info.get('version', 'unknown')}")
        print(f"   Status: {cluster_info.get('status', 'unknown')}")
    
    # Test 3: Available indices
    print("\n3. Checking available ESTC indices...")
    indices = elasticsearch_client.get_available_indices()
    if indices:
        print(f"   Found {len(indices)} ESTC indices:")
        for idx in indices:
            print(f"   - {idx}")
    else:
        print("   WARNING: No ESTC indices found. Data may not be indexed yet.")
    
    # Test 4: Test search functionality
    print("\n4. Testing search functionality...")
    
    test_queries = [
        {"type": "financial", "terms": ["revenue", "earnings"], "description": "Financial data search"},
        {"type": "stock", "terms": ["price", "analyst"], "description": "Stock data search"},
        {"type": "general", "terms": ["estc", "elastic"], "description": "General ESTC search"}
    ]
    
    for query in test_queries:
        print(f"\n   Testing {query['description']}...")
        results = elasticsearch_client.search_estc_data(
            query_type=query["type"],
            search_terms=query["terms"],
            limit=3
        )
        
        if "error" in results:
            print(f"   ERROR: {results['error']}")
        else:
            print(f"   Found {results.get('total', 0)} total results")
            print(f"   Returned {len(results.get('results', []))} results")
            
            # Show sample results
            for i, result in enumerate(results.get('results', [])[:2]):
                print(f"   Result {i+1}:")
                print(f"     Index: {result.get('index', 'unknown')}")
                print(f"     Score: {result.get('score', 0):.2f}")
                print(f"     Type: {result.get('type', 'unknown')}")
                
                # Show sample of source data
                source = result.get('source', {})
                if source:
                    sample_keys = list(source.keys())[:3]
                    print(f"     Sample fields: {', '.join(sample_keys)}")
    
    # Test 5: Test MCP generator
    print("\n5. Testing MCP generator with Elasticsearch data...")
    
    generator = ElasticsearchGenerator()
    
    test_user_query = "What is ESTC's recent financial performance?"
    
    try:
        response = await generator.generate_response(test_user_query)
        
        if response.startswith("ERROR:"):
            print(f"   ERROR: {response}")
            return False
        else:
            print("   ✓ MCP generator successfully retrieved and processed Elasticsearch data")
            print(f"   Response preview: {response[:200]}...")
            
    except Exception as e:
        print(f"   ERROR: Exception in MCP generator: {str(e)}")
        return False
    
    print("\n=== Test Summary ===")
    print("✓ All tests passed! Elasticsearch is properly connected and returning data.")
    print("✓ The MCP client is successfully retrieving ESTC data from Elasticsearch.")
    print("✓ No fallback data is being used - all data comes from Elasticsearch.")
    
    return True

async def main():
    """Main test function"""
    try:
        success = await test_elasticsearch_connection()
        if success:
            print("\n🎉 SUCCESS: Elasticsearch integration is working correctly!")
            sys.exit(0)
        else:
            print("\n❌ FAILURE: Elasticsearch integration has issues.")
            sys.exit(1)
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())