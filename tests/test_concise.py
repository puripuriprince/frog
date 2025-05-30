#!/usr/bin/env python3
"""
Concise test for OpenRouter model availability and tools functionality.
"""
import asyncio
from frog import FrogClient


class ConciseTest:
    """Simple test for model availability and tools."""
    
    def __init__(self):
        self.client = FrogClient(api_key="sk-frog_live_test")
        self.results = {"available": [], "unavailable": [], "tools_work": False}
        
        # Test models
        self.models = [
            "openai/gpt-4o",
            "openai/gpt-4o-mini",
            "anthropic/claude-3.5-sonnet",
            "google/gemini-2.5-pro-preview",
            "deepseek/deepseek-r1-0528",
            "meta-llama/llama-3.1-8b-instruct",
            "mistralai/mistral-7b-instruct"
        ]
    
    def test_models(self):
        """Test if models are available."""
        print("🔄 Testing Model Availability...")
        
        for model in self.models:
            try:
                response = self.client.chat(
                    messages=[{"role": "user", "content": "Hi"}],
                    model=model,
                    stream=False
                )
                
                if response.get('choices'):
                    self.results["available"].append(model)
                    print(f"✅ {model}")
                else:
                    self.results["unavailable"].append(model)
                    print(f"❌ {model}")
                    
            except Exception as e:
                self.results["unavailable"].append(model)
                print(f"❌ {model}: {str(e)[:50]}...")
    
    def test_tools(self):
        """Test if tools functionality works."""
        print("\n🔄 Testing Tools...")
        
        try:
            response = self.client.chat(
                messages=[{"role": "user", "content": "Search for info"}],
                model="openai/gpt-4o-mini",
                tools=["browser.search"],
                stream=False
            )
            
            if response.get('choices'):
                self.results["tools_work"] = True
                print("✅ Tools work")
            else:
                print("❌ Tools failed")
                
        except Exception as e:
            print(f"❌ Tools failed: {str(e)[:50]}...")
    
    def print_summary(self):
        """Print concise summary."""
        total = len(self.models)
        available = len(self.results["available"])
        
        print(f"\n🐸 SUMMARY")
        print("=" * 30)
        print(f"Models: {available}/{total} available ({available/total*100:.0f}%)")
        print(f"Tools: {'✅' if self.results['tools_work'] else '❌'}")
        
        if self.results["unavailable"]:
            print(f"\nUnavailable: {', '.join(self.results['unavailable'])}")
    
    def run_tests(self):
        """Run all tests."""
        self.test_models()
        self.test_tools()
        self.print_summary()


if __name__ == "__main__":
    tester = ConciseTest()
    tester.run_tests()