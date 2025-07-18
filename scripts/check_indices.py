#!/usr/bin/env python3
"""
Script to check all ESTC indices and compare document counts between original and v2 indices
"""

import os
import sys
from typing import Dict, List

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from elasticsearch import Elasticsearch
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class IndexChecker:
    """Check all ESTC indices and document counts"""
    
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
    
    def check_all_indices(self):
        """Check all ESTC indices and their document counts"""
        try:
            # Get all indices that start with 'estc-'
            response = self.client.indices.get_alias(index="estc-*", ignore_unavailable=True)
            all_indices = list(response.keys())
            
            print(f"\n📊 Found {len(all_indices)} ESTC indices:")
            
            # Separate original and v2 indices
            original_indices = [idx for idx in all_indices if not idx.endswith('-v2')]
            v2_indices = [idx for idx in all_indices if idx.endswith('-v2')]
            
            print(f"\n📋 ORIGINAL INDICES ({len(original_indices)}):")
            original_counts = {}
            total_original = 0
            
            for index in sorted(original_indices):
                try:
                    count_response = self.client.count(index=index)
                    doc_count = count_response['count']
                    original_counts[index] = doc_count
                    total_original += doc_count
                    print(f"   {index}: {doc_count} documents")
                except Exception as e:
                    print(f"   {index}: Error counting - {e}")
                    original_counts[index] = 0
            
            print(f"\n📋 V2 INDICES ({len(v2_indices)}):")
            v2_counts = {}
            total_v2 = 0
            
            for index in sorted(v2_indices):
                try:
                    count_response = self.client.count(index=index)
                    doc_count = count_response['count']
                    v2_counts[index] = doc_count
                    total_v2 += doc_count
                    print(f"   {index}: {doc_count} documents")
                except Exception as e:
                    print(f"   {index}: Error counting - {e}")
                    v2_counts[index] = 0
            
            print(f"\n📊 SUMMARY:")
            print(f"   Original indices total: {total_original} documents")
            print(f"   V2 indices total: {total_v2} documents")
            print(f"   Difference: {total_original - total_v2} documents")
            
            # Check for missing indices
            print(f"\n🔍 MISSING V2 INDICES:")
            missing_v2 = []
            for orig_index in original_indices:
                expected_v2 = f"{orig_index}-v2"
                if expected_v2 not in v2_indices:
                    missing_v2.append(orig_index)
                    print(f"   ❌ {orig_index} → {expected_v2} (MISSING)")
            
            if not missing_v2:
                print("   ✅ All original indices have corresponding v2 versions")
            
            # Compare document counts
            print(f"\n📈 DOCUMENT COUNT COMPARISON:")
            for orig_index in original_indices:
                expected_v2 = f"{orig_index}-v2"
                orig_count = original_counts.get(orig_index, 0)
                v2_count = v2_counts.get(expected_v2, 0)
                
                if expected_v2 in v2_indices:
                    if orig_count == v2_count:
                        print(f"   ✅ {orig_index}: {orig_count} → {expected_v2}: {v2_count}")
                    else:
                        print(f"   ❌ {orig_index}: {orig_count} → {expected_v2}: {v2_count} (MISMATCH)")
                else:
                    print(f"   ❌ {orig_index}: {orig_count} → {expected_v2}: NOT CREATED")
            
            return {
                'original_indices': original_counts,
                'v2_indices': v2_counts,
                'missing_v2': missing_v2,
                'total_original': total_original,
                'total_v2': total_v2
            }
            
        except Exception as e:
            print(f"❌ Error checking indices: {str(e)}")
            return None


if __name__ == "__main__":
    checker = IndexChecker()
    results = checker.check_all_indices()
    
    if results and results['total_original'] != results['total_v2']:
        print(f"\n⚠️  ISSUE DETECTED: Document count mismatch!")
        print(f"   Expected: {results['total_original']} documents")
        print(f"   Found: {results['total_v2']} documents") 
        print(f"   Missing: {results['total_original'] - results['total_v2']} documents")
        
        if results['missing_v2']:
            print(f"\n🔧 Need to create v2 indices for: {', '.join(results['missing_v2'])}")
    else:
        print(f"\n✅ All indices successfully migrated with matching document counts!")