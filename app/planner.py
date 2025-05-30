import httpx
import json
from typing import List, Optional
from app.models import Message, Workflow, WorkflowNode, ToolDefinition
from app.registry import list_available_tools
from app.config import settings


async def autoplan(tools: List[str], messages: List[Message]) -> Optional[Workflow]:
    """Auto-generate workflow from tools and conversation context."""
    if not settings.openai_key:
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
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.openai_key}",
                    "Content-Type": "application/json"
                },
                json={
                    "model": "gpt-3.5-turbo",
                    "messages": [
                        {"role": "system", "content": "You are a helpful workflow planner."},
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
            
            # Parse the JSON workflow
            try:
                workflow_data = json.loads(content)
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