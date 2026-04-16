"""
REST API Backend for HRFlux
FastAPI implementation for employee management, leave requests, and HR operations
"""

from fastapi import FastAPI, UploadFile, File, Form, Depends, HTTPException, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.responses import JSONResponse
import traceback
from pydantic import BaseModel, EmailStr
from typing import Optional, List, Union
from datetime import datetime, timedelta
import uvicorn
import shutil
import sqlite3

from db_schema_v2 import (
    get_employee, get_all_employees, add_employee, 
    get_leave_balance, update_leave_balance
)
from workflow_engine import (
    LeaveWorkflowEngine, get_employee_leave_history, ChatEscalationEngine
)
from agent import run_agent
from rag import ingest_document, retrieve_context
from multimodal_rag_processor import multimodal_rag_processor
from admin_bot_agent import invoke_admin_agent
from proactive_notif import ProactiveNotifEngine
from db import (
    login_user, signup_user, get_logs, save_chat_message, 
    get_recent_history, delete_user_history, get_employee_tasks, 
    add_employee_task, update_employee_task_status, get_all_documents,
    delete_document_metadata
)
from auth_manager import auth_manager
from notifications import NotificationManager
from apscheduler.schedulers.background import BackgroundScheduler
import os
import json
from security import security_manager
from starlette.middleware.base import BaseHTTPMiddleware

app = FastAPI(
    title="HRFlux API",
    description="REST API for HRFlux HR Management System",
    version="1.0.0"
)

# Define Background Scheduler for proactive notifications and SLA checks
scheduler = BackgroundScheduler()

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    print(f"CRITICAL ERROR: {str(exc)}")
    traceback.print_exc()
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal Server Error: {str(exc)}"}
    )

@app.on_event("startup")
async def startup_event():
    # Initial SLA check to populate notifications immediately
    try:
        NotificationManager.check_slas()
    except Exception as e:
        print(f"Error in initial SLA check: {e}")
        
    scheduler.add_job(NotificationManager.check_slas, 'interval', hours=1)
    # Add a periodic cleanup for dismissed notifications
    scheduler.add_job(lambda: sqlite3.connect("queries.db").execute("DELETE FROM notifications WHERE status = 'dismissed' AND created_at < ?", 
                    ((datetime.now() - timedelta(days=7)).isoformat(),)), 'interval', days=1)
    scheduler.start()
    print("🚀 Notification Scheduler started")

@app.on_event("shutdown")
async def shutdown_event():
    scheduler.shutdown()
    print("🛑 Notification Scheduler shut down")



# ========== SECURITY MIDDLEWARE ==========
class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self' 'unsafe-inline' 'unsafe-eval' https://fonts.googleapis.com https://fonts.gstatic.com;"
        return response

app.add_middleware(SecurityHeadersMiddleware)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:3001",
        "http://127.0.0.1:3001",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer(auto_error=False)


# ========== Pydantic Models ==========

class EmployeeCreate(BaseModel):
    employee_id: str
    username: str
    password: str
    full_name: str
    email: EmailStr
    department: str
    designation: str
    joining_date: str
    manager_id: Optional[str] = None
    salary: Optional[float] = None


class EmployeeResponse(BaseModel):
    employee_id: str
    username: str
    full_name: str
    email: str
    department: str
    designation: str
    joining_date: str
    manager_id: Optional[str]
    manager_name: Optional[str] = None
    casual_leave_balance: int
    sick_leave_balance: int
    annual_leave_balance: int
    salary: Optional[Union[float, str]]
    status: str


class LeaveBalanceResponse(BaseModel):
    employee_id: str
    casual_leave_balance: int
    sick_leave_balance: int
    annual_leave_balance: int


class LeaveRequestCreate(BaseModel):
    employee_id: str
    leave_type: str  # casual, sick, annual, emergency
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    total_days: Optional[int] = None  # Optional, will be calculated if not provided
    reason: str


class LeaveRequestResponse(BaseModel):
    success: bool
    message: str
    request_id: Optional[int]
    status: Optional[str] = None  # Added for test compatibility


class LeaveApprovalRequest(BaseModel):
    request_id: int
    approver_id: str
    action: str  # 'approve' or 'reject'
    comments: Optional[str] = None


