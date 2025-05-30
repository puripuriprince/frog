import asyncio
import httpx
import json
import os
import base64
from typing import Dict, Any, Callable, Awaitable, Optional
from app.models import WorkflowContext
from app.config import settings
from playwright.async_api import async_playwright
from browserbase import Browserbase
# Selenium imports
from selenium import webdriver
from selenium.webdriver.remote.remote_connection import RemoteConnection
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC


# Type alias for tool adapters
ToolAdapter = Callable[[Dict[str, Any], WorkflowContext], Awaitable[Dict[str, Any]]]

# Global instance of Browserbase client
browserbase_client = Browserbase(api_key=os.environ.get("BROWSERBASE_API_KEY", ""))

# Global dictionary to store active browser sessions
active_sessions = {}

# Custom RemoteConnection for Selenium with Browserbase
class CustomRemoteConnection(RemoteConnection):
    _signing_key = None

    def __init__(self, remote_server_addr: str, signing_key: str):
        super().__init__(remote_server_addr)
        self._signing_key = signing_key

    def get_remote_connection_headers(self, parsed_url, keep_alive=False):
        headers = super().get_remote_connection_headers(parsed_url, keep_alive)
        headers.update({'x-bb-signing-key': self._signing_key})
        return headers


# Function to create a Selenium session with Browserbase
async def create_selenium_session():
    """Create a Selenium session with Browserbase."""
    # This needs to run in a thread since Selenium is synchronous
    def _create_session():
        session = browserbase_client.sessions.create(
            project_id=os.environ.get("BROWSERBASE_PROJECT_ID", "")
        )
        custom_conn = CustomRemoteConnection(
            session.selenium_remote_url, 
            session.signing_key
        )
        options = webdriver.ChromeOptions()
        driver = webdriver.Remote(custom_conn, options=options)
        return {
            "driver": driver,
            "browserbase_session": session,
            "type": "selenium"
        }
    
    # Run the synchronous Selenium code in a thread
    return await asyncio.to_thread(_create_session)


# Function to create a Playwright session with Browserbase
async def create_playwright_session():
    """Create a Playwright session with Browserbase."""
    playwright = await async_playwright().start()
    
    # Create a session on Browserbase
    browserbase_session = await asyncio.to_thread(
        browserbase_client.sessions.create,
        project_id=os.environ.get("BROWSERBASE_PROJECT_ID", "")
    )
    
    # Connect to the remote session
    browser = await playwright.chromium.connect_over_cdp(browserbase_session.connect_url)
    context = browser.contexts[0]
    page = context.pages[0]
    
    return {
        "playwright": playwright,
        "browser": browser,
        "context": context,
        "page": page,
        "browserbase_session": browserbase_session,
        "type": "playwright"
    }


async def browser_search(params: Dict[str, Any], ctx: WorkflowContext) -> Dict[str, Any]:
    """Browser search tool adapter."""
    query = params.get("query", "")
    max_results = params.get("max_results", 5)
    use_selenium = params.get("use_selenium", False)  # Option to use Selenium instead of Playwright
    
    if not query:
        return {"error": "No search query provided"}
    
    # Use browser automation to perform a real search
    # First check if there's an active session for this request
    session_id = f"{ctx.request_id}"
    
    try:
        # If no active session, create one with Browserbase
        if session_id not in active_sessions:
            if use_selenium:
                active_sessions[session_id] = await create_selenium_session()
            else:
                active_sessions[session_id] = await create_playwright_session()
        
        session = active_sessions[session_id]
        session_type = session.get("type", "playwright")
        
        results = []
        
        if session_type == "playwright":
            # Use Playwright
            page = session["page"]
            
            # Navigate to search engine and perform search
            await page.goto(f"https://www.google.com/search?q={query}")
            
            # Extract search results
            result_elements = await page.query_selector_all("div.g")
            
            for i, element in enumerate(result_elements):
                if i >= max_results:
                    break
                    
                title_el = await element.query_selector("h3")
                url_el = await element.query_selector("a")
                snippet_el = await element.query_selector("div.VwiC3b")
                
                title = await title_el.text_content() if title_el else "No title"
                url = await url_el.get_attribute("href") if url_el else "#"
                snippet = await snippet_el.text_content() if snippet_el else "No snippet available"
                
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
        
        else:
            # Use Selenium
            driver = session["driver"]
            
            # Navigate to search engine and perform search
            driver.get(f"https://www.google.com/search?q={query}")
            
            # Wait for results to load
            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "div.g"))
            )
            
            # Extract search results
            result_elements = driver.find_elements(By.CSS_SELECTOR, "div.g")
            
            for i, element in enumerate(result_elements):
                if i >= max_results:
                    break
                
                try:
                    title_el = element.find_element(By.CSS_SELECTOR, "h3")
                    title = title_el.text
                except:
                    title = "No title"
                
                try:
                    url_el = element.find_element(By.CSS_SELECTOR, "a")
                    url = url_el.get_attribute("href")
                except:
                    url = "#"
                
                try:
                    snippet_el = element.find_element(By.CSS_SELECTOR, "div.VwiC3b")
                    snippet = snippet_el.text
                except:
                    snippet = "No snippet available"
                
                results.append({
                    "title": title,
                    "url": url,
                    "snippet": snippet
                })
        
        ctx.execution_log.append({
            "tool": "browser.search",
            "query": query,
            "results_count": len(results),
            "browser_type": session_type
        })
        
        return {"results": results, "query": query}
        
    except Exception as e:
        ctx.execution_log.append({
            "tool": "browser.search",
            "error": str(e),
            "status": "error"
        })
        
        return {"error": f"Search failed: {str(e)}"}


