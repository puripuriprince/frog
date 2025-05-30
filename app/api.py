import json
import time
import uuid
from typing import AsyncGenerator
from fastapi import APIRouter, HTTPException, Header, Depends
from fastapi.responses import StreamingResponse
from app.models import ChatRequest, ChatResponse, ChatChoice, Message, MessageRole
from app.engine import run_workflow
from app.planner import autoplan
from app.vault import inject_secrets
from app.config import settings


router = APIRouter()


def verify_api_key(authorization: str = Header(None)) -> str:
    """Verify API key from Authorization header."""
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Invalid Authorization format")
    
    token = authorization[7:]  # Remove "Bearer " prefix
    
    # For MVP, accept any token that starts with sk-frog
    if not token.startswith("sk-frog"):
        raise HTTPException(status_code=401, detail="Invalid API key")
    
    return token


async def generate_simple_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Generate a simple chat response without workflow."""
    request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    
    # Simple echo response for MVP
    last_message = request.messages[-1] if request.messages else None
    content = f"Echo: {last_message.content}" if last_message else "Hello! I'm frog 🐸"
    
    if request.stream:
        # Stream response chunks
        chunks = [
            {"type": "message_start"},
            {"type": "content", "content": content},
            {"type": "message_end"}
        ]
        
        for chunk in chunks:
            chunk_data = {
                "id": request_id,
                "object": "chat.completion.chunk",
                "created": created,
                "model": request.model,
                "choices": [{
                    "index": 0,
                    "delta": {"content": chunk.get("content", "")},
                    "finish_reason": "stop" if chunk["type"] == "message_end" else None
                }]
            }
            yield f"data: {json.dumps(chunk_data)}\n\n"
        
        yield "data: [DONE]\n\n"
    else:
        # Non-streaming response
        response = ChatResponse(
            id=request_id,
            created=created,
            model=request.model,
            choices=[
                ChatChoice(
                    index=0,
                    message=Message(role=MessageRole.ASSISTANT, content=content),
                    finish_reason="stop"
                )
            ]
        )
        yield json.dumps(response.dict())


async def generate_workflow_response(request: ChatRequest) -> AsyncGenerator[str, None]:
    """Generate response using workflow execution."""
    request_id = f"chatcmpl-{uuid.uuid4().hex[:8]}"
    created = int(time.time())
    
    workflow = request.workflow
    
    # Auto-plan workflow if requested
    if request.auto_plan and request.tools:
        planned_workflow = await autoplan(request.tools, request.messages)
        if planned_workflow:
            workflow = planned_workflow
    
    if not workflow:
        # Fallback to simple response
        async for chunk in generate_simple_response(request):
            yield chunk
        return
    
    # Create workflow context with secrets
    context = inject_secrets(workflow, request.account_id)
    
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
    api_key: str = Depends(verify_api_key)
):
    """OpenAI-compatible chat completions endpoint."""
    try:
        # Validate request
        if not request.messages:
            raise HTTPException(status_code=400, detail="Messages cannot be empty")
        
        # Choose response generator based on request
        if request.workflow or request.auto_plan:
            response_generator = generate_workflow_response(request)
        else:
            response_generator = generate_simple_response(request)
        
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
async def list_models(api_key: str = Depends(verify_api_key)):
    """List available models (OpenAI compatibility)."""
    return {
        "object": "list",
        "data": [
            {
                "id": "gpt-3.5-turbo",
                "object": "model",
                "created": int(time.time()),
                "owned_by": "frog"
            }
        ]
    } 