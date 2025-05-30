from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional, Literal, Union
from enum import Enum


class MessageRole(str, Enum):
    """Message role types."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Message(BaseModel):
    """Chat message following OpenAI format."""
    role: MessageRole
    content: str
    name: Optional[str] = None
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_call_id: Optional[str] = None


class ToolDefinition(BaseModel):
    """Tool definition for workflow nodes."""
    type: str = Field(..., description="Tool type (e.g., 'browser.search', 'python.exec')")
    parameters: Dict[str, Any] = Field(default_factory=dict, description="Tool-specific parameters")


class WorkflowNode(BaseModel):
    """Single node in a workflow DAG."""
    id: str = Field(..., description="Unique node identifier")
    tool: ToolDefinition
    depends_on: List[str] = Field(default_factory=list, description="Node IDs this depends on")
    condition: Optional[str] = Field(None, description="Optional condition for execution")


class Workflow(BaseModel):
    """Agent workflow definition as a DAG."""
    id: str = Field(..., description="Workflow identifier")
    name: str = Field(..., description="Human-readable workflow name")
    description: Optional[str] = Field(None, description="Workflow description")
    nodes: List[WorkflowNode] = Field(..., description="Workflow execution nodes")
    
    def validate_dag(self) -> bool:
        """Validate that workflow forms a valid DAG."""
        node_ids = {node.id for node in self.nodes}
        
        # Check all dependencies exist
        for node in self.nodes:
            for dep in node.depends_on:
                if dep not in node_ids:
                    return False
        
        # TODO: Add cycle detection for full DAG validation
        return True


class ChatRequest(BaseModel):
    """OpenAI-compatible chat completion request with frog extensions."""
    model: str = Field(default="openai/gpt-4o-mini", description="Model identifier")
    messages: List[Message] = Field(..., description="Conversation messages")
    stream: bool = Field(default=False, description="Enable streaming response")
    
    # Frog extensions
    tools: Optional[List[str]] = Field(None, description="Available tool names (MCP tools)")
    workflow_id: Optional[str] = Field(None, description="Workflow ID to use")
    workflow: Optional[Workflow] = Field(None, description="Full workflow definition (if null, uses base 'planner thinking model')")
    
    # Authentication context (populated from bearer token)
    account_id: Optional[str] = Field(None, description="Account ID extracted from bearer token")


class ChatChoice(BaseModel):
    """Single choice in chat completion response."""
    index: int
    message: Message
    finish_reason: Optional[Literal["stop", "length", "tool_calls", "content_filter"]] = None


class ChatUsage(BaseModel):
    """Token usage statistics."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int


class ChatResponse(BaseModel):
    """OpenAI-compatible chat completion response."""
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[ChatChoice]
    usage: Optional[ChatUsage] = None


class ChatStreamChunk(BaseModel):
    """Streaming response chunk."""
    id: str
    object: str = "chat.completion.chunk"
    created: int
    model: str
    choices: List[Dict[str, Any]]


class WorkflowContext(BaseModel):
    """Runtime context for workflow execution."""
    request_id: str
    account_id: Optional[str] = None
    secrets: Dict[str, str] = Field(default_factory=dict)
    variables: Dict[str, Any] = Field(default_factory=dict)
    execution_log: List[Dict[str, Any]] = Field(default_factory=list) 