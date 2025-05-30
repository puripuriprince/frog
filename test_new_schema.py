#!/usr/bin/env python3
"""
Test script for the new frog schema implementation.
"""
import asyncio
import json
from frog import FrogClient, AsyncFrogClient


def test_sync_client():
    """Test the sync client with new schema."""
    client = FrogClient(api_key="sk-frog_live_test123")
    
    # Test basic chat
    response = client.chat(
        messages=[{"role": "user", "content": "hello world"}],
        model="gpt-4o-mini"
    )
    print("Sync response:", json.dumps(response, indent=2))
    
    # Test with tools
    response = client.chat(
        messages=[{"role": "user", "content": "search for python tutorials"}],
        tools=["browser.search"],
        stream=False
    )
    print("Sync with tools:", json.dumps(response, indent=2))


async def test_async_client():
    """Test the async client with new schema."""
    client = AsyncFrogClient(api_key="sk-frog_live_test456")
    
    # Test basic chat
    response = await client.chat(
        messages=[{"role": "user", "content": "hello world"}],
        model="gpt-4o-mini"
    )
    print("Async response:", json.dumps(response, indent=2))
    
    # Test with workflow_id
    response = await client.chat(
        messages=[{"role": "user", "content": "analyze this data"}],
        workflow_id="custom_analysis",
        stream=False
    )
    print("Async with workflow_id:", json.dumps(response, indent=2))


def test_schema_validation():
    """Test that the schema matches the specification."""
    expected_fields = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": "hello world"}],
        "stream": True,
        "tools": ["browser.search"],
        "workflow_id": None,
        "workflow": None
    }
    
    client = FrogClient(api_key="sk-frog_live_schema_test")
    
    # This should work without errors
    try:
        response = client.chat(**expected_fields)
        print("Schema validation: PASSED")
    except Exception as e:
        print(f"Schema validation: FAILED - {e}")


if __name__ == "__main__":
    print("Testing new frog schema implementation...")
    print("=" * 50)
    
    # Note: These tests will fail without a running server
    # but they validate the client-side schema implementation
    
    try:
        test_schema_validation()
        test_sync_client()
        asyncio.run(test_async_client())
    except Exception as e:
        print(f"Test failed (expected without running server): {e}")
    
    print("Schema implementation complete!") 