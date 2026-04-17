from gemini_llm import classify_and_extract_leave
import sys

# Force UTF-8 for Windows console (best effort)
try:
    sys.stdout.reconfigure(encoding='utf-8')
except:
    pass

def debug_intent():
    question = "I want to apply for casual leave from 2025-12-20 to 2025-12-22 because I am sick"
    print(f"Testing intent extraction for: {question}")
    
    try:
        result = classify_and_extract_leave(question)
        print("Result:")
        print(result)
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    debug_intent()
