import json
import logging
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from config import get_current_api_key
from db_schema_v2 import get_employee
from db import add_employee_task, get_employee_tasks, update_employee_task_status
from datetime import datetime, timedelta
from dateutil import parser as date_parser
import sqlite3

logger = logging.getLogger(__name__)

DB_PATH = "queries.db"

def add_employee_task_with_time(employee_id, title, description, deadline, event_type, start_time=None, end_time=None):
    """
    Add employee task with time support.
    """
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO employee_tasks 
            (employee_id, title, description, deadline, event_type, start_time, end_time)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (employee_id, title, description, deadline, event_type, start_time, end_time))
        conn.commit()
        return True
    except Exception as e:
        print(f"Error adding employee task: {e}")
        return False
    finally:
        conn.close()

def parse_meeting_date(date_str):
    """
    Parse various date formats for meeting scheduling.
    Handles 'tomorrow', 'next monday', '15 dec', etc.
    """
    try:
        if not date_str:
            return None
        
        # Handle common relative terms
        date_str = date_str.lower().strip()
        today = datetime.now()
        
        if date_str == "tomorrow":
            return (today + timedelta(days=1)).strftime("%Y-%m-%d")
        elif date_str == "today":
            return today.strftime("%Y-%m-%d")
        elif "next monday" in date_str:
            days_ahead = (0 - today.weekday()) % 7
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        elif "next tuesday" in date_str:
            days_ahead = (1 - today.weekday()) % 7
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        elif "next wednesday" in date_str:
            days_ahead = (2 - today.weekday()) % 7
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        elif "next thursday" in date_str:
            days_ahead = (3 - today.weekday()) % 7
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        elif "next friday" in date_str:
            days_ahead = (4 - today.weekday()) % 7
            if days_ahead <= 0:
                days_ahead += 7
            return (today + timedelta(days=days_ahead)).strftime("%Y-%m-%d")
        
        # Use dateutil for other formats
        dt = date_parser.parse(date_str, fuzzy=True)
        if dt.year == 1900:
            dt = dt.replace(year=today.year)
        
        return dt.strftime("%Y-%m-%d")
    except Exception as e:
        logger.warning(f"Date parsing failed for '{date_str}': {e}")
        return None

def parse_meeting_time(time_str):
    """
    Parse various time formats for meeting scheduling.
    Handles '2:00 PM', '14:00', '2pm', etc.
    """
    try:
        if not time_str:
            return None, None
        
        time_str = time_str.strip().lower()
        
        # Handle common formats
        if 'am' in time_str or 'pm' in time_str:
            # Parse 12-hour format
            if ':' in time_str:
                time_part = time_str.replace('am', '').replace('pm', '').strip()
                hour_min = time_part.split(':')
                hour = int(hour_min[0])
                minute = int(hour_min[1]) if len(hour_min) > 1 else 0
            else:
                # Simple format like "2pm"
                hour = int(time_str.replace('am', '').replace('pm', '').strip())
                minute = 0
            
            if 'pm' in time_str and hour != 12:
                hour += 12
            elif 'am' in time_str and hour == 12:
                hour = 0
        else:
            # Parse 24-hour format
            if ':' in time_str:
                hour_min = time_str.split(':')
                hour = int(hour_min[0])
                minute = int(hour_min[1]) if len(hour_min) > 1 else 0
            else:
                hour = int(time_str)
                minute = 0
        
        # Default 1-hour meeting duration
        end_hour = hour + 1
        if end_hour >= 24:
            end_hour -= 1  # Keep it within same day
        
        start_time = f"{hour:02d}:{minute:02d}"
        end_time = f"{end_hour:02d}:{minute:02d}"
        
        return start_time, end_time
        
    except Exception as e:
        logger.warning(f"Time parsing failed for '{time_str}': {e}")
        return None, None

def check_time_conflicts(employee_id, date, start_time, end_time, exclude_task_id=None):
    """
    Check if there are any scheduling conflicts for the given time slot.
    """
    try:
        all_tasks = get_employee_tasks(employee_id)
        
        for task in all_tasks:
            # Skip the task being checked (for updates)
            if exclude_task_id and task['id'] == exclude_task_id:
                continue
                
            # Only check pending tasks that have a time
            if (task['status'] == 'pending' and 
                task['deadline'] == date and 
                task.get('start_time')):
                
                task_start = task['start_time']
                task_end = task.get('end_time', task_start)
                
                # Check for time overlap
                if ((start_time >= task_start and start_time < task_end) or
                    (end_time > task_start and end_time <= task_end) or
                    (start_time <= task_start and end_time >= task_end)):
                    return task
        
        return None
    except Exception as e:
        logger.error(f"Error checking conflicts: {e}")
        return None

