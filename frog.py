"""
Frog 🐸 - Python SDK for the frog micro-service
"""
import httpx
import json
from typing import List, Dict, Any, Optional, AsyncGenerator, Generator


class FrogClient:
    """Sync client for frog micro-service."""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-4o-mini",
        stream: bool = False,
        workflow: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        tools: Optional[List[str]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Send chat completion request."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "workflow": workflow,
            "workflow_id": workflow_id,
            "tools": tools,
            **kwargs
        }
        
        with httpx.Client() as client:
            response = client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            if stream:
                return self._parse_stream(response.text)
            else:
                return response.json()
    
    def _parse_stream(self, text: str) -> Generator[Dict[str, Any], None, None]:
        """Parse streaming response."""
        for line in text.split('\n'):
            if line.startswith('data: ') and line != 'data: [DONE]':
                try:
                    yield json.loads(line[6:])
                except json.JSONDecodeError:
                    continue


class AsyncFrogClient:
    """Async client for frog micro-service."""
    
    def __init__(self, api_key: str, base_url: str = "http://localhost:8000"):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.headers = {"Authorization": f"Bearer {api_key}"}
    
    async def chat(
        self,
        messages: List[Dict[str, str]],
        model: str = "openai/gpt-4o-mini",
        stream: bool = False,
        workflow: Optional[Dict[str, Any]] = None,
        workflow_id: Optional[str] = None,
        tools: Optional[List[str]] = None,
        **kwargs
    ):
        """Send async chat completion request."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": stream,
            "workflow": workflow,
            "workflow_id": workflow_id,
            "tools": tools,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            
            if stream:
                return self._parse_stream_async(response.aiter_lines())
            else:
                return response.json()
    
    async def _parse_stream_async(self, lines) -> AsyncGenerator[Dict[str, Any], None]:
        """Parse async streaming response."""
        async for line in lines:
            if line.startswith('data: ') and line != 'data: [DONE]':
                try:
                    yield json.loads(line[6:])
                except json.JSONDecodeError:
                    continue


# Convenience functions
def chat(messages: List[Dict[str, str]], api_key: str, **kwargs) -> Dict[str, Any]:
    """Quick sync chat function."""
    client = FrogClient(api_key)
    return client.chat(messages, **kwargs)


async def achat(messages: List[Dict[str, str]], api_key: str, **kwargs) -> Dict[str, Any]:
    """Quick async chat function."""
    client = AsyncFrogClient(api_key)
    return await client.chat(messages, **kwargs) 