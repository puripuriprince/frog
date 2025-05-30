# Frog 🐸

OpenAI-compatible micro-service with agent workflows (~600 LOC)

[![FastAPI](https://img.shields.io/badge/FastAPI-0.104.1-009688.svg)](https://fastapi.tiangolo.com)
[![Python](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

## Overview

Frog is a lightweight FastAPI micro-service that exposes an OpenAI-compatible `/v1/chat/completions` endpoint with optional agent workflows and tools. Perfect for hackathons and rapid prototyping.

## Features

- 🔌 **OpenAI-compatible API** - Drop-in replacement for OpenAI chat completions
- 🤖 **Agent workflows** - Define DAG-based tool execution workflows  
- 🔧 **Built-in tools** - Browser search, Python execution, HTTP requests
- 🔐 **Secret management** - Encrypted storage with Fernet
- 📡 **Streaming support** - Real-time response streaming
- 🐍 **Python SDK** - Sync and async client libraries
- 🐋 **Docker ready** - 10-line Dockerfile for easy deployment

## Quick Start

### 1. Installation

```bash
git clone https://github.com/your-org/frog.git
cd frog
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Run the service

```bash
uvicorn app.main:app --reload
```

The service will start on `http://localhost:8000`

### 3. Test with curl

```bash
# Simple chat completion
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-frog_test" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Hello!"}]
  }'

# With workflow
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-frog_test" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Search for Python tutorials"}],
    "workflow": {
      "id": "search_workflow",
      "name": "Search Workflow",
      "nodes": [{
        "id": "search",
        "tool": {
          "type": "browser.search",
          "parameters": {"query": "Python tutorials"}
        },
        "depends_on": []
      }]
    }
  }'

# Auto-plan workflow
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Authorization: Bearer sk-frog_test" \
  -H "Content-Type: application/json" \
  -d '{
    "model": "gpt-3.5-turbo",
    "messages": [{"role": "user", "content": "Search for weather in NYC"}],
    "tools": ["browser.search"],
    "auto_plan": true
  }'
```

## Python SDK Usage

```python
from frog import FrogClient

# Initialize client
client = FrogClient(api_key="sk-frog_test")

# Simple chat
response = client.chat([
    {"role": "user", "content": "Hello!"}
])

# With workflow
workflow = {
    "id": "my_workflow",
    "name": "My Workflow", 
    "nodes": [{
        "id": "search",
        "tool": {
            "type": "browser.search",
            "parameters": {"query": "FastAPI tutorials"}
        },
        "depends_on": []
    }]
}

response = client.chat(
    messages=[{"role": "user", "content": "Find tutorials"}],
    workflow=workflow
)

# Async usage
import asyncio
from frog import AsyncFrogClient

async def main():
    client = AsyncFrogClient(api_key="sk-frog_test")
    response = await client.chat([
        {"role": "user", "content": "Hello async!"}
    ])
    print(response)

asyncio.run(main())
```

## Environment Variables

Create a `.env` file:

```bash
# API Configuration
FROG_API_KEY=sk-frog_dev_demo
PORT=8000

# External Services
OPENAI_KEY=sk-your_openai_key_here

# Security
VAULT_KEY=your_32_byte_base64_vault_key_here
```

Generate a vault key:
```bash
python -c "import base64, os; print(base64.urlsafe_b64encode(os.urandom(32)).decode())"
```

## Available Tools

- `browser.search` - Web search (mock implementation)
- `python.exec` - Python code execution (sandboxed mock)
- `http.request` - HTTP API requests

## Docker Deployment

```bash
# Build image
docker build -t frog:0.1 .

# Run container
docker run -p 8000:8000 -e OPENAI_KEY=your_key frog:0.1
```

## Testing

```bash
pytest tests/
```

## Architecture

```
frog/
├── app/                 # FastAPI micro-service
│   ├── main.py         # FastAPI app entry point
│   ├── api.py          # REST routes
│   ├── models.py       # Pydantic schemas
│   ├── engine.py       # Workflow DAG runner
│   ├── planner.py      # Auto-planning with LLM
│   ├── registry.py     # Tool adapters
│   ├── vault.py        # Secret encryption
│   └── config.py       # Environment settings
├── frog.py             # Python SDK
├── tests/              # Test suite
├── Dockerfile          # Container image
└── requirements.txt    # Dependencies
```

## Deployment Options

### Fly.io
```bash
fly launch
fly deploy
```

### Railway
```bash
railway login
railway init
railway up
```

### Render
Connect your GitHub repo and deploy with one click.

## Extension Hooks

- **Database**: Swap in-memory cache for PostgreSQL
- **Tools**: Add custom tool adapters in `registry.py`
- **Auth**: Enhance API key validation
- **Monitoring**: Add logging and metrics
- **SDK**: Publish to PyPI with `pyproject.toml`

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## License

MIT License - see LICENSE file for details.

---

Built with ❤️ for hackathons and rapid prototyping 🐸







{
  "model": "openai/gpt-4o-mini", // openrouter for the models
  "messages": [
    {"role": "user", "content": "hello world"}
  ],
  "tools": ["browser.search"],  // to implement: tool pool so people can use any tool
  "workflow_id": null,
  "workflow": null,
  "stream": true
}

