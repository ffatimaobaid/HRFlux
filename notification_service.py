import os
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
import json

def get_groq_llm():
    from config import get_current_api_key
    try:
        return ChatGroq(
            model_name="llama-3.3-70b-versatile",
            temperature=0.8, # Higher temperature for more creative/fun responses
            groq_api_key=get_current_api_key()
        )
    except Exception as e:
        print(f"Error initializing Groq: {e}")
        return None

def generate_creative_notification(employee_name, pending_tasks):
    """
    Generate a fun, creative, and varied proactive notification for an employee
    encouraging them to complete their pending tasks.
    """
    if not pending_tasks:
        return "You have no pending tasks. Enjoy your day! 🎉"

    llm = get_groq_llm()
    if not llm:
        return f"Hey {employee_name}, don't forget you have {len(pending_tasks)} pending tasks!"

    # Format tasks for the prompt
    task_descriptions = []
    for t in pending_tasks:
        desc = f"- {t['title']}"
        if t.get('deadline'):
            desc += f" (Due: {t['deadline']})"
        task_descriptions.append(desc)
    
    task_list_str = "\n".join(task_descriptions)
    
    system_prompt = (
        "You are a fun, highly creative, and eccentric AI AI assistant for a corporate HR platform. "
        "Your job is to generate a short, engaging, and *proactive notification* to encourage an employee to tackle their tasks. "
        "Do NOT use typical corporate speak like 'Just a friendly reminder' or 'Please be advised'. "
        "Use humor, puns, pop culture references, or motivational metaphors. Keep it under 3 sentences. "
        "Make sure to mention their name occasionally. The notification should NOT be static or sound like a robot on loop. "
        "Only output the notification text, nothing else."
    )
    
    human_prompt = f"Employee Name: {employee_name}\nPending Tasks:\n{task_list_str}\n\nGenerate the notification:"
    
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=human_prompt)
    ]
    
    try:
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception as e:
        print(f"Error generating notification: {e}")
        return f"Hey {employee_name}, don't forget you have {len(pending_tasks)} pending tasks!"