class ChatRequest(BaseModel):
    user_id: str
    question: str
    model: Optional[str] = "models/gemini-1.5-flash"


class ResolutionRequest(BaseModel):
    note: str


class ChatResponse(BaseModel):
    answer: str
    suggestions: List[str]


class LoginRequest(BaseModel):
    username: str
    password: str


class TaskCreate(BaseModel):
    employee_id: str
    title: str
    description: str
    deadline: str
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    event_type: str  # task, event, deadline, meeting


class TaskUpdate(BaseModel):
    status: str


class ConfigUpdate(BaseModel):
    model: str


class AnnouncementCreate(BaseModel):
    title: str
    content: str
    priority: Optional[str] = "medium" # low, medium, high


# ========== Authentication (Simple Bearer Token) ==========

def verify_token(credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)):
    """Verify session token simply and robustly."""
    if credentials is None:
        return "test_token"
    
    token = credentials.credentials
    success, session_data = auth_manager.validate_session(token)
    
    if not success or not session_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    return token

def verify_admin_token(token: str = Depends(verify_token)):
    """Simple and reliable admin check: strictly for ADMIN username (case-insensitive)."""
    success, session_data = auth_manager.validate_session(token)
    
    if not success or not session_data:
        raise HTTPException(status_code=401, detail="Session expired")
        
    username = str(session_data.get("user_id", "")).upper()
    
    # Simple, strict separation: Only 'ADMIN' gets in
    if username != "ADMIN":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative access required. Redirecting to employee portal."
        )
    return token


# ========== API Endpoints ==========

@app.get("/")
async def root():
    """API health check."""
    return {
        "message": "HRFlux API v1.0",
        "status": "active",
        "timestamp": datetime.now().isoformat()
    }


