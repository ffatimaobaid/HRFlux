"""
Debug the tool selection issue.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def debug_tools():
    """Debug what tools are available and why the LLM isn't using them."""
    print("🔍 Debugging Tool Selection Issue")
    print("=" * 50)
    
    try:
        # Check docu_tools
        print("\n1. Checking docu_tools...")
        try:
            from docu_tools import docu_bot_tools
            print(f"✅ Tools available: {len(docu_bot_tools)}")
            for i, tool in enumerate(docu_bot_tools):
                print(f"   {i+1}. {tool.name}")
        except Exception as e:
            print(f"❌ Error importing docu_tools: {e}")
        
        # Check supervisor workflow
        print("\n2. Checking supervisor_workflow...")
        try:
            from supervisor_workflow import master_tools
            print(f"✅ Master tools: {len(master_tools)}")
            docu_tools = [tool for tool in master_tools if 'docu' in tool.name.lower()]
            print(f"📄 Document tools found: {len(docu_tools)}")
            for tool in docu_tools:
                print(f"   - {tool.name}")
        except Exception as e:
            print(f"❌ Error checking supervisor_workflow: {e}")
        
        # Test direct tool call
        print("\n3. Testing direct tool call...")
        try:
            from docu_tools import tool_generate_enhanced_document
            print("✅ tool_generate_enhanced_document imported successfully")
            print(f"📝 Tool name: {tool_generate_enhanced_document.name}")
            print(f"📝 Tool description: {tool_generate_enhanced_document.description[:100]}...")
        except Exception as e:
            print(f"❌ Error importing tool: {e}")
        
        print("\n🎯 Possible Issues:")
        print("1. LLM not recognizing the tool")
        print("2. Tool not properly registered")
        print("3. System prompt not clear enough")
        print("4. Tool selection logic issue")
        
        print("\n💡 Solutions to try:")
        print("1. Restart the chatbot app")
        print("2. Clear Streamlit cache")
        print("3. Check tool descriptions")
        print("4. Test with simpler prompt")
        
    except Exception as e:
        print(f"❌ Debug error: {e}")
    
    print("\n" + "=" * 50)
    print("🔍 Debug Complete!")

if __name__ == "__main__":
    debug_tools()
