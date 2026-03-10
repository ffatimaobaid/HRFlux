with open("gemini_llm.py", "r", encoding="utf-8") as f:
    text = f.read()
    
# Find the start of the function and remove it to the end or replace it
start_idx = text.find("def classify_and_extract_leave")
if start_idx != -1:
    text = text[:start_idx].strip() + "\n"
    
with open("gemini_llm.py", "w", encoding="utf-8") as f:
    f.write(text)
