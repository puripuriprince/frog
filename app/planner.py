import httpx
import json
import os
import re
from typing import List, Optional
from dotenv import load_dotenv

from app.models import Message, Workflow, WorkflowNode, ToolDefinition
from app.registry import list_available_tools

# Load environment variables from .env file
load_dotenv()


def extract_json_from_response(content: str) -> str:
    """Extract JSON from response, handling markdown code blocks."""
    content = content.strip()
    
    # Check if content is wrapped in markdown code blocks
    if content.startswith('```'):
        # Remove markdown code block markers
        lines = content.split('\n')
        # Remove first line if it's ```json or ```
        if lines[0].startswith('```'):
            lines = lines[1:]
        # Remove last line if it's ```
        if lines and lines[-1].strip() == '```':
            lines = lines[:-1]
        content = '\n'.join(lines).strip()
    
    return content


async def autoplan(tools: List[str], messages: List[Message]) -> Optional[Workflow]:
    """Auto-generate workflow from tools and conversation context."""
    # Use OPENROUTER_API_KEY environment variable for OpenRouter
    openrouter_key = os.getenv("OPENROUTER_API_KEY")
    if not openrouter_key:
        return None
    
    # Get last user message for planning context
    user_messages = [msg for msg in messages if msg.role == "user"]
    if not user_messages:
        return None
    
    last_user_message = user_messages[-1].content
    
    # Build available tools description
    available_tools = list_available_tools()
    tools_desc = "\n".join([
        f"- {tool}: {desc}" 
        for tool, desc in available_tools.items() 
        if tool in tools
    ])
    
    # Create planning prompt
    planning_prompt = f"""
You are a workflow planner. Given a user request and available tools, create a simple workflow.

User Request: {last_user_message}

Available Tools:
{tools_desc}

Create a JSON workflow with this structure:
{{
  "id": "auto_workflow_1",
  "name": "Auto-generated workflow",
  "description": "Brief description",
  "nodes": [
    {{
      "id": "step1",
      "tool": {{
        "type": "tool_name",
        "parameters": {{"param": "value"}}
      }},
      "depends_on": []
    }}
  ]
}}

Rules:
1. Keep it simple - max 3 nodes
2. Use only the available tools
3. Create logical dependencies between nodes
4. Extract relevant parameters from the user request
5. Return ONLY the JSON, no explanation

Workflow:"""

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            response = await client.post(
                "https://openrouter.ai/api/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {openrouter_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "openai/gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are a helpful workflow planner. Return only valid JSON without markdown formatting."},
                        {"role": "user", "content": planning_prompt}
                    ],
                    "temperature": 0.3,
                    "max_tokens": 500
                }
            )
            
            if response.status_code != 200:
                return None
            
            result = response.json()
            content = result["choices"][0]["message"]["content"].strip()
            
            # Extract JSON from response (handle markdown code blocks)
            json_content = extract_json_from_response(content)
            
            # Parse the JSON workflow
            try:
                workflow_data = json.loads(json_content)
                workflow = Workflow(**workflow_data)
                
                # Validate the workflow uses only available tools
                for node in workflow.nodes:
                    if node.tool.type not in available_tools:
                        return None
                
                return workflow
                
            except (json.JSONDecodeError, ValueError):
                return None
                
    except Exception:
        return None 