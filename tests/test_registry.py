import pytest
import json
import asyncio
from unittest.mock import patch, MagicMock

from app.registry import (
    browser_search, 
    browser_navigate,
    browser_extract,
    browser_screenshot,
    python_exec,
    http_request,
    get_tool_adapter,
    list_available_tools,
    TOOL_REGISTRY
)
from app.models import WorkflowContext
from app.openrouter import openrouter_client


@pytest.fixture
def workflow_context():
    """Create a test workflow context."""
    return WorkflowContext(request_id="test-123")


@pytest.mark.asyncio
async def test_browser_search(workflow_context):
    """Test browser search tool adapter."""
    result = await browser_search({"query": "test query", "max_results": 2}, workflow_context)
    
    assert "results" in result
    assert len(result["results"]) == 2
    assert "query" in result
    assert result["query"] == "test query"
    
    # Check execution log
    assert len(workflow_context.execution_log) == 1
    assert workflow_context.execution_log[0]["tool"] == "browser.search"
    assert workflow_context.execution_log[0]["query"] == "test query"


@pytest.mark.asyncio
async def test_browser_search_no_query(workflow_context):
    """Test browser search with no query."""
    result = await browser_search({}, workflow_context)
    
    assert "error" in result
    assert result["error"] == "No search query provided"


@pytest.mark.asyncio
async def test_browser_navigate(workflow_context):
    """Test browser navigate tool adapter."""
    url = "https://example.com"
    result = await browser_navigate({"url": url}, workflow_context)
    
    assert "url" in result
    assert result["url"] == url
    assert "title" in result
    assert "success" in result
    assert result["success"] is True
    
    # Check that page was stored in context
    assert "current_page" in workflow_context.variables
    assert workflow_context.variables["current_page"]["url"] == url
    
    # Check execution log
    assert len(workflow_context.execution_log) == 1
    assert workflow_context.execution_log[0]["tool"] == "browser.navigate"


@pytest.mark.asyncio
async def test_browser_navigate_no_url(workflow_context):
    """Test browser navigate with no URL."""
    result = await browser_navigate({}, workflow_context)
    
    assert "error" in result
    assert result["error"] == "No URL provided"


@pytest.mark.asyncio
async def test_browser_extract_no_page(workflow_context):
    """Test browser extract with no active page."""
    result = await browser_extract({"selector": "h1"}, workflow_context)
    
    assert "error" in result
    assert result["error"] == "No active page. Use browser.navigate first."


@pytest.mark.asyncio
async def test_browser_extract_with_page(workflow_context):
    """Test browser extract with active page."""
    # First navigate to a page
    url = "https://example.com"
    await browser_navigate({"url": url}, workflow_context)
    
    # Now extract content
    result = await browser_extract({"selector": "h1"}, workflow_context)
    
    assert "results" in result
    assert len(result["results"]) > 0
    assert "selector" in result
    assert result["selector"] == "h1"
    
    # Check execution log
    assert len(workflow_context.execution_log) == 2
    assert workflow_context.execution_log[1]["tool"] == "browser.extract"


@pytest.mark.asyncio
async def test_browser_screenshot(workflow_context):
    """Test browser screenshot tool adapter."""
    # First navigate to a page
    url = "https://example.com"
    await browser_navigate({"url": url}, workflow_context)
    
    # Now take screenshot
    result = await browser_screenshot({}, workflow_context)
    
    assert "screenshot" in result
    assert "url" in result
    assert result["url"] == url
    assert "success" in result
    assert result["success"] is True
    
    # Check execution log
    assert len(workflow_context.execution_log) == 2
    assert workflow_context.execution_log[1]["tool"] == "browser.screenshot"


@pytest.mark.asyncio
async def test_browser_screenshot_no_page(workflow_context):
    """Test browser screenshot with no active page."""
    result = await browser_screenshot({}, workflow_context)
    
    assert "error" in result
    assert result["error"] == "No active page. Use browser.navigate first."


@pytest.mark.asyncio
async def test_python_exec(workflow_context):
    """Test Python execution tool adapter."""
    result = await python_exec({"code": "print('hello')"}, workflow_context)
    
    assert "output" in result
    assert "status" in result
    assert result["status"] == "success"
    
    # Check execution log
    assert len(workflow_context.execution_log) == 1
    assert workflow_context.execution_log[0]["tool"] == "python.exec"


@pytest.mark.asyncio
async def test_python_exec_no_code(workflow_context):
    """Test Python execution with no code."""
    result = await python_exec({}, workflow_context)
    
    assert "error" in result
    assert result["error"] == "No code provided"


@pytest.mark.asyncio
@patch("httpx.AsyncClient.request")
async def test_http_request(mock_request, workflow_context):
    """Test HTTP request tool adapter."""
    # Mock response
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.headers = {"Content-Type": "application/json"}
    mock_response.text = '{"success": true}'
    mock_response.url = "https://api.example.com"
    mock_request.return_value = mock_response
    
    result = await http_request({
        "url": "https://api.example.com",
        "method": "GET"
    }, workflow_context)
    
    assert "status_code" in result
    assert result["status_code"] == 200
    assert "headers" in result
    assert "text" in result
    assert "url" in result
    
    # Check execution log
    assert len(workflow_context.execution_log) == 1
    assert workflow_context.execution_log[0]["tool"] == "http.request"
    assert workflow_context.execution_log[0]["method"] == "GET"


