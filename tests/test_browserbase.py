import pytest
import os
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from app.registry import (
    create_playwright_session,
    create_selenium_session,
    browser_search,
    browser_navigate,
    browser_extract,
    browser_screenshot,
    close_browser_session
)
from app.models import WorkflowContext


@pytest.fixture
def workflow_context():
    """Create a test workflow context."""
    return WorkflowContext(request_id="test-browserbase-123")


@pytest.fixture
def mock_browserbase_session():
    """Create a mock Browserbase session."""
    session = MagicMock()
    session.id = "mock-session-id"
    session.connect_url = "wss://browserbase.com/ws/mock"
    session.selenium_remote_url = "https://browserbase.com/wd/hub/mock"
    session.signing_key = "mock-signing-key"
    return session


@pytest.fixture
def mock_playwright():
    """Create a mock Playwright instance."""
    # Create nested mocks for the Playwright API
    page = AsyncMock()
    page.goto = AsyncMock()
    page.title = AsyncMock(return_value="Mock Page Title")
    page.content = AsyncMock(return_value="<html><body>Mock content</body></html>")
    page.url = AsyncMock(return_value="https://example.com")
    page.query_selector_all = AsyncMock(return_value=[])
    page.screenshot = AsyncMock(return_value=b"mock_screenshot_bytes")
    
    context = MagicMock()
    context.pages = [page]
    
    browser = MagicMock()
    browser.contexts = [context]
    browser.close = AsyncMock()
    
    chromium = MagicMock()
    chromium.connect_over_cdp = AsyncMock(return_value=browser)
    
    playwright = MagicMock()
    playwright.chromium = chromium
    playwright.start = AsyncMock(return_value=playwright)
    
    return {
        "instance": playwright,
        "browser": browser,
        "context": context,
        "page": page
    }


@pytest.fixture
def mock_selenium_driver():
    """Create a mock Selenium WebDriver."""
    driver = MagicMock()
    driver.get = MagicMock()
    driver.title = "Mock Selenium Title"
    driver.page_source = "<html><body>Mock Selenium content</body></html>"
    driver.current_url = "https://example.com"
    driver.find_elements = MagicMock(return_value=[])
    driver.get_screenshot_as_png = MagicMock(return_value=b"mock_selenium_screenshot")
    driver.quit = MagicMock()
    
    # Mock the execute_script method for waiting
    driver.execute_script = MagicMock(return_value="complete")
    
    return driver


@pytest.mark.asyncio
@patch("app.registry.browserbase_client.sessions.create")
@patch("app.registry.async_playwright")
async def test_create_playwright_session(mock_async_playwright, mock_create_session, mock_playwright, mock_browserbase_session):
    """Test creating a Playwright session with Browserbase."""
    # Configure mocks
    mock_create_session.return_value = mock_browserbase_session
    mock_async_playwright.return_value = mock_playwright["instance"]
    
    # Call the function
    session = await create_playwright_session()
    
    # Verify the session was created correctly
    assert session["type"] == "playwright"
    assert "page" in session
    assert "browser" in session
    assert "context" in session
    assert "browserbase_session" in session
    assert session["browserbase_session"] == mock_browserbase_session
    
    # Verify the correct methods were called
    mock_create_session.assert_called_once()
    mock_playwright["instance"].chromium.connect_over_cdp.assert_called_once_with(mock_browserbase_session.connect_url)


@pytest.mark.asyncio
@patch("app.registry.browserbase_client.sessions.create")
@patch("app.registry.webdriver.Remote")
async def test_create_selenium_session(mock_webdriver_remote, mock_create_session, mock_browserbase_session, mock_selenium_driver):
    """Test creating a Selenium session with Browserbase."""
    # Configure mocks
    mock_create_session.return_value = mock_browserbase_session
    mock_webdriver_remote.return_value = mock_selenium_driver
    
    # Call the function
    session = await create_selenium_session()
    
    # Verify the session was created correctly
    assert session["type"] == "selenium"
    assert "driver" in session
    assert session["driver"] == mock_selenium_driver
    assert "browserbase_session" in session
    assert session["browserbase_session"] == mock_browserbase_session
    
    # Verify the correct methods were called
    mock_create_session.assert_called_once()
    mock_webdriver_remote.assert_called_once()


@pytest.mark.asyncio
@patch("app.registry.create_playwright_session")
async def test_browser_navigate_playwright(mock_create_session, workflow_context, mock_playwright):
    """Test browser navigate with Playwright."""
    # Configure mock
    mock_create_session.return_value = {
        "page": mock_playwright["page"],
        "browser": mock_playwright["browser"],
        "context": mock_playwright["context"],
        "browserbase_session": MagicMock(),
        "type": "playwright"
    }
    
    # Call the function
    result = await browser_navigate({
        "url": "https://example.com",
        "wait_for_load": True
    }, workflow_context)
    
    # Verify the result
    assert result["success"] is True
    assert result["url"] == "https://example.com"
    assert result["title"] == "Mock Page Title"
    
    # Verify the page was navigated to
    mock_playwright["page"].goto.assert_called_once()
    
    # Verify context was updated
    assert "current_page" in workflow_context.variables
    assert workflow_context.variables["current_page"]["url"] == "https://example.com"
    
    # Verify execution log
    assert len(workflow_context.execution_log) == 1
    assert workflow_context.execution_log[0]["tool"] == "browser.navigate"
    assert workflow_context.execution_log[0]["browser_type"] == "playwright"