@tool
def tool_schedule_meeting(username: str, event_title: str = "", event_type: str = "", event_date: str = "", 
                         start_time: str = "", end_time: str = "", participants: str = "", 
                         description: str = "") -> str:
    """
    Schedule a meeting or event for an employee. This tool should be used step by step:
    
    STEP 1: Call with just the username to check if scheduling is available
    STEP 2: Ask the user for event title, type, date, time, participants, and description
    STEP 3: Call again with all details to actually schedule the event
    
    Args:
        username: The username of the employee scheduling the event
        event_title: Title of the event (required for actual scheduling)
        event_type: Type of event (required for actual scheduling: 'meeting', 'task', 'deadline', 'event')
        event_date: Date of the event (required for actual scheduling, e.g., "tomorrow", "2024-12-15", "next monday")
        start_time: Start time (e.g., "2:00 PM", "14:00")
        end_time: End time (optional, defaults to 1 hour after start)
        participants: List of participants (optional, comma-separated names)
        description: Event description/agenda (optional)
        
    Returns:
        JSON string with status and event details or prompts for missing information
    """
    try:
        # Get employee info
        employee = get_employee(username=username)
        if not employee:
            return json.dumps({
                "status": "error",
                "message": f"Employee '{username}' not found in the system."
            })
        
        # If only username provided, return guidance on what's needed
        if not event_title or not event_type or not event_date:
            return json.dumps({
                "status": "info",
                "message": "To schedule an event, I need the following details:",
                "required_fields": {
                    "event_title": "What is the event title? (e.g., 'Project Review', 'Team Standup', 'Client Meeting')",
                    "event_type": "What type of event? (choose one: 'meeting', 'task', 'deadline', 'event')",
                    "event_date": "When should the event be scheduled? (e.g., 'tomorrow', 'next monday', '2024-12-15')",
                    "start_time": "What time does it start? (e.g., '2:00 PM', '14:00')",
                    "end_time": "What time does it end? (optional, defaults to 1 hour duration)",
                    "participants": "Who should attend? (optional, comma-separated names)",
                    "description": "What's the agenda/details? (optional)"
                },
                "example": "Please provide: 'Schedule a meeting titled 'Project Review' for tomorrow at 2:00 PM with John and Sarah to discuss Q4 targets'"
            })
        
        # Validate event type
        valid_types = ['meeting', 'task', 'deadline', 'event']
        if event_type not in valid_types:
            return json.dumps({
                "status": "error",
                "message": f"Invalid event type '{event_type}'. Please choose from: {', '.join(valid_types)}"
            })
        
        # Parse the event date
        parsed_date = parse_meeting_date(event_date)
        if not parsed_date:
            return json.dumps({
                "status": "error", 
                "message": f"Could not understand the date '{event_date}'. Please use a format like 'tomorrow', 'next monday', or '2024-12-15'."
            })
        
        # Parse times
        parsed_start_time, parsed_end_time = parse_meeting_time(start_time)
        if not parsed_start_time:
            return json.dumps({
                "status": "error",
                "message": f"Could not understand the time '{start_time}'. Please use a format like '2:00 PM' or '14:00'."
            })
        
        # Use provided end_time or calculated default
        if end_time:
            _, parsed_end_time = parse_meeting_time(end_time)
        
        # Check for scheduling conflicts
        conflict = check_time_conflicts(employee['employee_id'], parsed_date, parsed_start_time, parsed_end_time)
        if conflict:
            return json.dumps({
                "status": "conflict",
                "message": f"⚠️ Scheduling conflict detected! There's already a '{conflict['title']}' scheduled on {parsed_date} from {conflict.get('start_time', 'all day')}.",
                "conflicting_event": conflict,
                "suggestions": [
                    "Choose a different time slot",
                    "Choose a different date",
                    f"Reschedule the existing '{conflict['title']}' event"
                ]
            })
        
        # Create event description with all details
        full_description = f"{event_type.title()}: {event_title}\n"
        if parsed_start_time:
            full_description += f"Time: {parsed_start_time} - {parsed_end_time}\n"
        if participants:
            full_description += f"Participants: {participants}\n"
        if description:
            full_description += f"Details: {description}\n"
        
        # Add to employee tasks
        success = add_employee_task_with_time(
            employee_id=employee['employee_id'],
            title=event_title,
            description=full_description,
            deadline=parsed_date,
            event_type=event_type,
            start_time=parsed_start_time,
            end_time=parsed_end_time
        )
        
        if success:
            return json.dumps({
                "status": "success",
                "message": f"✅ {event_type.title()} '{event_title}' scheduled successfully for {parsed_date} from {parsed_start_time} to {parsed_end_time}",
                "event_details": {
                    "title": event_title,
                    "type": event_type,
                    "date": parsed_date,
                    "start_time": parsed_start_time,
                    "end_time": parsed_end_time,
                    "participants": participants,
                    "description": description
                },
                "notification": "The event will appear in your calendar and notifications."
            })
        else:
            return json.dumps({
                "status": "error",
                "message": "Failed to schedule event due to a database error."
            })
            
    except Exception as e:
        logger.error(f"Failed to schedule event: {e}")
        return json.dumps({"error": str(e)})

