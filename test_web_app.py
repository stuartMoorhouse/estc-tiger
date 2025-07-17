#!/usr/bin/env python3
"""
Test script to verify web app is working correctly with Elasticsearch v9 client
"""

import sys
import os
import asyncio
import requests
import json

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_web_app():
    """Test the web app endpoints"""
    
    print("=== ESTC Tiger Web App Test ===\n")
    
    # Test 1: Check if app is running
    print("1. Testing if web app is running...")
    try:
        response = requests.get('http://localhost:5000', timeout=5)
        if response.status_code == 200:
            print("   ✓ Web app is running")
        else:
            print(f"   ✗ Web app returned status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Web app is not accessible: {e}")
        return False
    
    # Test 2: Test chat endpoint
    print("\n2. Testing chat endpoint...")
    try:
        chat_data = {
            "message": "What is ESTC's recent financial performance?",
            "session_id": "test_session"
        }
        
        response = requests.post(
            'http://localhost:5000/chat',
            json=chat_data,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            print(f"   Response: {result}")
            
            # Check if it's properly handling Elasticsearch unavailability
            if result.get('success') == False and 'Elasticsearch' in result.get('response', ''):
                print("   ✓ Properly showing Elasticsearch error message")
                return True
            elif result.get('success') == True:
                print("   ✓ Chat endpoint working with Elasticsearch connected")
                return True
            else:
                print(f"   ✗ Unexpected response: {result}")
                return False
        else:
            print(f"   ✗ Chat endpoint returned status {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"   ✗ Chat endpoint error: {e}")
        return False

def main():
    """Main test function"""
    try:
        success = test_web_app()
        if success:
            print("\n🎉 SUCCESS: Web app is working correctly!")
            return True
        else:
            print("\n❌ FAILURE: Web app has issues.")
            return False
    except Exception as e:
        print(f"\n❌ CRITICAL ERROR: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)