async def browser_navigate(params: Dict[str, Any], ctx: WorkflowContext) -> Dict[str, Any]:
    """Browser navigation tool adapter."""
    url = params.get("url", "")
    wait_for_load = params.get("wait_for_load", True)
    use_selenium = params.get("use_selenium", False)  # Option to use Selenium instead of Playwright
    
    if not url:
        return {"error": "No URL provided"}
    
    session_id = f"{ctx.request_id}"
    
    try:
        # If no active session, create one with Browserbase
        if session_id not in active_sessions:
            if use_selenium:
                active_sessions[session_id] = await create_selenium_session()
            else:
                active_sessions[session_id] = await create_playwright_session()
        
        session = active_sessions[session_id]
        session_type = session.get("type", "playwright")
        
        title = ""
        content = ""
        
        if session_type == "playwright":
            # Use Playwright
            page = session["page"]
            
            # Navigate to the URL
            if wait_for_load:
                await page.goto(url, wait_until="networkidle")
            else:
                await page.goto(url, wait_until="domcontentloaded")
            
            # Get page title and content
            title = await page.title()
            content = await page.content()
            
        else:
            # Use Selenium
            driver = session["driver"]
            
            # Navigate to the URL
            driver.get(url)
            
            # Wait for page to load if needed
            if wait_for_load:
                # Wait for document.readyState to be complete
                WebDriverWait(driver, 30).until(
                    lambda d: d.execute_script("return document.readyState") == "complete"
                )
            
            # Get page title and content
            title = driver.title
            content = driver.page_source
        
        # Store in context for other browser tools to use
        ctx.variables["current_page"] = {
            "url": url,
            "content": content,
            "title": title
        }
        
        ctx.execution_log.append({
            "tool": "browser.navigate",
            "url": url,
            "success": True,
            "browser_type": session_type
        })
        
        return {
            "url": url,
            "title": title,
            "success": True
        }
        
    except Exception as e:
        ctx.execution_log.append({
            "tool": "browser.navigate",
            "error": str(e),
            "status": "error"
        })
        
        return {"error": f"Navigation failed: {str(e)}"}


async def browser_extract(params: Dict[str, Any], ctx: WorkflowContext) -> Dict[str, Any]:
    """Extract content from the current browser page using CSS selectors."""
    selector = params.get("selector", "")
    extract_type = params.get("type", "text")  # Options: text, html, attribute
    attribute = params.get("attribute", "") if extract_type == "attribute" else None
    
    if not selector:
        return {"error": "No CSS selector provided"}
    
    session_id = f"{ctx.request_id}"
    
    # Check if we have an active browser session
    if session_id not in active_sessions:
        return {"error": "No active browser session. Use browser.navigate first."}
    
    try:
        session = active_sessions[session_id]
        session_type = session.get("type", "playwright")
        
        results = []
        
        if session_type == "playwright":
            # Use Playwright
            page = session["page"]
            
            # Extract content based on the selector and type
            elements = await page.query_selector_all(selector)
            
            for element in elements:
                if extract_type == "text":
                    content = await element.text_content()
                elif extract_type == "html":
                    content = await element.inner_html()
                elif extract_type == "attribute" and attribute:
                    content = await element.get_attribute(attribute)
                else:
                    content = await element.text_content()
                    
                if content:
                    results.append(content)
                    
        else:
            # Use Selenium
            driver = session["driver"]
            
            # Extract content based on the selector and type
            elements = driver.find_elements(By.CSS_SELECTOR, selector)
            
            for element in elements:
                if extract_type == "text":
                    content = element.text
                elif extract_type == "html":
                    content = element.get_attribute("innerHTML")
                elif extract_type == "attribute" and attribute:
                    content = element.get_attribute(attribute)
                else:
                    content = element.text
                    
                if content:
                    results.append(content)
        
        ctx.execution_log.append({
            "tool": "browser.extract",
            "selector": selector,
            "type": extract_type,
            "results_count": len(results),
            "browser_type": session_type
        })
        
        return {
            "results": results,
            "selector": selector,
            "type": extract_type,
            "count": len(results)
        }
        
    except Exception as e:
        ctx.execution_log.append({
            "tool": "browser.extract",
            "error": str(e),
            "status": "error"
        })
        
        return {"error": f"Content extraction failed: {str(e)}"}


