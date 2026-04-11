import sys
import os

# Add the current directory to path
sys.path.append(os.getcwd())

try:
    print("Testing run_agent('tom.dev', 'hi')...")
    from agent import run_agent
    answer, suggestions = run_agent('tom.dev', 'hi')
    print(f"SUCCESS! Answer: {answer}")
except Exception as e:
    print(f"FAILED with exception: {type(e).__name__}: {e}")
    import traceback
    traceback.print_exc()
