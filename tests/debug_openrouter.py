#!/usr/bin/env python3
"""
Debug script to test OpenRouter integration directly.
"""
import asyncio
import httpx
import json
import os
from app.config import settings


async def test_openrouter_direct():
    """Test OpenRouter API directly."""
    api_key = settings.openrouter_api_key
    
    if not api_key:
        print("❌ OPENROUTER_API_KEY not set in settings")
        print(f"   Direct os.getenv: {os.getenv('OPENROUTER_API_KEY', 'NOT_SET')}")
        print(f"   Settings value: {settings.openrouter_api_key}")
        return
    
    print(f"✅ API Key found: {api_key[:20]}...")
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "openai/gpt-4o-mini",
        "messages": [
            {"role": "user", "content": "Say hello"}
        ]
    }
    
    try:
        print("🔄 Testing direct OpenRouter request...")
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')
                print(f"✅ OpenRouter works: {content}")
            else:
                print(f"❌ OpenRouter error: {response.text}")
                
    except Exception as e:
        print(f"❌ OpenRouter request failed: {e}")


async def test_frog_server():
    """Test if frog server is running."""
    try:
        print("🔄 Testing frog server...")
        async with httpx.AsyncClient() as client:
            response = await client.get("http://localhost:8000/v1/models", timeout=5)
            print(f"✅ Frog server is running: {response.status_code}")
    except Exception as e:
        print(f"❌ Frog server not running: {e}")


async def test_frog_with_openrouter():
    """Test frog server with OpenRouter."""
    try:
        print("🔄 Testing frog + OpenRouter...")
        headers = {
            "Authorization": "Bearer sk-frog_live_test",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": "openai/gpt-4o-mini",
            "messages": [
                {"role": "user", "content": "What is 2+2?"}
            ],
            "stream": False
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "http://localhost:8000/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=30
            )
            
            print(f"Status: {response.status_code}")
            if response.status_code == 200:
                result = response.json()
                content = result.get('choices', [{}])[0].get('message', {}).get('content', 'No content')
                print(f"✅ Frog + OpenRouter works: {content}")
            else:
                print(f"❌ Frog + OpenRouter error: {response.text}")
                
    except Exception as e:
        print(f"❌ Frog + OpenRouter failed: {e}")


async def main():
    print("🐸 Debugging OpenRouter integration...")
    print("=" * 50)
    
    await test_openrouter_direct()
    print()
    await test_frog_server()
    print()
    await test_frog_with_openrouter()


if __name__ == "__main__":
    asyncio.run(main()) 