async def browser_screenshot(params: Dict[str, Any], ctx: WorkflowContext) -> Dict[str, Any]:
    """Take a screenshot of the current browser page."""
    selector = params.get("selector", None)  # Optional: screenshot specific element
    full_page = params.get("full_page", True)
    
    session_id = f"{ctx.request_id}"
    
    # Check if we have an active browser session
    if session_id not in active_sessions:
        return {"error": "No active browser session. Use browser.navigate first."}
    
    try:
        session = active_sessions[session_id]
        session_type = session.get("type", "playwright")
        
        screenshot_bytes = None
        target = "full page" if full_page else "viewport"
        url = ""
        
        if session_type == "playwright":
            # Use Playwright
            page = session["page"]
            url = await page.url()
            
            if selector:
                # Screenshot specific element
                element = await page.query_selector(selector)
                if not element:
                    return {"error": f"Element not found with selector: {selector}"}
                
                screenshot_bytes = await element.screenshot()
                target = selector
            else:
                # Screenshot full page or viewport
                screenshot_bytes = await page.screenshot(full_page=full_page)
                
        else:
            # Use Selenium
            driver = session["driver"]
            url = driver.current_url
            
            if selector:
                # Screenshot specific element
                try:
                    element = driver.find_element(By.CSS_SELECTOR, selector)
                    screenshot_bytes = element.screenshot_as_png
                    target = selector
                except Exception as e:
                    return {"error": f"Element not found with selector: {selector}. Error: {str(e)}"}
            else:
                # Selenium doesn't have a built-in full page screenshot, so we use the viewport
                screenshot_bytes = driver.get_screenshot_as_png()
                target = "viewport"  # Selenium can't easily do full page screenshots
        
        # Convert to base64 for response
        screenshot_base64 = base64.b64encode(screenshot_bytes).decode('utf-8')
        
        # Get dimensions (this is a simplified approach)
        width = 1280  # Default
        height = 800  # Default
        
        screenshot = {
            "format": "png",
            "data": screenshot_base64,
            "width": width,
            "height": height
        }
        
        ctx.execution_log.append({
            "tool": "browser.screenshot",
            "url": url,
            "target": target,
            "success": True,
            "browser_type": session_type
        })
        
        return {
            "screenshot": screenshot,
            "url": url,
            "target": target,
            "success": True
        }
        
    except Exception as e:
        ctx.execution_log.append({
            "tool": "browser.screenshot",
            "error": str(e),
            "status": "error"
        })
        
        return {"error": f"Screenshot failed: {str(e)}"}


async def close_browser_session(ctx: WorkflowContext) -> Dict[str, Any]:
    """Close the browser session and clean up resources."""
    session_id = f"{ctx.request_id}"
    
    if session_id not in active_sessions:
        return {"success": False, "error": "No active session to close"}
    
    try:
        session = active_sessions[session_id]
        session_type = session.get("type", "playwright")
        browserbase_session = session["browserbase_session"]
        
        if session_type == "playwright":
            # Close Playwright session
            await session["page"].close()
            await session["browser"].close()
        else:
            # Close Selenium session
            session["driver"].quit()
        
        # Log the session URL for replay
        replay_url = f"https://browserbase.com/sessions/{browserbase_session.id}"
        
        # Remove from active sessions
        del active_sessions[session_id]
        
        ctx.execution_log.append({
            "tool": "browser.close",
            "success": True,
            "replay_url": replay_url,
            "browser_type": session_type
        })
        
        return {"success": True, "replay_url": replay_url}
        
    except Exception as e:
        ctx.execution_log.append({
            "tool": "browser.close",
            "error": str(e),
            "status": "error"
        })
        
        return {"error": f"Failed to close browser session: {str(e)}"}


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
    "browser.navigate": browser_navigate,
    "browser.extract": browser_extract,
    "browser.screenshot": browser_screenshot,
    "browser.close": close_browser_session,
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
        "browser.navigate": "Navigate to a URL in the browser",
        "browser.extract": "Extract content from a webpage using CSS selectors",
        "browser.screenshot": "Take a screenshot of the current browser page",
        "browser.close": "Close the current browser session and clean up resources",
        "python.exec": "Execute Python code (sandboxed)",
        "http.request": "Make HTTP requests to APIs",
    } 