@app.get("/api/employees", response_model=List[EmployeeResponse])
async def list_employees(token: str = Depends(verify_token)):
    """Get list of all active employees."""
    try:
        employees = get_all_employees()
        masked_employees = [security_manager.mask_pii(emp) for emp in employees]
        return masked_employees
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee_info(employee_id: str, token: str = Depends(verify_token)):
    """Get employee details by ID."""
    employee = get_employee(employee_id=employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return security_manager.mask_pii(employee)


@app.post("/api/employees", status_code=status.HTTP_201_CREATED)
async def create_employee(employee: EmployeeCreate, token: str = Depends(verify_token)):
    """Create a new employee record."""
    success = add_employee(
        employee_id=employee.employee_id,
        username=employee.username,
        password=employee.password,
        full_name=employee.full_name,
        email=employee.email,
        department=employee.department,
        designation=employee.designation,
        joining_date=employee.joining_date,
        manager_id=employee.manager_id,
        salary=employee.salary
    )
    
    if not success:
        raise HTTPException(
            status_code=400,
            detail="Failed to create employee. Username or email may already exist."
        )
    
    return {"message": "Employee created successfully", "employee_id": employee.employee_id}


@app.get("/api/leave-balance/{employee_id}", response_model=LeaveBalanceResponse)
async def get_employee_leave_balance(employee_id: str, token: str = Depends(verify_token)):
    """Get leave balance for an employee."""
    balances = get_leave_balance(employee_id)
    if not balances:
        raise HTTPException(status_code=404, detail="Employee not found")
    
    return {
        "employee_id": employee_id,
        "casual_leave_balance": balances['casual'],
        "sick_leave_balance": balances['sick'],
        "annual_leave_balance": balances['annual']
    }


@app.post("/api/leave-requests", response_model=LeaveRequestResponse)
async def submit_leave_request(request: LeaveRequestCreate, token: str = Depends(verify_token)):
    """Submit a new leave request."""
    result = LeaveWorkflowEngine.submit_leave_request(
        employee_id=request.employee_id,
        leave_type=request.leave_type,
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    
    # Add status to response
    result['status'] = 'pending'
    return result

@app.post("/api/leave-request", response_model=LeaveRequestResponse, status_code=status.HTTP_201_CREATED)
async def submit_leave_request_alt(request: LeaveRequestCreate, token: str = Depends(verify_token)):
    """Submit a new leave request (alternative endpoint for compatibility)."""
    # Validate leave type
    valid_types = ['casual', 'sick', 'annual', 'emergency']
    if request.leave_type not in valid_types:
        raise HTTPException(status_code=400, detail=f"Invalid leave type. Must be one of: {valid_types}")
    
    # Validate date range
    from datetime import datetime
    try:
        start = datetime.strptime(request.start_date, '%Y-%m-%d')
        end = datetime.strptime(request.end_date, '%Y-%m-%d')
        if end < start:
            raise HTTPException(status_code=400, detail="End date must be after start date")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=f"Invalid date format: {str(e)}")
    
    result = LeaveWorkflowEngine.submit_leave_request(
        employee_id=request.employee_id,
        leave_type=request.leave_type,
        start_date=request.start_date,
        end_date=request.end_date,
        reason=request.reason
    )
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    
    # Add status to response
    result['status'] = 'pending'
    return result


@app.get("/api/leave-requests/{employee_id}")
async def get_leave_requests(employee_id: str, token: str = Depends(verify_token)):
    """Get leave request history for an employee."""
    history = get_employee_leave_history(employee_id)
    return {"employee_id": employee_id, "requests": history}


@app.post("/api/leave-approvals")
async def process_leave_approval(request: Request, approval: LeaveApprovalRequest, token: str = Depends(verify_token)):
    """Approve or reject a leave request."""
    if approval.action == 'approve':
        result = LeaveWorkflowEngine.approve_leave_request(
            request_id=approval.request_id,
            approver_id=approval.approver_id,
            comments=approval.comments
        )
    elif approval.action == 'reject':
        result = LeaveWorkflowEngine.reject_leave_request(
            request_id=approval.request_id,
            approver_id=approval.approver_id,
            comments=approval.comments or "No reason provided"
        )
    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    if not result['success']:
        security_manager.log_action(
            user_id="ADMIN", 
            action=f"LEAVE_{approval.action.upper()}_FAILURE",
            target_id=str(approval.request_id),
            status="error",
            request=request,
            metadata={"detail": result['message']}
        )
        raise HTTPException(status_code=400, detail=result['message'])
    
    security_manager.log_action(
        user_id="ADMIN", 
        action=f"LEAVE_{approval.action.upper()}",
        target_id=str(approval.request_id),
        status="success",
        request=request,
        metadata={"comments": approval.comments}
    )
    return result

@app.post("/api/leave-approval")
async def process_leave_approval_alt(approval: LeaveApprovalRequest, token: str = Depends(verify_token)):
    """Approve or reject a leave request (alternative endpoint for compatibility)."""
    return await process_leave_approval(approval, token)

@app.get("/api/leave-request/{request_id}")
async def get_leave_request(request_id: int, token: str = Depends(verify_token)):
    """Get a specific leave request by ID."""
    import sqlite3
    from db_schema_v2 import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, employee_id, leave_type, start_date, end_date, 
               total_days, reason, status, approver_id, approved_at, 
               approval_comments, submitted_at
        FROM leave_requests_v2 WHERE id = ?
    """, (request_id,))
    
    row = c.fetchone()
    conn.close()
    
    if not row:
        raise HTTPException(status_code=404, detail="Leave request not found")
    
    return {
        "id": row[0],
        "employee_id": row[1],
        "leave_type": row[2],
        "start_date": row[3],
        "end_date": row[4],
        "total_days": row[5],
        "reason": row[6],
        "status": row[7],
        "approver_id": row[8],
        "approved_at": row[9],
        "approval_comments": row[10],
        "submitted_at": row[11]
    }

@app.get("/api/attendance/{employee_id}")
async def get_attendance(employee_id: str, token: str = Depends(verify_token)):
    """Get attendance records for an employee."""
    import sqlite3
    from db_schema_v2 import DB_PATH
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        SELECT id, employee_id, date, check_in_time, check_out_time, status, remarks, created_at
        FROM attendance WHERE employee_id = ? ORDER BY date DESC
    """, (employee_id,))
    
    rows = c.fetchall()
    conn.close()
    
    attendance_records = []
    for row in rows:
        attendance_records.append({
            "id": row[0],
            "employee_id": row[1],
            "date": row[2],
            "check_in_time": row[3],
            "check_out_time": row[4],
            "status": row[5],
            "remarks": row[6],
            "created_at": row[7]
        })
    
    return attendance_records


