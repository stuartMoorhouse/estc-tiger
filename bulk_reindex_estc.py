#!/usr/bin/env python3
"""
Bulk reindex ESTC data from original indices to v2 with ELSER embeddings
"""

import os
import sys
from elasticsearch import Elasticsearch
from elasticsearch.helpers import bulk
from dotenv import load_dotenv
import json
from datetime import datetime

# Load environment variables
load_dotenv()

# Create Elasticsearch client
es = Elasticsearch(
    os.getenv('ELASTICSEARCH_URL'),
    api_key=os.getenv('ELASTICSEARCH_API_KEY'),
    verify_certs=True
)

def generate_content_for_vector(doc_source):
    """Generate content_for_vector field from document fields"""
    content_parts = []
    
    # Add all fields as formatted text
    for field, value in doc_source.items():
        if field in ['content_for_vector', 'ml']:  # Skip these fields
            continue
            
        # Format field name nicely
        field_name = field.replace('_', ' ').title()
        
        # Add to content
        if value is not None:
            if isinstance(value, list):
                content_parts.append(f"{field_name}: {', '.join(map(str, value))}")
            else:
                content_parts.append(f"{field_name}: {str(value)}")
    
    return '\n'.join(content_parts)

def create_v2_index(source_index, target_index):
    """Create v2 index with proper mapping"""
    
    # Delete target if exists
    if es.indices.exists(index=target_index):
        response = input(f"  Target index {target_index} already exists. Delete and recreate? (y/n): ")
        if response.lower() != 'y':
            return False
        es.indices.delete(index=target_index)
        print(f"  Deleted existing index {target_index}")
    
    # Get source mapping
    source_mapping = es.indices.get_mapping(index=source_index)
    source_properties = source_mapping[source_index]['mappings'].get('properties', {})
    
    # Create v2 mapping
    v2_properties = source_properties.copy()
    v2_properties['content_for_vector'] = {"type": "text"}
    v2_properties['ml'] = {
        "properties": {
            "tokens": {"type": "sparse_vector"},
            "model_id": {
                "type": "text",
                "fields": {
                    "keyword": {
                        "type": "keyword",
                        "ignore_above": 256
                    }
                }
            }
        }
    }
    
    # Create index
    es.indices.create(
        index=target_index,
        body={
            "mappings": {
                "properties": v2_properties
            }
        }
    )
    print(f"  Created target index {target_index}")
    return True

def process_documents(source_index, target_index):
    """Process all documents from source to target with ELSER"""
    
    # Get all documents from source
    response = es.search(
        index=source_index,
        scroll='2m',
        size=1000,
        body={"query": {"match_all": {}}}
    )
    
    scroll_id = response['_scroll_id']
    documents = response['hits']['hits']
    
    all_docs = []
    while documents:
        for doc in documents:
            # Create new document with content_for_vector
            new_doc = doc['_source'].copy()
            new_doc['content_for_vector'] = generate_content_for_vector(doc['_source'])
            
            # Prepare for bulk indexing
            all_docs.append({
                '_index': target_index,
                '_id': doc['_id'],
                '_source': new_doc,
                'pipeline': 'elser-v2-pipeline'
            })
        
        # Get next batch
        response = es.scroll(scroll_id=scroll_id, scroll='2m')
        documents = response['hits']['hits']
    
    # Clear scroll
    es.clear_scroll(scroll_id=scroll_id)
    
    return all_docs

def bulk_index_with_elser(docs, target_index):
    """Bulk index documents with ELSER pipeline"""
    
    # Index documents in batches
    batch_size = 10  # Small batches for ELSER
    total_docs = len(docs)
    
    for i in range(0, total_docs, batch_size):
        batch = docs[i:i + batch_size]
        
        try:
            # Use bulk helper with pipeline
            actions = []
            for doc in batch:
                action = {
                    '_index': target_index,
                    '_id': doc['_id'],
                    '_source': doc['_source'],
                    'pipeline': 'elser-v2-pipeline'
                }
                actions.append(action)
            
            # Execute bulk request
            success, failed = bulk(es, actions, index=target_index)
            
            print(f"    Batch {i//batch_size + 1}: {success} indexed, {len(failed)} failed")
            
            if failed:
                for failure in failed:
                    print(f"      Failed: {failure}")
                    
        except Exception as e:
            print(f"    Batch {i//batch_size + 1} failed: {e}")
            continue

def reindex_single_index(source_index, target_index):
    """Reindex a single index with ELSER"""
    print(f"\nReindexing {source_index} -> {target_index}")
    
    # Get document count
    source_count = es.count(index=source_index)['count']
    print(f"  Source documents: {source_count}")
    
    # Create target index
    if not create_v2_index(source_index, target_index):
        return False
    
    # Process documents
    print(f"  Processing documents...")
    docs = process_documents(source_index, target_index)
    
    # Bulk index with ELSER
    print(f"  Indexing {len(docs)} documents with ELSER...")
    bulk_index_with_elser(docs, target_index)
    
    # Verify results
    target_count = es.count(index=target_index)['count']
    print(f"  Target documents: {target_count}")
    
    if target_count == source_count:
        print(f"  ✓ Successfully reindexed {source_count} documents")
        return True
    else:
        print(f"  ✗ Document count mismatch: {source_count} -> {target_count}")
        return False

def main():
    print("ESTC Bulk Reindexing with ELSER")
    print("=" * 40)
    
    # Check connection
    try:
        info = es.info()
        print(f"Connected to Elasticsearch {info['version']['number']}")
    except Exception as e:
        print(f"Failed to connect: {e}")
        sys.exit(1)
    
    # Check ELSER pipeline
    try:
        pipeline = es.ingest.get_pipeline(id='elser-v2-pipeline')
        print("✓ ELSER pipeline found")
    except:
        print("✗ ELSER pipeline not found")
        sys.exit(1)
    
    # Get source indices
    indices = es.indices.get_alias(index="estc-*")
    source_indices = sorted([idx for idx in indices.keys() if not idx.endswith('-v2')])
    
    if not source_indices:
        print("No source indices found")
        sys.exit(1)
    
    print(f"\nFound {len(source_indices)} indices to reindex:")
    for idx in source_indices:
        count = es.count(index=idx)['count']
        print(f"  - {idx}: {count} documents")
    
    # Confirm
    response = input("\nProceed with reindexing? (y/n): ")
    if response.lower() != 'y':
        print("Cancelled")
        sys.exit(0)
    
    # Reindex each
    success_count = 0
    for source_index in source_indices:
        target_index = f"{source_index}-v2"
        if reindex_single_index(source_index, target_index):
            success_count += 1
    
    print(f"\n{'='*40}")
    print(f"Reindexing complete: {success_count}/{len(source_indices)} successful")

if __name__ == "__main__":
    main()