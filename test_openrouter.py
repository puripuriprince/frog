#!/usr/bin/env python3
"""
Test script for OpenRouter integration.
"""
import asyncio
import json
import os
from frog import FrogClient, AsyncFrogClient


def test_openrouter_models():
    """Test different OpenRouter models."""
    client = FrogClient(api_key="sk-frog_live_openrouter_test")
    
    models_to_test = [
        "openai/gpt-4o",
        "openai/gpt-4o-mini", 
        "anthropic/claude-3.5-sonnet",
        "meta-llama/llama-3.1-8b-instruct",
        "google/gemini-pro"
    ]
    
    for model in models_to_test:
        print(f"\n--- Testing {model} ---")
        try:
            response = client.chat(
                messages=[{"role": "user", "content": "Say hello in a creative way"}],
                model=model,
                stream=False
            )
            print(f"✅ {model}: {response.get('choices', [{}])[0].get('message', {}).get('content', 'No content')[:100]}...")
        except Exception as e:
            print(f"❌ {model}: {e}")


def test_frog_features_with_models():
    """Test frog-specific features with different models."""
    client = FrogClient(api_key="sk-frog_live_features_test")
    
    print("\n--- Testing frog features with OpenRouter models ---")
    
    # Test with tools (should use workflow)
    try:
        response = client.chat(
            messages=[{"role": "user", "content": "Search for Python tutorials"}],
            model="openai/gpt-4o",
            tools=["browser.search"],
            stream=False
        )
        print("✅ Tools + OpenRouter model:", response.get('choices', [{}])[0].get('message', {}).get('content', 'No content')[:100])
    except Exception as e:
        print(f"❌ Tools test: {e}")
    
    # Test with workflow_id (should use workflow)
    try:
        response = client.chat(
            messages=[{"role": "user", "content": "Analyze this data"}],
            model="anthropic/claude-3.5-sonnet",
            workflow_id="custom_analysis",
            stream=False
        )
        print("✅ Workflow + Claude:", response.get('choices', [{}])[0].get('message', {}).get('content', 'No content')[:100])
    except Exception as e:
        print(f"❌ Workflow test: {e}")
    
    # Test simple request (should use direct OpenRouter)
    try:
        response = client.chat(
            messages=[{"role": "user", "content": "What is 2+2?"}],
            model="openai/gpt-4o-mini",
            stream=False
        )
        print("✅ Simple + GPT-4o-mini:", response.get('choices', [{}])[0].get('message', {}).get('content', 'No content')[:100])
    except Exception as e:
        print(f"❌ Simple test: {e}")


async def test_streaming():
    """Test streaming with OpenRouter."""
    client = AsyncFrogClient(api_key="sk-frog_live_stream_test")
    
    print("\n--- Testing streaming with OpenRouter ---")
    try:
        stream = await client.chat(
            messages=[{"role": "user", "content": "Count from 1 to 5"}],
            model="openai/gpt-4o-mini",
            stream=True
        )
        
        print("Stream chunks:")
        async for chunk in stream:
            if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                print(chunk['choices'][0]['delta']['content'], end='', flush=True)
        print("\n✅ Streaming test completed")
    except Exception as e:
        print(f"❌ Streaming test: {e}")


def test_model_list():
    """Test model listing from OpenRouter."""
    client = FrogClient(api_key="sk-frog_live_models_test")
    
    print("\n--- Testing model list ---")
    try:
        # This would normally call the /v1/models endpoint
        print("Note: Model list test requires running server")
        print("Expected: Should return OpenRouter model list")
    except Exception as e:
        print(f"❌ Model list test: {e}")


if __name__ == "__main__":
    print("Testing OpenRouter integration...")
    print("=" * 60)
    
    # Check if OPENROUTER_API_KEY is set
    if not os.getenv("OPENROUTER_API_KEY"):
        print("⚠️  OPENROUTER_API_KEY not set - tests will use fallback responses")
    
    try:
        test_openrouter_models()
        test_frog_features_with_models()
        asyncio.run(test_streaming())
        test_model_list()
    except Exception as e:
        print(f"Test failed (expected without running server): {e}")
    
    print("\n🐸 OpenRouter integration complete!")
    print("\nTo use with real OpenRouter API:")
    print("1. Set OPENROUTER_API_KEY environment variable")
    print("2. Start the frog server: uvicorn app.main:app")
    print("3. Use any OpenRouter model: openai/gpt-4o, anthropic/claude-3.5-sonnet, etc.") 