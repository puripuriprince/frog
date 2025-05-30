#!/usr/bin/env python3
"""
Quick test script for frog micro-service
"""
import requests
import json

BASE_URL = "http://localhost:8000"
API_KEY = "sk-frog_test"

def test_health():
    """Test health endpoint"""
    response = requests.get(f"{BASE_URL}/health")
    print(f"Health check: {response.status_code}")
    print(f"Response: {response.json()}")
    return response.status_code == 200

def test_simple_chat():
    """Test simple chat completion"""
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Hello, frog!"}]
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json=payload
    )
    
    print(f"Simple chat: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data['choices'][0]['message']['content']}")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200

def test_workflow_chat():
    """Test chat with workflow"""
    workflow = {
        "id": "test_workflow",
        "name": "Test Search Workflow",
        "nodes": [{
            "id": "search",
            "tool": {
                "type": "browser.search",
                "parameters": {"query": "FastAPI tutorials"}
            },
            "depends_on": []
        }]
    }
    
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": "Search for FastAPI tutorials"}],
        "workflow": workflow
    }
    
    response = requests.post(
        f"{BASE_URL}/v1/chat/completions",
        headers={"Authorization": f"Bearer {API_KEY}"},
        json=payload
    )
    
    print(f"Workflow chat: {response.status_code}")
    if response.status_code == 200:
        data = response.json()
        print(f"Response: {data['choices'][0]['message']['content'][:200]}...")
    else:
        print(f"Error: {response.text}")
    
    return response.status_code == 200

if __name__ == "__main__":
    print("🐸 Testing Frog micro-service...")
    print("=" * 50)
    
    tests = [
        ("Health Check", test_health),
        ("Simple Chat", test_simple_chat),
        ("Workflow Chat", test_workflow_chat),
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{name}:")
        try:
            success = test_func()
            results.append((name, success))
            print(f"✅ {name}: {'PASSED' if success else 'FAILED'}")
        except Exception as e:
            print(f"❌ {name}: ERROR - {e}")
            results.append((name, False))
    
    print("\n" + "=" * 50)
    print("Test Summary:")
    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"  {name}: {status}")
    
    all_passed = all(success for _, success in results)
    print(f"\nOverall: {'🎉 ALL TESTS PASSED' if all_passed else '⚠️  SOME TESTS FAILED'}") 