@tool
def tool_list_meetings(username: str, start_date: str = "", end_date: str = "") -> str:
    """
    List scheduled meetings for an employee.
    
    Args:
        username: The username of the employee
        start_date: Start date filter (optional)
        end_date: End date filter (optional)
        
    Returns:
        JSON string with list of meetings
    """
    try:
        employee = get_employee(username=username)
        if not employee:
            return json.dumps({
                "status": "error",
                "message": f"Employee '{username}' not found in the system."
            })
        
        # Get all tasks and filter for meetings
        all_tasks = get_employee_tasks(employee['employee_id'])
        meetings = [task for task in all_tasks if task['event_type'] == 'meeting']
        
        # Filter by date range if provided
        if start_date:
            meetings = [m for m in meetings if m['deadline'] >= start_date]
        if end_date:
            meetings = [m for m in meetings if m['deadline'] <= end_date]
        
        # Sort by date
        meetings.sort(key=lambda x: x['deadline'])
        
        return json.dumps({
            "status": "success",
            "meetings": meetings
        })
        
    except Exception as e:
        logger.error(f"Failed to list meetings: {e}")
        return json.dumps({"error": str(e)})

@tool
def tool_cancel_meeting(username: str, meeting_title: str, meeting_date: str = "") -> str:
    """
    Cancel a scheduled meeting.
    
    Args:
        username: The username of the employee
        meeting_title: Title of the meeting to cancel
        meeting_date: Date of the meeting (optional, helps identify specific meeting)
        
    Returns:
        JSON string with status
    """
    try:
        employee = get_employee(username=username)
        if not employee:
            return json.dumps({
                "status": "error",
                "message": f"Employee '{username}' not found in the system."
            })
        
        # Get meetings and find the one to cancel
        all_tasks = get_employee_tasks(employee['employee_id'])
        meetings = [task for task in all_tasks if task['event_type'] == 'meeting' and task['status'] == 'pending']
        
        # Find matching meeting
        target_meeting = None
        for meeting in meetings:
            if meeting_title.lower() in meeting['title'].lower():
                if not meeting_date or meeting['deadline'] == meeting_date:
                    target_meeting = meeting
                    break
        
        if not target_meeting:
            return json.dumps({
                "status": "error",
                "message": f"Could not find a meeting matching '{meeting_title}'. Please check the title and date."
            })
        
        # Cancel the meeting
        success = update_employee_task_status(target_meeting['id'], 'cancelled')
        
        if success:
            return json.dumps({
                "status": "success",
                "message": f"Meeting '{target_meeting['title']}' on {target_meeting['deadline']} has been cancelled."
            })
        else:
            return json.dumps({
                "status": "error",
                "message": "Failed to cancel meeting due to a database error."
            })
            
    except Exception as e:
        logger.error(f"Failed to cancel meeting: {e}")
        return json.dumps({"error": str(e)})

meeting_bot_tools = [tool_schedule_meeting, tool_list_meetings, tool_cancel_meeting]