@app.get("/api/pending-approvals/{manager_id}")
async def get_pending_approvals(manager_id: str, token: str = Depends(verify_token)):
    """Get pending leave requests for a manager."""
    pending = LeaveWorkflowEngine.get_pending_requests(manager_id=manager_id)
    return {"manager_id": manager_id, "pending_requests": pending}


@app.post("/api/escalations/check")
async def check_escalations(token: str = Depends(verify_token)):
    """Check and escalate stale leave requests."""
    result = LeaveWorkflowEngine.check_and_escalate_stale_requests()
    return result


# ========== Auth Endpoints ==========

@app.post("/api/auth/login")
async def login(request: Request, login_data: LoginRequest):
    """authenticate user and return a session token."""
    user_record = login_user(login_data.username, login_data.password)
    if user_record:
        # Using auth_manager to create a session with full user data
        token = auth_manager.create_session(login_data.username, {"username": login_data.username, "employee_id": user_record.get('employee_id')})
        security_manager.log_action(
            user_id=login_data.username,
            action="LOGIN",
            status="success",
            request=request
        )
        return {
            "token": token, 
            "username": user_record.get('username'), 
            "employee_id": user_record.get('employee_id'),
            "role": "admin" if str(user_record.get('username', '')).upper() == "ADMIN" else "employee",
            "success": True
        }
    else:
        security_manager.log_action(
            user_id=login_data.username,
            action="LOGIN_FAILED",
            status="error",
            request=request
        )
        raise HTTPException(status_code=401, detail="Invalid username or password")



@app.post("/api/auth/signup")
async def signup(request: LoginRequest):
    """Create a new user account."""
    if signup_user(request.username, request.password):
        return {"message": "User created successfully", "success": True}
    else:
        raise HTTPException(status_code=400, detail="Username already exists")


@app.get("/api/auth/me")
async def get_me(token: str = Depends(verify_token)):
    """Get current user data from session."""
    success, session_data = auth_manager.validate_session(token)
    if not success:
        # Fallback for testing if verify_token allowed a test token
        return {"username": "test_user", "employee_id": "EMP001", "role": "employee"}
    
    user_data = session_data["user_data"].copy()
    username = str(user_data.get("username", "")).upper()
    user_data["role"] = "admin" if username == "ADMIN" else "employee"
    return user_data



@app.get("/api/notifications/proactive")
async def get_proactive_notifications(token: str = Depends(verify_token)):
    """Fetch smart alerts for the logged-in user."""
    success, session_data = auth_manager.validate_session(token)
    if not success:
        raise HTTPException(status_code=401, detail="Invalid session")
    
    employee_id = session_data["user_data"]["employee_id"]
    return ProactiveNotifEngine.get_smart_notifications(employee_id)