@pytest.mark.asyncio
async def test_http_request_no_url(workflow_context):
    """Test HTTP request with no URL."""
    result = await http_request({}, workflow_context)
    
    assert "error" in result
    assert result["error"] == "No URL provided"


def test_get_tool_adapter():
    """Test get_tool_adapter function."""
    # Test valid tool
    adapter = get_tool_adapter("browser.search")
    assert adapter == browser_search
    
    # Test invalid tool
    with pytest.raises(ValueError):
        get_tool_adapter("invalid.tool")


def test_list_available_tools():
    """Test list_available_tools function."""
    tools = list_available_tools()
    
    # Check that all tools are listed
    assert "browser.search" in tools
    assert "browser.navigate" in tools
    assert "browser.extract" in tools
    assert "browser.screenshot" in tools
    assert "python.exec" in tools
    assert "http.request" in tools
    
    # Check that descriptions are provided
    for tool_name, description in tools.items():
        assert isinstance(description, str)
        assert len(description) > 0


def test_tool_registry():
    """Test TOOL_REGISTRY contains all expected tools."""
    assert "browser.search" in TOOL_REGISTRY
    assert "browser.navigate" in TOOL_REGISTRY
    assert "browser.extract" in TOOL_REGISTRY
    assert "browser.screenshot" in TOOL_REGISTRY
    assert "python.exec" in TOOL_REGISTRY
    assert "http.request" in TOOL_REGISTRY
    
    # Check that all tools are functions
    for tool_name, adapter in TOOL_REGISTRY.items():
        assert callable(adapter)


@pytest.mark.asyncio
@patch("app.openrouter.openrouter_client._chat_completion_sync")
async def test_openrouter_tool_calling(mock_completion, workflow_context):
    """Test OpenRouter integration for tool calling."""
    # Mock the OpenRouter API response
    mock_completion.return_value = {
        "id": "test-123",
        "object": "chat.completion",
        "created": 1625072592,
        "model": "openai/gpt-3.5-turbo",
        "choices": [{
            "index": 0,
            "message": {
                "role": "assistant",
                "tool_calls": [{
                    "id": "call_123",
                    "type": "function",
                    "function": {
                        "name": "browser.search",
                        "arguments": '{"query": "OpenRouter API", "max_results": 3}'
                    }
                }]
            },
            "finish_reason": "tool_calls"
        }]
    }
    
    # Format tools for OpenAI format
    tools = openrouter_client.format_tools_for_openai(["browser.search"])
    
    # Test chat completion with tools
    response = await openrouter_client.chat_completion(
        model="openai/gpt-3.5-turbo",
        messages=[{"role": "user", "content": "Search for OpenRouter API"}],
        tools=tools
    )
    
    # Verify the response
    assert "choices" in response
    assert len(response["choices"]) > 0
    assert "message" in response["choices"][0]
    assert "tool_calls" in response["choices"][0]["message"]
    
    # Verify that the tool call is for browser.search
    tool_call = response["choices"][0]["message"]["tool_calls"][0]
    assert tool_call["function"]["name"] == "browser.search"
    
    # Verify that the arguments are correctly formatted
    arguments = json.loads(tool_call["function"]["arguments"])
    assert "query" in arguments
    assert arguments["query"] == "OpenRouter API"


@pytest.mark.asyncio
async def test_format_tools_for_openai():
    """Test formatting registry tools into OpenAI format."""
    # Test with a single tool
    single_tools = openrouter_client.format_tools_for_openai(["browser.search"])
    assert len(single_tools) == 1
    assert single_tools[0]["type"] == "function"
    assert single_tools[0]["function"]["name"] == "browser.search"
    assert "parameters" in single_tools[0]["function"]
    
    # Test with multiple tools
    multi_tools = openrouter_client.format_tools_for_openai([
        "browser.search", 
        "browser.navigate", 
        "http.request"
    ])
    assert len(multi_tools) == 3
    
    # Check that tool names are correct
    tool_names = [tool["function"]["name"] for tool in multi_tools]
    assert "browser.search" in tool_names
    assert "browser.navigate" in tool_names
    assert "http.request" in tool_names
    
    # Check that required parameters are specified
    for tool in multi_tools:
        if tool["function"]["name"] == "browser.search":
            assert "required" in tool["function"]["parameters"]
            assert "query" in tool["function"]["parameters"]["required"]
        elif tool["function"]["name"] == "browser.navigate":
            assert "required" in tool["function"]["parameters"]
            assert "url" in tool["function"]["parameters"]["required"]
        elif tool["function"]["name"] == "http.request":
            assert "required" in tool["function"]["parameters"]
            assert "url" in tool["function"]["parameters"]["required"]
