import asyncio
import json
import time
from typing import List, Dict, Any, AsyncGenerator, Set
from app.models import Workflow, Message, WorkflowContext, ChatStreamChunk
from app.registry import get_tool_adapter
from app.vault import inject_secrets


def topological_sort(workflow: Workflow) -> List[str]:
    """Topologically sort workflow nodes for execution order."""
    # Build dependency graph
    graph = {node.id: node.depends_on for node in workflow.nodes}
    node_ids = set(graph.keys())
    
    # Kahn's algorithm for topological sorting
    in_degree = {node_id: 0 for node_id in node_ids}
    for deps in graph.values():
        for dep in deps:
            if dep in in_degree:
                in_degree[dep] += 1
    
    queue = [node_id for node_id, degree in in_degree.items() if degree == 0]
    result = []
    
    while queue:
        current = queue.pop(0)
        result.append(current)
        
        # Update in-degrees of dependent nodes
        for node_id, deps in graph.items():
            if current in deps:
                in_degree[node_id] -= 1
                if in_degree[node_id] == 0:
                    queue.append(node_id)
    
    if len(result) != len(node_ids):
        raise ValueError("Workflow contains cycles")
    
    return result


async def execute_node(
    node_id: str, 
    workflow: Workflow, 
    context: WorkflowContext,
    node_results: Dict[str, Any]
) -> Dict[str, Any]:
    """Execute a single workflow node."""
    # Find the node
    node = next((n for n in workflow.nodes if n.id == node_id), None)
    if not node:
        raise ValueError(f"Node {node_id} not found in workflow")
    
    # Check dependencies are satisfied
    for dep_id in node.depends_on:
        if dep_id not in node_results:
            raise ValueError(f"Dependency {dep_id} not satisfied for node {node_id}")
    
    # Prepare parameters with dependency results
    params = node.tool.parameters.copy()
    
    # Inject dependency results into parameters
    for dep_id in node.depends_on:
        dep_result = node_results[dep_id]
        # Simple variable substitution - can be enhanced
        params[f"dep_{dep_id}"] = dep_result
    
    # Get and execute tool adapter
    try:
        adapter = get_tool_adapter(node.tool.type)
        result = await adapter(params, context)
        
        context.execution_log.append({
            "node_id": node_id,
            "tool_type": node.tool.type,
            "status": "success",
            "timestamp": time.time()
        })
        
        return result
        
    except Exception as e:
        error_result = {"error": str(e), "node_id": node_id}
        
        context.execution_log.append({
            "node_id": node_id,
            "tool_type": node.tool.type,
            "status": "error",
            "error": str(e),
            "timestamp": time.time()
        })
        
        return error_result


async def run_workflow(
    workflow: Workflow,
    messages: List[Message],
    context: WorkflowContext
) -> AsyncGenerator[str, None]:
    """Execute workflow and yield streaming results."""
    try:
        # Validate workflow
        if not workflow.validate_dag():
            yield json.dumps({
                "error": "Invalid workflow DAG",
                "type": "workflow_error"
            }) + "\n"
            return
        
        # Get execution order
        execution_order = topological_sort(workflow)
        
        # Track node results
        node_results: Dict[str, Any] = {}
        
        # Yield workflow start
        yield json.dumps({
            "type": "workflow_start",
            "workflow_id": workflow.id,
            "nodes": len(workflow.nodes),
            "execution_order": execution_order
        }) + "\n"
        
        # Execute nodes in topological order
        for node_id in execution_order:
            # Yield node start
            yield json.dumps({
                "type": "node_start",
                "node_id": node_id
            }) + "\n"
            
            # Execute node
            try:
                result = await execute_node(node_id, workflow, context, node_results)
                node_results[node_id] = result
                
                # Yield node result
                yield json.dumps({
                    "type": "node_complete",
                    "node_id": node_id,
                    "result": result
                }) + "\n"
                
            except Exception as e:
                # Yield node error
                yield json.dumps({
                    "type": "node_error",
                    "node_id": node_id,
                    "error": str(e)
                }) + "\n"
                
                # Continue with other nodes if possible
                node_results[node_id] = {"error": str(e)}
        
        # Generate final response based on workflow results
        final_content = generate_workflow_summary(workflow, node_results, context)
        
        # Yield final message
        yield json.dumps({
            "type": "message",
            "content": final_content,
            "role": "assistant"
        }) + "\n"
        
        # Yield workflow complete
        yield json.dumps({
            "type": "workflow_complete",
            "execution_log": context.execution_log
        }) + "\n"
        
    except Exception as e:
        yield json.dumps({
            "type": "workflow_error",
            "error": str(e)
        }) + "\n"


def generate_workflow_summary(
    workflow: Workflow,
    node_results: Dict[str, Any],
    context: WorkflowContext
) -> str:
    """Generate a summary of workflow execution results."""
    summary_parts = [f"Workflow '{workflow.name}' completed:"]
    
    for node in workflow.nodes:
        result = node_results.get(node.id, {})
        if "error" in result:
            summary_parts.append(f"❌ {node.id}: {result['error']}")
        else:
            summary_parts.append(f"✅ {node.id}: Success")
    
    # Add execution stats
    total_nodes = len(workflow.nodes)
    successful_nodes = sum(1 for r in node_results.values() if "error" not in r)
    
    summary_parts.append(f"\nExecution Summary: {successful_nodes}/{total_nodes} nodes completed successfully")
    
    return "\n".join(summary_parts) 