@pytest.mark.asyncio
@patch("app.registry.create_selenium_session")
async def test_browser_navigate_selenium(mock_create_session, workflow_context, mock_selenium_driver):
    """Test browser navigate with Selenium."""
    # Configure mock
    mock_create_session.return_value = {
        "driver": mock_selenium_driver,
        "browserbase_session": MagicMock(),
        "type": "selenium"
    }
    
    # Call the function
    result = await browser_navigate({
        "url": "https://example.com",
        "wait_for_load": True,
        "use_selenium": True
    }, workflow_context)
    
    # Verify the result
    assert result["success"] is True
    assert result["url"] == "https://example.com"
    assert result["title"] == "Mock Selenium Title"
    
    # Verify the page was navigated to
    mock_selenium_driver.get.assert_called_once_with("https://example.com")
    
    # Verify context was updated
    assert "current_page" in workflow_context.variables
    assert workflow_context.variables["current_page"]["url"] == "https://example.com"
    
    # Verify execution log
    assert len(workflow_context.execution_log) == 1
    assert workflow_context.execution_log[0]["tool"] == "browser.navigate"
    assert workflow_context.execution_log[0]["browser_type"] == "selenium"


@pytest.mark.asyncio
@patch("app.registry.create_playwright_session")
async def test_browser_screenshot(mock_create_session, workflow_context, mock_playwright):
    """Test browser screenshot with Playwright."""
    # Configure mock
    mock_create_session.return_value = {
        "page": mock_playwright["page"],
        "browser": mock_playwright["browser"],
        "context": mock_playwright["context"],
        "browserbase_session": MagicMock(),
        "type": "playwright"
    }
    
    # First navigate to a page
    await browser_navigate({
        "url": "https://example.com"
    }, workflow_context)
    
    # Now take a screenshot
    result = await browser_screenshot({
        "full_page": True
    }, workflow_context)
    
    # Verify the result
    assert result["success"] is True
    assert "screenshot" in result
    assert result["screenshot"]["format"] == "png"
    assert "data" in result["screenshot"]
    
    # Verify the screenshot was taken
    mock_playwright["page"].screenshot.assert_called_once()
    
    # Verify execution log
    assert len(workflow_context.execution_log) == 2
    assert workflow_context.execution_log[1]["tool"] == "browser.screenshot"


@pytest.mark.asyncio
@patch("app.registry.create_selenium_session")
async def test_browser_screenshot_selenium(mock_create_session, workflow_context, mock_selenium_driver):
    """Test browser screenshot with Selenium."""
    # Configure mock
    mock_create_session.return_value = {
        "driver": mock_selenium_driver,
        "browserbase_session": MagicMock(),
        "type": "selenium"
    }
    
    # First navigate to a page
    await browser_navigate({
        "url": "https://example.com",
        "use_selenium": True
    }, workflow_context)
    
    # Now take a screenshot
    result = await browser_screenshot({}, workflow_context)
    
    # Verify the result
    assert result["success"] is True
    assert "screenshot" in result
    assert result["screenshot"]["format"] == "png"
    assert "data" in result["screenshot"]
    
    # Verify the screenshot was taken
    mock_selenium_driver.get_screenshot_as_png.assert_called_once()
    
    # Verify execution log
    assert len(workflow_context.execution_log) == 2
    assert workflow_context.execution_log[1]["tool"] == "browser.screenshot"


@pytest.mark.asyncio
@patch("app.registry.create_playwright_session")
async def test_close_browser_session(mock_create_session, workflow_context, mock_playwright):
    """Test closing a browser session."""
    # Configure mock
    mock_browserbase_session = MagicMock()
    mock_browserbase_session.id = "test-session-id"
    
    mock_create_session.return_value = {
        "page": mock_playwright["page"],
        "browser": mock_playwright["browser"],
        "context": mock_playwright["context"],
        "browserbase_session": mock_browserbase_session,
        "type": "playwright"
    }
    
    # First navigate to a page to create a session
    await browser_navigate({
        "url": "https://example.com"
    }, workflow_context)
    
    # Now close the session
    result = await close_browser_session(workflow_context)
    
    # Verify the result
    assert result["success"] is True
    assert "replay_url" in result
    assert result["replay_url"] == "https://browserbase.com/sessions/test-session-id"
    
    # Verify the browser was closed
    mock_playwright["page"].close.assert_called_once()
    mock_playwright["browser"].close.assert_called_once()
    
    # Verify execution log
    assert len(workflow_context.execution_log) == 2
    assert workflow_context.execution_log[1]["tool"] == "browser.close"


@pytest.mark.asyncio
@patch("app.registry.create_selenium_session")
async def test_close_browser_session_selenium(mock_create_session, workflow_context, mock_selenium_driver):
    """Test closing a Selenium browser session."""
    # Configure mock
    mock_browserbase_session = MagicMock()
    mock_browserbase_session.id = "test-selenium-session-id"
    
    mock_create_session.return_value = {
        "driver": mock_selenium_driver,
        "browserbase_session": mock_browserbase_session,
        "type": "selenium"
    }
    
    # First navigate to a page to create a session
    await browser_navigate({
        "url": "https://example.com",
        "use_selenium": True
    }, workflow_context)
    
    # Now close the session
    result = await close_browser_session(workflow_context)
    
    # Verify the result
    assert result["success"] is True
    assert "replay_url" in result
    assert result["replay_url"] == "https://browserbase.com/sessions/test-selenium-session-id"
    
    # Verify the driver was quit
    mock_selenium_driver.quit.assert_called_once()
    
    # Verify execution log
    assert len(workflow_context.execution_log) == 2
    assert workflow_context.execution_log[1]["tool"] == "browser.close"


if __name__ == "__main__":
    # Run the tests
    pytest.main(["-xvs", __file__])
