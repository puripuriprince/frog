#!/usr/bin/env python3
"""
Comprehensive test suite for OpenRouter integration with frog schema.
Tests multiple models with various frog features.
"""
import asyncio
import json
import time
from typing import Dict, List, Any
from frog import FrogClient, AsyncFrogClient
from app.config import settings


class ComprehensiveTest:
    """Comprehensive test runner for frog + OpenRouter integration."""
    
    def __init__(self):
        self.client = FrogClient(api_key="sk-frog_live_comprehensive_test")
        self.async_client = AsyncFrogClient(api_key="sk-frog_live_comprehensive_test")
        self.results = {
            "passed": 0,
            "failed": 0,
            "tests": []
        }
        
        # Test models from different providers (updated with correct names)
        self.test_models = [
            "openai/gpt-4o",
            "openai/gpt-4o-mini", 
            "openai/gpt-3.5-turbo",
            "anthropic/claude-3.5-sonnet",
            "anthropic/claude-3-haiku",
            "meta-llama/llama-3.1-8b-instruct",
            "google/gemini-2.5-pro-preview",  # ← Fixed Gemini model name
            "deepseek/deepseek-r1-0528",      # ← Added DeepSeek model
            "mistralai/mistral-7b-instruct",
            "cohere/command-r-plus"
        ]
        
        # High-priority models for more intensive testing
        self.priority_models = [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.5-pro-preview",
            "deepseek/deepseek-r1-0528"
        ]
    
    def log_test(self, test_name: str, model: str, success: bool, response: str = "", error: str = ""):
        """Log test result."""
        result = {
            "test": test_name,
            "model": model,
            "success": success,
            "response": response[:100] + "..." if len(response) > 100 else response,
            "error": error,
            "timestamp": time.time()
        }
        self.results["tests"].append(result)
        
        if success:
            self.results["passed"] += 1
            print(f"✅ {test_name} | {model}: {response[:50]}...")
        else:
            self.results["failed"] += 1
            print(f"❌ {test_name} | {model}: {error}")
    
    def test_simple_requests(self):
        """Test simple requests (no frog features) with multiple models."""
        print("\n🔄 Testing Simple Requests (Direct OpenRouter)")
        print("=" * 60)
        
        for model in self.test_models:
            try:
                # Special test for DeepSeek reasoning model
                if "deepseek-r1" in model:
                    prompt = "Think step by step: What is 15 * 23?"
                else:
                    prompt = f"Say 'Hello from {model}' in a creative way"
                
                response = self.client.chat(
                    messages=[{"role": "user", "content": prompt}],
                    model=model,
                    stream=False
                )
                
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                self.log_test("Simple Request", model, True, content)
                
            except Exception as e:
                self.log_test("Simple Request", model, False, error=str(e))
    
    def test_reasoning_models(self):
        """Test reasoning capabilities of specific models."""
        print("\n🔄 Testing Reasoning Capabilities")
        print("=" * 60)
        
        reasoning_models = [
            "deepseek/deepseek-r1-0528",
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.5-pro-preview"
        ]
        
        reasoning_prompt = """
        Solve this step by step:
        A train leaves Station A at 2:00 PM traveling at 60 mph.
        Another train leaves Station B at 2:30 PM traveling at 80 mph toward Station A.
        The stations are 350 miles apart.
        At what time will the trains meet?
        """
        
        for model in reasoning_models:
            try:
                response = self.client.chat(
                    messages=[{"role": "user", "content": reasoning_prompt}],
                    model=model,
                    stream=False
                )
                
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                self.log_test("Reasoning Test", model, True, content)
                
            except Exception as e:
                self.log_test("Reasoning Test", model, False, error=str(e))
    
    def test_with_tools(self):
        """Test requests with tools (should use workflow)."""
        print("\n🔄 Testing With Tools (Workflow Mode)")
        print("=" * 60)
        
        # Test priority models for workflow features
        for model in self.priority_models:
            try:
                response = self.client.chat(
                    messages=[{"role": "user", "content": "Search for Python tutorials and summarize the top 3"}],
                    model=model,
                    tools=["browser.search", "text.summarize"],
                    stream=False
                )
                
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                self.log_test("Tools Request", model, True, content)
                
            except Exception as e:
                self.log_test("Tools Request", model, False, error=str(e))
    
    def test_with_workflow_id(self):
        """Test requests with workflow_id."""
        print("\n🔄 Testing With Workflow ID")
        print("=" * 60)
        
        workflow_models = [
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.5-pro-preview",
            "deepseek/deepseek-r1-0528"
        ]
        
        for model in workflow_models:
            try:
                response = self.client.chat(
                    messages=[{"role": "user", "content": "Analyze this data and provide insights"}],
                    model=model,
                    workflow_id="data_analysis",
                    stream=False
                )
                
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                self.log_test("Workflow ID", model, True, content)
                
            except Exception as e:
                self.log_test("Workflow ID", model, False, error=str(e))
    
    def test_with_custom_workflow(self):
        """Test requests with custom workflow definition."""
        print("\n🔄 Testing With Custom Workflow")
        print("=" * 60)
        
        custom_workflow = {
            "id": "test_workflow",
            "name": "Test Workflow",
            "description": "Custom workflow for testing",
            "nodes": [
                {
                    "id": "analyze",
                    "tool": {
                        "type": "analysis.deep",
                        "parameters": {"depth": "comprehensive"}
                    }
                },
                {
                    "id": "summarize",
                    "tool": {
                        "type": "text.summarize",
                        "parameters": {"length": "brief"}
                    },
                    "depends_on": ["analyze"]
                }
            ]
        }
        
        test_models = [
            "openai/gpt-4o", 
            "anthropic/claude-3.5-sonnet",
            "deepseek/deepseek-r1-0528"
        ]
        
        for model in test_models:
            try:
                response = self.client.chat(
                    messages=[{"role": "user", "content": "Process this complex data set"}],
                    model=model,
                    workflow=custom_workflow,
                    stream=False
                )
                
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                self.log_test("Custom Workflow", model, True, content)
                
            except Exception as e:
                self.log_test("Custom Workflow", model, False, error=str(e))
    
    async def test_streaming(self):
        """Test streaming responses with multiple models."""
        print("\n🔄 Testing Streaming Responses")
        print("=" * 60)
        
        streaming_models = [
            "openai/gpt-4o-mini",
            "anthropic/claude-3-haiku",
            "deepseek/deepseek-r1-0528",
            "google/gemini-2.5-pro-preview"
        ]
        
        for model in streaming_models:
            try:
                print(f"\n--- Streaming {model} ---")
                stream = await self.async_client.chat(
                    messages=[{"role": "user", "content": "Count from 1 to 5 with explanations"}],
                    model=model,
                    stream=True
                )
                
                content_parts = []
                async for chunk in stream:
                    if chunk.get('choices') and chunk['choices'][0].get('delta', {}).get('content'):
                        content = chunk['choices'][0]['delta']['content']
                        content_parts.append(content)
                        print(content, end='', flush=True)
                
                full_content = ''.join(content_parts)
                self.log_test("Streaming", model, True, full_content)
                print()  # New line after streaming
                
            except Exception as e:
                self.log_test("Streaming", model, False, error=str(e))
    
    def test_model_comparison(self):
        """Test same prompt across different models for comparison."""
        print("\n🔄 Testing Model Comparison")
        print("=" * 60)
        
        comparison_prompt = "Explain quantum computing in exactly 2 sentences."
        comparison_models = [
            "openai/gpt-4o",
            "anthropic/claude-3.5-sonnet", 
            "google/gemini-2.5-pro-preview",
            "deepseek/deepseek-r1-0528"
        ]
        
        for model in comparison_models:
            try:
                response = self.client.chat(
                    messages=[{"role": "user", "content": comparison_prompt}],
                    model=model,
                    stream=False
                )
                
                content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
                self.log_test("Model Comparison", model, True, content)
                
            except Exception as e:
                self.log_test("Model Comparison", model, False, error=str(e))
    
    def test_mixed_features(self):
        """Test combinations of frog features."""
        print("\n🔄 Testing Mixed Features")
        print("=" * 60)
        
        # Test tools + different models
        try:
            print("Testing tools + DeepSeek reasoning...")
            response = self.client.chat(
                messages=[{"role": "user", "content": "Research AI reasoning models and create a comparison"}],
                model="deepseek/deepseek-r1-0528",
                tools=["browser.search", "document.create"],
                stream=False
            )
            
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            self.log_test("Tools + DeepSeek", "deepseek/deepseek-r1-0528", True, content)
            
        except Exception as e:
            self.log_test("Tools + DeepSeek", "deepseek/deepseek-r1-0528", False, error=str(e))
        
        # Test Gemini with tools
        try:
            print("Testing tools + Gemini...")
            response = self.client.chat(
                messages=[{"role": "user", "content": "Analyze current tech trends"}],
                model="google/gemini-2.5-pro-preview",
                tools=["browser.search", "analysis.trend"],
                stream=False
            )
            
            content = response.get('choices', [{}])[0].get('message', {}).get('content', '')
            self.log_test("Tools + Gemini", "google/gemini-2.5-pro-preview", True, content)
            
        except Exception as e:
            self.log_test("Tools + Gemini", "google/gemini-2.5-pro-preview", False, error=str(e))
    
    def test_error_handling(self):
        """Test error handling with invalid models/requests."""
        print("\n🔄 Testing Error Handling")
        print("=" * 60)
        
        # Test invalid model
        try:
            response = self.client.chat(
                messages=[{"role": "user", "content": "Hello"}],
                model="invalid/model-name",
                stream=False
            )
            self.log_test("Invalid Model", "invalid/model-name", False, error="Should have failed but didn't")
        except Exception as e:
            self.log_test("Invalid Model", "invalid/model-name", True, response="Correctly failed: " + str(e)[:50])
        
        # Test empty messages
        try:
            response = self.client.chat(
                messages=[],
                model="openai/gpt-4o-mini",
                stream=False
            )
            self.log_test("Empty Messages", "openai/gpt-4o-mini", False, error="Should have failed but didn't")
        except Exception as e:
            self.log_test("Empty Messages", "openai/gpt-4o-mini", True, response="Correctly failed: " + str(e)[:50])
    
    def print_summary(self):
        """Print test summary."""
        print("\n" + "=" * 80)
        print("🐸 COMPREHENSIVE TEST SUMMARY")
        print("=" * 80)
        
        total_tests = self.results["passed"] + self.results["failed"]
        success_rate = (self.results["passed"] / total_tests * 100) if total_tests > 0 else 0
        
        print(f"Total Tests: {total_tests}")
        print(f"Passed: {self.results['passed']} ✅")
        print(f"Failed: {self.results['failed']} ❌")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Group results by test type
        test_types = {}
        for test in self.results["tests"]:
            test_type = test["test"]
            if test_type not in test_types:
                test_types[test_type] = {"passed": 0, "failed": 0}
            
            if test["success"]:
                test_types[test_type]["passed"] += 1
            else:
                test_types[test_type]["failed"] += 1
        
        print("\nResults by Test Type:")
        for test_type, counts in test_types.items():
            total = counts["passed"] + counts["failed"]
            rate = (counts["passed"] / total * 100) if total > 0 else 0
            print(f"  {test_type}: {counts['passed']}/{total} ({rate:.1f}%)")
        
        # Group results by model
        model_results = {}
        for test in self.results["tests"]:
            model = test["model"]
            if model not in model_results:
                model_results[model] = {"passed": 0, "failed": 0}
            
            if test["success"]:
                model_results[model]["passed"] += 1
            else:
                model_results[model]["failed"] += 1
        
        print("\nResults by Model:")
        for model, counts in sorted(model_results.items()):
            total = counts["passed"] + counts["failed"]
            rate = (counts["passed"] / total * 100) if total > 0 else 0
            print(f"  {model}: {counts['passed']}/{total} ({rate:.1f}%)")
        
        # Show failed tests
        failed_tests = [t for t in self.results["tests"] if not t["success"]]
        if failed_tests:
            print(f"\nFailed Tests ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  ❌ {test['test']} | {test['model']}: {test['error'][:60]}...")
    
    async def run_all_tests(self):
        """Run all tests."""
        print("🐸 Starting Comprehensive OpenRouter + Frog Tests")
        print("=" * 80)
        print(f"API Key configured: {'✅' if settings.openrouter_api_key else '❌'}")
        print(f"Testing {len(self.test_models)} models with frog schema")
        print(f"Priority models: {', '.join(self.priority_models)}")
        print()
        
        # Run tests in order
        self.test_simple_requests()
        self.test_reasoning_models()
        self.test_with_tools()
        self.test_with_workflow_id()
        self.test_with_custom_workflow()
        await self.test_streaming()
        self.test_model_comparison()
        self.test_mixed_features()
        self.test_error_handling()
        
        # Print summary
        self.print_summary()
        
        # Save results to file
        with open("test_results_comprehensive.json", "w") as f:
            json.dump(self.results, f, indent=2)
        print(f"\n📄 Detailed results saved to test_results_comprehensive.json")


async def main():
    """Run comprehensive tests."""
    tester = ComprehensiveTest()
    await tester.run_all_tests()


if __name__ == "__main__":
    asyncio.run(main())