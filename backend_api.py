"""
REST API Backend for HRFlux
FastAPI implementation for employee management, leave requests, and HR operations
"""

from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime
import uvicorn

from db_schema_v2 import (
    get_employee, get_all_employees, add_employee, 
    get_leave_balance, update_leave_balance
)
from workflow_engine import (
    LeaveWorkflowEngine, get_employee_leave_history
)

app = FastAPI(
    title="HRFlux API",
    description="REST API for HRFlux HR Management System",
    version="1.0.0"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

security = HTTPBearer()


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
    casual_leave_balance: int
    sick_leave_balance: int
    annual_leave_balance: int
    salary: Optional[float]
    status: str


class LeaveBalanceResponse(BaseModel):
    employee_id: str
    casual: int
    sick: int
    annual: int
    total_available: int


class LeaveRequestCreate(BaseModel):
    employee_id: str
    leave_type: str  # casual, sick, annual, emergency
    start_date: str  # YYYY-MM-DD
    end_date: str    # YYYY-MM-DD
    reason: str


class LeaveRequestResponse(BaseModel):
    success: bool
    message: str
    request_id: Optional[int]


class LeaveApprovalRequest(BaseModel):
    request_id: int
    approver_id: str
    action: str  # 'approve' or 'reject'
    comments: Optional[str] = None


# ========== Authentication (Simple Bearer Token) ==========

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    """
    Simple token verification. In production, use JWT or OAuth2.
    For demo purposes, accepting any non-empty token.
    """
    token = credentials.credentials
    if not token or len(token) < 10:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials"
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
        return employees
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/employees/{employee_id}", response_model=EmployeeResponse)
async def get_employee_info(employee_id: str, token: str = Depends(verify_token)):
    """Get employee details by ID."""
    employee = get_employee(employee_id=employee_id)
    if not employee:
        raise HTTPException(status_code=404, detail="Employee not found")
    return employee


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
        "casual": balances['casual'],
        "sick": balances['sick'],
        "annual": balances['annual'],
        "total_available": balances['casual'] + balances['sick'] + balances['annual']
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
    
    return result


@app.get("/api/leave-requests/{employee_id}")
async def get_leave_requests(employee_id: str, token: str = Depends(verify_token)):
    """Get leave request history for an employee."""
    history = get_employee_leave_history(employee_id)
    return {"employee_id": employee_id, "requests": history}


@app.post("/api/leave-approvals")
async def process_leave_approval(approval: LeaveApprovalRequest, token: str = Depends(verify_token)):
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
            reason=approval.comments or "No reason provided"
        )
    else:
        raise HTTPException(status_code=400, detail="Action must be 'approve' or 'reject'")
    
    if not result['success']:
        raise HTTPException(status_code=400, detail=result['message'])
    
    return result


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


# ========== Main Entry Point ==========

if __name__ == "__main__":
    print("🚀 Starting HRFlux API Server...")
    print("📖 API Documentation: http://localhost:8000/docs")
    print("🔧 Interactive API: http://localhost:8000/redoc")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
