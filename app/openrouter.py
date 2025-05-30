"""
OpenRouter client for proxying chat completion requests.
"""
import httpx
import json
from typing import Dict, Any, AsyncGenerator
from app.config import settings


class OpenRouterClient:
    """Client for OpenRouter API."""
    
    def __init__(self):
        self.api_key = settings.openrouter_api_key
        self.base_url = settings.openrouter_base_url
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    async def chat_completion(
        self, 
        model: str, 
        messages: list, 
        stream: bool = False,
        **kwargs
    ):
        """Send chat completion request to OpenRouter."""
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not configured")
        
        if stream:
            return self._chat_completion_stream(model, messages, **kwargs)
        else:
            return await self._chat_completion_sync(model, messages, **kwargs)
    
    async def _chat_completion_sync(self, model: str, messages: list, **kwargs) -> Dict[str, Any]:
        """Handle non-streaming chat completion."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": False,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            return response.json()
    
    async def _chat_completion_stream(self, model: str, messages: list, **kwargs) -> AsyncGenerator[str, None]:
        """Handle streaming chat completion."""
        payload = {
            "model": model,
            "messages": messages,
            "stream": True,
            **kwargs
        }
        
        async with httpx.AsyncClient() as client:
            async with client.stream(
                "POST",
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=60
            ) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line.strip():
                        yield line
    
    async def list_models(self) -> Dict[str, Any]:
        """List available models from OpenRouter."""
        if not self.api_key:
            return {"data": [], "object": "list"}
        
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/models",
                headers=self.headers,
                timeout=30
            )
            response.raise_for_status()
            return response.json()


# Global client instance
openrouter_client = OpenRouterClient() 