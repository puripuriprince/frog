import json
import time
import uuid
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from app.models import ChatRequest, ChatResponse, ChatChoice, Message, MessageRole, Workflow, WorkflowNode, ToolDefinition
from app.engine import run_workflow
from app.planner import autoplan
from app.vault import inject_secrets
from app.config import settings
from app.openrouter import openrouter_client


router = APIRouter()


def verify_api_key(authorization: str = Header(None)) -> tuple[str, str]:
    """Verify API key from Authorization header and extract account ID."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # For MVP, accept any token that starts with sk-frog
    if not token.startswith("sk-frog"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    # Extract account ID from token format: sk-frog_{env}_{account_id}
    # Example: sk-frog_live_abc123 -> account_id = "abc123"
    parts = token.split("_")
    if len(parts) >= 3:
        account_id = "_".join(parts[2:])  # Handle account IDs with underscores
    else:
        account_id = "default"
    
    return token, account_id


def get_base_workflow() -> Workflow:
    """Get the base 'planner thinking model' workflow."""
    return Workflow(
        id="base_planner",
        name="Planner Thinking Model",
        description="Base workflow that uses planning and reasoning",
        nodes=[
            WorkflowNode(
                id="think",
                tool=ToolDefinition(
                    type="reasoning.think",
                    parameters={"approach": "step_by_step"}
                )
            ),
            WorkflowNode(
                id="plan",
                tool=ToolDefinition(
                    type="planning.create",
                    parameters={"strategy": "goal_oriented"}
                ),
                depends_on=["think"]
            ),
            WorkflowNode(
                id="execute",
                tool=ToolDefinition(
                    type="execution.run",
                    parameters={"follow_plan": True}
                ),
                depends_on=["plan"]
            )
        ]
    )


async def generate_openrouter_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Generate response using OpenRouter for any model."""
    try:
        # Convert frog messages to OpenRouter format
        openrouter_messages = []
        for msg in request.messages:
            openrouter_messages.append({
                "role": msg.role.value,
                "content": msg.content
            })
        
        # Use OpenRouter for the actual model inference
        if request.stream:
            async for chunk in openrouter_client.chat_completion(
                model=request.model,
                messages=openrouter_messages,
                stream=True
            ):
                yield chunk
        else:
            response = await openrouter_client.chat_completion(
                model=request.model,
                messages=openrouter_messages,
                stream=False
            )
            yield json.dumps(response)
            
    except Exception as e:
        # Fallback error response
        error_response = {
            "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
            "object": "chat.completion",
            "created": int(time.time()),
            "model": request.model,
            "choices": [{
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": f"Error: {str(e)}"
                },
                "finish_reason": "stop"
            }]
        }
        yield json.dumps(error_response)


async def generate_workflow_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Generate response using workflow execution with OpenRouter integration."""
    request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    
    workflow = request.workflow
    
    # If no workflow provided, use the base "planner thinking model"
    if workflow is None:
        workflow = get_base_workflow()
    
    # TODO: Handle workflow_id lookup from registry when provided
    if request.workflow_id and workflow is None:
        # In future: workflow = await get_workflow_by_id(request.workflow_id)
        # For now, fallback to base workflow
        workflow = get_base_workflow()
    
    # Create workflow context with secrets
    context = inject_secrets(workflow, request.account_id)
    
    # Add OpenRouter client to context for workflow tools to use
    context.variables["openrouter_client"] = openrouter_client
    context.variables["model"] = request.model
    
    if request.stream:
        # Stream workflow execution
        yield f"data: {json.dumps({'type': 'workflow_start', 'workflow_id': workflow.id})}\n\n"
        
        async for result_chunk in run_workflow(workflow, request.messages, context):
            # Convert workflow chunks to OpenAI format
            try:
                chunk_data = json.loads(result_chunk.strip())
                
                if chunk_data.get("type") == "message":
                    # Convert to OpenAI streaming format
                    openai_chunk = {
                        "id": request_id,
                        "object": "chat.completion.chunk",
                        "created": created,
                        "model": request.model,
                        "choices": [{
                            "index": 0,
                            "delta": {"content": chunk_data.get("content", "")},
                            "finish_reason": None
                        }]
                    }
                    yield f"data: {json.dumps(openai_chunk)}\n\n"
                else:
                    # Pass through other chunk types
                    yield f"data: {json.dumps(chunk_data)}\n\n"
                    
            except json.JSONDecodeError:
                continue
        
        # Final chunk
        final_chunk = {
            "id": request_id,
            "object": "chat.completion.chunk",
            "created": created,
            "model": request.model,
            "choices": [{
                "index": 0,
                "delta": {},
                "finish_reason": "stop"
            }]
        }
        yield f"data: {json.dumps(final_chunk)}\n\n"
        yield "data: [DONE]\n\n"
    
    else:
        # Non-streaming workflow execution
        content_parts = []
        async for result_chunk in run_workflow(workflow, request.messages, context):
            try:
                chunk_data = json.loads(result_chunk.strip())
                if chunk_data.get("type") == "message":
                    content_parts.append(chunk_data.get("content", ""))
            except json.JSONDecodeError:
                continue
        
        final_content = "\n".join(content_parts) or "Workflow completed"
        
        response = ChatResponse(
            id=request_id,
            created=created,
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=Message(role=MessageRole.ASSISTANT, content=final_content),
                    finish_reason="stop"
                )
            ]
        )
        yield json.dumps(response.dict())


@router.post("/v1/chat/completions")
async def chat_completions(
    request: ChatRequest,
    auth_info: tuple[str, str] = Depends(verify_api_key)
):
    """OpenAI-compatible chat completions endpoint with OpenRouter integration."""
    try:
        # Extract token and account_id from auth
        token, account_id = auth_info
        
        # Populate account_id in request for downstream processing
        request.account_id = account_id
        
        # Validate request
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages cannot be empty")
        
        # Determine response type based on frog-specific features
        has_frog_features = bool(request.workflow or request.workflow_id or request.tools)
        
        if has_frog_features:
            # Use workflow-based response for frog features
            response_generator = generate_workflow_response(request)
        else:
            # Use direct OpenRouter for simple model requests
            response_generator = generate_openrouter_response(request)
        
        # Return streaming or non-streaming response
        if request.stream:
            return StreamingResponse(
                response_generator,
                media_type="text/plain",
                headers={"Cache-Control": "no-cache"}
            )
        else:
            # For non-streaming, collect all chunks and return JSON
            chunks = []
            async for chunk in response_generator:
                chunks.append(chunk)
            
            response_text = "".join(chunks)
            try:
                response_data = json.loads(response_text)
                return response_data
            except json.JSONDecodeError:
                raise HTTPException(status_code=500, detail="Failed to generate response")
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.get("/v1/models")
async def list_models(auth_info: tuple[str, str] = Depends(verify_api_key)):
    """List available models from OpenRouter."""
    try:
        # Get models from OpenRouter
        models_response = await openrouter_client.list_models()
        return models_response
    except Exception as e:
        # Fallback to basic model list
        return {
            "object": "list",
            "data": [
                {
                    "id": "openai/gpt-4o",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "openai"
                },
                {
                    "id": "openai/gpt-4o-mini",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "openai"
                },
                {
                    "id": "anthropic/claude-3.5-sonnet",
                    "object": "model",
                    "created": int(time.time()),
                    "owned_by": "anthropic"
                }
            ]
        } 