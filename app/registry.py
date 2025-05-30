import asyncio
import httpx
import json
from typing import Dict, Any, Callable, Awaitable
from app.models import WorkflowContext


# Type alias for tool adapters
ToolAdapter = Callable[[Dict[str, Any], WorkflowContext], Awaitable[Dict[str, Any]]]


async def browser_search(params: Dict[str, Any], ctx: WorkflowContext) -> Dict[str, Any]:
    """Browser search tool adapter."""
    query = params.get("query", "")
    max_results = params.get("max_results", 5)
    
    if not query:
        return {"error": "No search query provided"}
    
    # Mock search results for MVP
    # TODO: Integrate with real search API (SerpAPI, Bing, etc.)
    results = [
        {
            "title": f"Search result {i+1} for: {query}",
            "url": f"https://example.com/result-{i+1}",
            "snippet": f"This is a mock search result snippet for query '{query}'. Result number {i+1}."
        }
        for i in range(min(max_results, 3))
    ]
    
    ctx.execution_log.append({
        "tool": "browser.search",
        "query": query,
        "results_count": len(results)
    })
    
    return {"results": results, "query": query}


async def python_exec(params: Dict[str, Any], ctx: WorkflowContext) -> Dict[str, Any]:
    """Python code execution tool adapter."""
    code = params.get("code", "")
    timeout = params.get("timeout", 10)
    
    if not code:
        return {"error": "No code provided"}
    
    # For security, this is a mock implementation
    # TODO: Implement sandboxed execution (Docker, pyodide, etc.)
    try:
        # Simulate code execution
        await asyncio.sleep(0.1)  # Simulate execution time
        
        # Mock successful execution
        output = f"# Executed code:\n{code}\n\n# Output:\nCode executed successfully (mock)"
        
        ctx.execution_log.append({
            "tool": "python.exec",
            "code_length": len(code),
            "status": "success"
        })
        
        return {"output": output, "status": "success"}
        
    except Exception as e:
        ctx.execution_log.append({
            "tool": "python.exec",
            "error": str(e),
            "status": "error"
        })
        
        return {"error": str(e), "status": "error"}


async def http_request(params: Dict[str, Any], ctx: WorkflowContext) -> Dict[str, Any]:
    """HTTP request tool adapter."""
    url = params.get("url", "")
    method = params.get("method", "GET").upper()
    headers = params.get("headers", {})
    data = params.get("data")
    timeout = params.get("timeout", 30)
    
    if not url:
        return {"error": "No URL provided"}
    
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.request(
                method=method,
                url=url,
                headers=headers,
                json=data if data else None
            )
            
            result = {
                "status_code": response.status_code,
                "headers": dict(response.headers),
                "text": response.text[:1000],  # Limit response size
                "url": str(response.url)
            }
            
            ctx.execution_log.append({
                "tool": "http.request",
                "method": method,
                "url": url,
                "status_code": response.status_code
            })
            
            return result
            
    except Exception as e:
        ctx.execution_log.append({
            "tool": "http.request",
            "error": str(e),
            "status": "error"
        })
        
        return {"error": str(e), "status": "error"}


# Tool registry mapping tool names to adapter functions
TOOL_REGISTRY: Dict[str, ToolAdapter] = {
    "browser.search": browser_search,
    "python.exec": python_exec,
    "http.request": http_request,
}


def get_tool_adapter(tool_name: str) -> ToolAdapter:
    """Get tool adapter by name."""
    adapter = TOOL_REGISTRY.get(tool_name)
    if not adapter:
        raise ValueError(f"Unknown tool: {tool_name}")
    return adapter


def list_available_tools() -> Dict[str, str]:
    """List all available tools with descriptions."""
    return {
        "browser.search": "Search the web for information",
        "python.exec": "Execute Python code (sandboxed)",
        "http.request": "Make HTTP requests to APIs",
    } 