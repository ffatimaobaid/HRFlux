import os
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import HumanMessage

# Use the current Gemini key from config
try:
    from config import get_current_gemini_key
    key = get_current_gemini_key()
except:
    key = os.getenv("GOOGLE_API_KEY")

llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash", google_api_key=key)
res = llm.invoke([HumanMessage(content="hi")])
print(f"Type: {type(res.content)}")
print(f"Content: {res.content}")
