#!/usr/bin/env python3
"""
Script to enhance Elasticsearch indices with ELSER sparse vectors for improved semantic search.
This creates new vector-enhanced indices and reindexes all documents with sparse vector embeddings.
"""

import os
import sys
from typing import Dict, List, Any
import json
from datetime import datetime

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elasticsearch import Elasticsearch
from elasticsearch.helpers import reindex
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class ElasticsearchVectorEnhancer:
    """Enhances Elasticsearch indices with ELSER sparse vectors for semantic search"""
    
    def __init__(self):
        # Initialize Elasticsearch client
        self.es_url = os.getenv('ELASTICSEARCH_URL', 'http://localhost:9200')
        self.es_username = os.getenv('ELASTICSEARCH_USERNAME', 'elastic')
        self.es_password = os.getenv('ELASTICSEARCH_PASSWORD', '')
        self.es_api_key = os.getenv('ELASTICSEARCH_API_KEY', '')
        
        # Connect to Elasticsearch
        if self.es_api_key:
            self.client = Elasticsearch(
                [self.es_url],
                api_key=self.es_api_key,
                verify_certs=False,
                ssl_show_warn=False
            )
        elif self.es_username and self.es_password:
            self.client = Elasticsearch(
                [self.es_url],
                basic_auth=(self.es_username, self.es_password),
                verify_certs=False,
                ssl_show_warn=False
            )
        else:
            self.client = Elasticsearch(
                [self.es_url],
                verify_certs=False,
                ssl_show_warn=False
            )
        
        # Verify connection
        if not self.client.ping():
            raise ConnectionError(f"Failed to connect to Elasticsearch at {self.es_url}")
        
        print(f"✅ Connected to Elasticsearch at {self.es_url}")
        
        # Define ACTUAL indices found in the cluster (missing v2 versions)
        self.indices_to_enhance = [
            'estc-scenario-analysis',
            'estc-guidance-data', 
            'estc-analyst-data',
            'estc-rsu-relevant',
            'estc-market-events',
            'estc-acquisition-history',
            'estc-competitive-data',
            'estc-partnership-data',
            'estc-risk-factors',
            'estc-quarterly-data',
            'estc-customer-metrics'
        ]
    
    def create_elser_pipeline(self) -> bool:
        """Create the ELSER inference pipeline for sparse vector generation"""
        pipeline_id = "elser-v2-pipeline"
        
        try:
            # Create inference pipeline using the inference API (ES 9.0 syntax)
            pipeline_config = {
                "processors": [
                    {
                        "inference": {
                            "model_id": ".elser-2-elasticsearch",
                            "input_output": [
                                {
                                    "input_field": "content_for_vector",
                                    "output_field": "ml.tokens"
                                }
                            ],
                            "on_failure": [
                                {
                                    "set": {
                                        "field": "_ingest.on_failure_message",
                                        "value": "Failed to generate sparse vector"
                                    }
                                }
                            ]
                        }
                    }
                ]
            }
            
            # Create the pipeline
            self.client.ingest.put_pipeline(
                id=pipeline_id,
                body=pipeline_config
            )
            
            print(f"✅ Created ELSER inference pipeline: {pipeline_id}")
            return True
            
        except Exception as e:
            print(f"❌ Error creating ELSER pipeline: {str(e)}")
            print("⚠️  Make sure ELSER v2 model is deployed in your Elasticsearch cluster")
            print("   Deploy it via Kibana: Machine Learning > Model Management > ELSER")
            return False
    
    def create_vector_enhanced_index(self, original_index: str) -> str:
        """Create a new vector-enhanced version of an index"""
        new_index = f"{original_index}-v2"
        
        try:
            # Get original index mapping
            original_mapping = self.client.indices.get_mapping(index=original_index)
            
            # Extract properties from original mapping
            original_properties = {}
            for index_name, mapping_data in original_mapping.items():
                original_properties = mapping_data['mappings'].get('properties', {})
                break
            
            # Create enhanced mapping with sparse vector field
            enhanced_mapping = {
                "mappings": {
                    "properties": {
                        **original_properties,  # Include all original fields
                        "content_for_vector": {
                            "type": "text",
                            "index": False  # Don't index this field directly
                        },
                        "ml": {
                            "properties": {
                                "tokens": {
                                    "type": "sparse_vector"  # ELSER sparse vector field
                                }
                            }
                        }
                    }
                },
                "settings": {
                    "index": {
                        "default_pipeline": "elser-v2-pipeline"  # Automatically apply ELSER
                    }
                }
            }
            
            # Delete the index if it already exists
            if self.client.indices.exists(index=new_index):
                print(f"⚠️  Index {new_index} already exists, deleting...")
                self.client.indices.delete(index=new_index)
            
            # Create the new index
            self.client.indices.create(index=new_index, body=enhanced_mapping)
            print(f"✅ Created vector-enhanced index: {new_index}")
            
            return new_index
            
        except Exception as e:
            print(f"❌ Error creating vector-enhanced index for {original_index}: {str(e)}")
            return None
    
    def prepare_document_for_vector(self, doc: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare a document for vector generation by creating content_for_vector field"""
        # Combine relevant text fields for vector generation
        text_parts = []
        
        # Add title/name if available
        if 'title' in doc:
            text_parts.append(f"Title: {doc['title']}")
        elif 'name' in doc:
            text_parts.append(f"Name: {doc['name']}")
        
        # Add description/summary
        if 'description' in doc:
            text_parts.append(f"Description: {doc['description']}")
        elif 'summary' in doc:
            text_parts.append(f"Summary: {doc['summary']}")
        
        # Add main content
        if 'content' in doc:
            text_parts.append(doc['content'])
        
        # Add financial metrics if available
        financial_fields = [
            'revenue', 'revenue_growth_yoy', 'operating_margin', 
            'free_cash_flow_margin', 'net_expansion_rate'
        ]
        
        financial_parts = []
        for field in financial_fields:
            if field in doc and doc[field]:
                field_name = field.replace('_', ' ').title()
                financial_parts.append(f"{field_name}: {doc[field]}")
        
        if financial_parts:
            text_parts.append("Financial Metrics: " + ", ".join(financial_parts))
        
        # Add document type if available
        if 'document_type' in doc:
            text_parts.append(f"Type: {doc['document_type']}")
        
        # Combine all parts
        content_for_vector = "\n".join(text_parts)
        
        # Add the field to the document
        doc['content_for_vector'] = content_for_vector
        
        return doc
    
    def reindex_with_vectors(self, original_index: str, new_index: str) -> bool:
        """Reindex documents from original to vector-enhanced index"""
        try:
            # Count documents in original index
            count_response = self.client.count(index=original_index)
            total_docs = count_response['count']
            print(f"📊 Reindexing {total_docs} documents from {original_index} to {new_index}")
            
            # Reindex with transformation
            success_count = 0
            batch_size = 10  # Smaller batch size to avoid timeouts
            
            # Scroll through all documents
            response = self.client.search(
                index=original_index,
                scroll='2m',
                body={
                    "size": batch_size,
                    "query": {"match_all": {}}
                }
            )
            
            scroll_id = response['_scroll_id']
            hits = response['hits']['hits']
            
            while hits:
                # Prepare batch for indexing
                bulk_actions = []
                
                for hit in hits:
                    doc = hit['_source']
                    doc_id = hit['_id']
                    
                    # Prepare document for vector generation
                    enhanced_doc = self.prepare_document_for_vector(doc)
                    
                    # Add to bulk actions
                    bulk_actions.append({
                        "_index": new_index,
                        "_id": doc_id,
                        "_source": enhanced_doc
                    })
                
                # Bulk index the batch
                if bulk_actions:
                    # Format for elasticsearch-py bulk API
                    bulk_body = []
                    for action in bulk_actions:
                        # Add action header
                        bulk_body.append({
                            "index": {
                                "_index": action["_index"],
                                "_id": action["_id"]
                            }
                        })
                        # Add document source
                        bulk_body.append(action["_source"])
                    
                    bulk_response = self.client.bulk(body=bulk_body)
                    if not bulk_response['errors']:
                        success_count += len(bulk_actions)
                        print(f"  → Processed {success_count}/{total_docs} documents")
                    else:
                        print(f"  ⚠️  Some documents failed to index")
                        # Print first error for debugging
                        for item in bulk_response['items']:
                            if 'index' in item and 'error' in item['index']:
                                print(f"     Error: {item['index']['error']}")
                                break
                
                # Get next batch
                response = self.client.scroll(scroll_id=scroll_id, scroll='2m')
                hits = response['hits']['hits']
            
            # Clear scroll
            self.client.clear_scroll(scroll_id=scroll_id)
            
            print(f"✅ Successfully reindexed {success_count}/{total_docs} documents")
            return success_count == total_docs
            
        except Exception as e:
            print(f"❌ Error reindexing {original_index}: {str(e)}")
            return False
    
    def update_index_aliases(self, original_index: str, new_index: str):
        """Update aliases to point to new vector-enhanced indices"""
        try:
            # Create alias for backward compatibility
            alias_name = f"{original_index}-latest"
            
            # Remove alias from old index if it exists
            if self.client.indices.exists_alias(name=alias_name):
                self.client.indices.delete_alias(index="*", name=alias_name)
            
            # Add alias to new index
            self.client.indices.put_alias(index=new_index, name=alias_name)
            
            print(f"✅ Updated alias {alias_name} to point to {new_index}")
            
        except Exception as e:
            print(f"⚠️  Warning: Could not update alias for {original_index}: {str(e)}")
    
    def enhance_all_indices(self):
        """Main method to enhance all indices with ELSER vectors"""
        print("\n🚀 Starting Elasticsearch Vector Enhancement Process\n")
        
        # Step 1: Create ELSER pipeline
        print("Step 1: Creating ELSER inference pipeline")
        if not self.create_elser_pipeline():
            print("❌ Failed to create ELSER pipeline. Exiting.")
            return False
        
        # Step 2: Process each index
        print("\nStep 2: Creating vector-enhanced indices and reindexing")
        
        successful_indices = []
        failed_indices = []
        
        for original_index in self.indices_to_enhance:
            # Check if index exists
            if not self.client.indices.exists(index=original_index):
                print(f"⚠️  Skipping {original_index} - index does not exist")
                continue
            
            print(f"\n📁 Processing {original_index}...")
            
            # Create vector-enhanced index
            new_index = self.create_vector_enhanced_index(original_index)
            if not new_index:
                failed_indices.append(original_index)
                continue
            
            # Reindex with vectors
            if self.reindex_with_vectors(original_index, new_index):
                successful_indices.append((original_index, new_index))
                # Update aliases
                self.update_index_aliases(original_index, new_index)
            else:
                failed_indices.append(original_index)
        
        # Summary
        print("\n" + "="*60)
        print("📊 VECTOR ENHANCEMENT SUMMARY")
        print("="*60)
        print(f"✅ Successfully enhanced: {len(successful_indices)} indices")
        for orig, new in successful_indices:
            print(f"   • {orig} → {new}")
        
        if failed_indices:
            print(f"\n❌ Failed: {len(failed_indices)} indices")
            for idx in failed_indices:
                print(f"   • {idx}")
        
        print("\n✨ Vector enhancement process complete!")
        
        # Save the mapping of old to new indices
        mapping = {orig: new for orig, new in successful_indices}
        with open('vector_index_mapping.json', 'w') as f:
            json.dump(mapping, f, indent=2)
        print(f"\n💾 Saved index mapping to vector_index_mapping.json")
        
        return len(failed_indices) == 0


if __name__ == "__main__":
    enhancer = ElasticsearchVectorEnhancer()
    success = enhancer.enhance_all_indices()
    
    if success:
        print("\n✅ All indices successfully enhanced with ELSER vectors!")
        print("\n📝 Next steps:")
        print("1. Update ElasticsearchService to use the new v2 indices")
        print("2. Implement hybrid search with RRF")
        print("3. Test improved retrieval performance")
    else:
        print("\n⚠️  Some indices failed to enhance. Check the errors above.")
        sys.exit(1)