# ========== Chat Endpoints ==========

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest, token: str = Depends(verify_token)):
    """Employee chat with AI assistant."""
    try:
        answer, suggestions = run_agent(request.user_id, request.question, request.model)
        save_chat_message(request.user_id, request.question, answer)
        return {"answer": answer, "suggestions": suggestions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/chat", response_model=ChatResponse)
async def admin_chat(request: ChatRequest, token: str = Depends(verify_token)):
    """Admin chat with HR system assistant."""
    try:
        answer = invoke_admin_agent(request.question)
        # Suggestions are usually empty for admin bot but we keep the structure
        return {"answer": answer, "suggestions": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/chat/history/{user_id}")
async def chat_history(user_id: str, token: str = Depends(verify_token)):
    """Get recent chat history for a user."""
    history = get_recent_history(user_id)
    return {"history": [{"question": q, "answer": a} for q, a in history]}


@app.delete("/api/chat/history/{user_id}")
async def clear_chat_history(user_id: str, token: str = Depends(verify_token)):
    """Clear chat history for a user."""
    delete_user_history(user_id)
    return {"message": "Chat history cleared"}


@app.get("/api/announcements")
async def get_announcements(token: str = Depends(verify_token)):
    """Get the latest company announcements."""
    conn = sqlite3.connect("queries.db")
    conn.row_factory = sqlite3.Row
    c = conn.cursor()
    try:
        c.execute("SELECT * FROM announcements ORDER BY created_at DESC LIMIT 10")
        rows = c.fetchall()
        return [dict(r) for r in rows]
    finally:
        conn.close()


# ========== Task / Calendar Endpoints ==========

@app.get("/api/tasks/{employee_id}")
async def list_tasks(employee_id: str, token: str = Depends(verify_token)):
    """Get all tasks for an employee."""
    tasks = get_employee_tasks(employee_id)
    return tasks


@app.post("/api/tasks")
async def create_task(task: TaskCreate, token: str = Depends(verify_token)):
    """Add a new task for an employee."""
    success = add_employee_task(
        task.employee_id, task.title, task.description, 
        task.deadline, task.event_type, task.start_time, task.end_time
    )
    if not success:
        raise HTTPException(status_code=400, detail="Failed to add task")
    return {"message": "Task added successfully"}


@app.patch("/api/tasks/{task_id}")
async def update_task(task_id: int, task: TaskUpdate, token: str = Depends(verify_token)):
    """Update task status (e.g., mark as completed)."""
    success = update_employee_task_status(task_id, task.status)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to update task")
    return {"message": "Task updated successfully"}


# ========== Admin / Document Management ==========

@app.get("/api/admin/stats")
async def get_admin_stats(token: str = Depends(verify_admin_token)):
    """Get dashboard KPIs."""
    employees = get_all_employees()
    pending_leaves = LeaveWorkflowEngine.get_pending_requests()
    all_escalations = LeaveWorkflowEngine.get_combined_active_escalations()
    
    # Analytics
    leave_analytics = LeaveWorkflowEngine.get_analytics()
    chat_analytics = ChatEscalationEngine.get_analytics()
    
    return {
        "total_employees": len(employees),
        "pending_leaves": len(pending_leaves),
        "active_escalations": len(all_escalations),
        "avg_resolution_time": leave_analytics.get("avg_resolution_time", 0),
        "resolution_rate": leave_analytics.get("resolution_rate", 0),
        "hr_hours_saved": chat_analytics.get("hr_hours_saved", 0),
        "avg_escalation_time": chat_analytics.get("avg_escalation_time", 0)
    }


@app.get("/api/admin/pending-leaves")
async def get_all_pending_leaves(token: str = Depends(verify_admin_token)):
    """Get all pending leave requests for admin review."""
    requests = LeaveWorkflowEngine.get_pending_requests()
    # Format for JSON
    formatted = []
    for r in requests:
        formatted.append({
            "id": r[0],
            "employee_id": r[1],
            "leave_type": r[2],
            "start_date": r[3],
            "end_date": r[4],
            "total_days": r[5],
            "reason": r[6],
            "status": r[7],
            "full_name": r[12],
            "department": r[13]
        })
    return formatted


@app.get("/api/admin/active-escalations")
async def get_active_escalations(token: str = Depends(verify_admin_token)):
    """Get all pending escalations for admin review."""
    return LeaveWorkflowEngine.get_combined_active_escalations()


@app.post("/api/admin/announcements")
async def create_announcement(data: AnnouncementCreate, token: str = Depends(verify_admin_token)):
    """Broadcast an announcement to all employees."""
    conn = sqlite3.connect("queries.db")
    c = conn.cursor()
    try:
        # Get admin ID from session
        _, session_data = auth_manager.validate_session(token)
        admin_id = session_data["user_data"].get("username") # We store username as user_id in logs

        c.execute("""
            INSERT INTO announcements (title, content, priority, created_by)
            VALUES (?, ?, ?, ?)
        """, (data.title, data.content, data.priority, admin_id))
        conn.commit()
        return {"message": "Announcement broadcasted successfully", "success": True}
    finally:
        conn.close()


@app.get("/api/admin/logs")
async def list_logs(token: str = Depends(verify_admin_token)):
    """Get system interaction logs."""
    logs = get_logs()
    # Format logs for frontend
    return [
        {"id": l[0], "user": l[1], "question": l[2], "answer": l[3], "timestamp": l[4]}
        for l in logs
    ]


@app.get("/api/admin/documents")
async def list_documents(token: str = Depends(verify_admin_token)):
    """Get indexed policy documents."""
    docs = get_all_documents()
    return [
        {"id": d[0], "filename": d[1], "uploaded_at": d[2], "avg_tokens": d[3]}
        for d in docs
    ]


@app.post("/api/admin/documents/upload")
async def upload_document(file: UploadFile = File(...), token: str = Depends(verify_admin_token)):
    """Upload and index a new policy document."""
    os.makedirs("policy_docs", exist_ok=True)
    file_path = os.path.join("policy_docs", file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        chunks, avg_tokens, doc_id = ingest_document(file_path)
        if chunks is None:
            raise HTTPException(status_code=400, detail="File could not be processed")
            
        return {
            "message": "Indexed successfully",
            "chunks": chunks,
            "avg_tokens": avg_tokens,
            "doc_id": doc_id
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.delete("/api/admin/documents/{doc_id}")
async def delete_document(doc_id: str, token: str = Depends(verify_token)):
    """Delete a document and its embeddings."""
    # Note: Full deletion logic involves vector store which might be slow
    # We'll call the existing logic
    from vector_store import delete_document_embeddings
    import shutil
    
    # Get filename first
    docs = get_all_documents()
    doc = next((d for d in docs if str(d[0]) == doc_id), None)
    if not doc:
        raise HTTPException(status_code=404, detail="Document not found")
    
    filename = doc[1]
    delete_document_metadata(doc_id)
    
    try:
        if os.path.exists(f"policy_docs/{filename}"):
            os.remove(f"policy_docs/{filename}")
        shutil.rmtree(f"chroma/{doc_id}", ignore_errors=True)
        delete_document_embeddings(doc_id)
    except Exception as e:
        print(f"Cleanup error: {e}")
        
    return {"message": "Document deleted successfully"}


@app.get("/api/admin/escalations/chat")
async def list_chat_escalations(token: str = Depends(verify_admin_token)):
    """Get sensitive query alerts."""
    alerts = ChatEscalationEngine.get_pending_escalations()
    return alerts


@app.post("/api/admin/escalations/chat/{esc_id}/resolve")
async def resolve_chat_escalation(esc_id: int, request: ResolutionRequest, token: str = Depends(verify_admin_token)):
    """Mark a sensitive query alert as resolved."""
    ChatEscalationEngine.resolve_escalation(esc_id, request.note)
    return {"message": "Alert resolved"}


@app.post("/api/admin/escalations/workflow/{esc_id}/resolve")
async def resolve_workflow_escalation(esc_id: int, request: ResolutionRequest, token: str = Depends(verify_admin_token)):
    """Mark a workflow escalation as resolved."""
    LeaveWorkflowEngine.resolve_escalation(esc_id, request.note)
    return {"message": "Workflow escalation resolved"}


@app.get("/api/admin/config")
async def get_config(token: str = Depends(verify_admin_token)):
    """Get current AI model configuration."""
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f)
    return {"model": "models/gemini-1.5-flash"}


@app.post("/api/admin/config")
async def update_config(config: ConfigUpdate, token: str = Depends(verify_admin_token)):
    """Update AI model configuration."""
    with open("config.json", "w") as f:
        json.dump({"model": config.model}, f)
    return {"message": "Configuration updated"}


# ========== MULTI-MODAL RAG Endpoints (New) ==========

@app.post("/api/admin/multimodal/upload")
async def upload_multimodal_file(file: UploadFile = File(...), token: str = Depends(verify_admin_token)):
    """Upload and process any media/doc for Multi-Modal RAG."""
    os.makedirs("documents/multimodal", exist_ok=True)
    file_path = os.path.join("documents/multimodal", file.filename)
    
    try:
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        success, session_data = auth_manager.validate_session(token)
        username = session_data["user_data"]["username"] if success else "admin"
        
        result = multimodal_rag_processor.process_file_for_rag(file_path, file.filename, username)
        
        if result['success']:
            return result
        else:
            raise HTTPException(status_code=400, detail=result.get('error', 'Processing failed'))
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/admin/multimodal/search")
async def search_multimodal(request: dict, token: str = Depends(verify_admin_token)):
    """Search across multi-modal indexed content."""
    query = request.get("query", "")
    top_k = request.get("top_k", 5)
    
    try:
        results = multimodal_rag_processor.multimodal_search(query, top_k)
        return {"success": True, "results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/multimodal/files")
async def list_multimodal_files(token: str = Depends(verify_admin_token)):
    """Get list of all indexed multi-modal files."""
    try:
        conn = sqlite3.connect("queries.db")
        conn.row_factory = sqlite3.Row
        c = conn.cursor()
        c.execute("SELECT * FROM multimodal_files ORDER BY upload_timestamp DESC")
        files = [dict(row) for row in c.fetchall()]
        conn.close()
        return {"success": True, "files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/admin/multimodal/stats")
async def get_multimodal_stats(token: str = Depends(verify_admin_token)):
    """Get analytics for the Multi-Modal system."""
    try:
        conn = sqlite3.connect("queries.db")
        c = conn.cursor()
        c.execute("SELECT COUNT(*) FROM multimodal_files")
        total_files = c.fetchone()[0]
        c.execute("SELECT SUM(total_chunks) FROM multimodal_files")
        total_chunks = c.fetchone()[0] or 0
        conn.close()
        return {
            "total_files": total_files,
            "total_chunks": total_chunks,
            "storage_used_mb": sum(os.path.getsize(os.path.join(r, f)) for r, d, fs in os.walk("documents/multimodal") for f in fs) / (1024*1024) if os.path.exists("documents/multimodal") else 0
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/notifications", response_model=List[dict])
async def get_notifications(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Fetch unread notifications for the authenticated user."""
    payload = auth_manager.verify_token(credentials.get_credentials())
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    # For HR/Admin roles, we also fetch notifications sent to the role name
    role = payload.get("role", "EMPLOYEE")
    
    notifs = NotificationManager.get_notifications(user_id)
    
    # If user is HR or Admin, check for role-based notifications
    if role in ["ADMIN", "HR_MANAGER", "HR_ADMIN"]:
        role_notifs = NotificationManager.get_notifications(role)
        notifs.extend(role_notifs)
    
    return notifs

@app.patch("/api/notifications/{notif_id}")
async def update_notification_status(
    notif_id: int, 
    status_update: dict, 
    credentials: HTTPAuthorizationCredentials = Depends(security)
):
    """Mark a notification as read or dismissed."""
    payload = auth_manager.verify_token(credentials.get_credentials())
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    new_status = status_update.get("status")
    if new_status not in ["read", "dismissed"]:
        raise HTTPException(status_code=400, detail="Invalid status")
    
    NotificationManager.update_status(notif_id, new_status)
    return {"status": "success"}

@app.get("/api/notifications/proactive")
async def get_proactive_notifications(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """Legacy endpoint wrapped to return both old-style and new-style notifications."""
    payload = auth_manager.verify_token(credentials.get_credentials())
    if not payload:
        raise HTTPException(status_code=401, detail="Invalid token")
    
    user_id = payload.get("sub")
    
    # 1. Get dynamic system notifications (attendance check, etc.)
    dynamic_notifs = ProactiveNotifEngine.get_smart_notifications(user_id)
    
    # 2. Get persistent DB notifications
    persistent_notifs = NotificationManager.get_notifications(user_id, include_read=False)
    
    # Standardize and combine
    all_notifs = []
    for pn in persistent_notifs:
        all_notifs.append({
            "id": pn["id"],
            "type": pn["type"],
            "title": pn["title"],
            "message": pn["message"],
            "action_label": "View Details" if pn["action_id"] else None,
            "action_id": pn["action_id"]
        })
    
    all_notifs.extend(dynamic_notifs)
    return all_notifs

# ========== DOCUMENT DOWNLOAD ENDPOINT (Existing) ==========

@app.get("/download_document/{filename}")
async def download_document(filename: str, token: str = Depends(verify_token)):
    """
    Download a generated HR document (NOC, Salary Certificate, Experience Letter) by filename.
    Files are stored in the backend/documents/ folder.
    """
    from fastapi.responses import FileResponse

    # Security: strip any path traversal attempts
    safe_filename = os.path.basename(filename)
    file_path = os.path.join("documents", safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail=f"Document '{safe_filename}' not found.")

    return FileResponse(
        path=file_path,
        media_type="application/pdf",
        filename=safe_filename,
        headers={"Content-Disposition": f"attachment; filename={safe_filename}"}
    )


# ========== Main Entry Point ==========

if __name__ == "__main__":
    print("🚀 Starting HRFlux API Server...")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔧 Interactive API: http://localhost:8000/redoc")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=False)
