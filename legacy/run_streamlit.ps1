Set-Location $PSScriptRoot
if (Test-Path "venv\Scripts\Activate.ps1") {
    . .\venv\Scripts\Activate.ps1
}
else {
    Write-Host "Virtual environment not found."
    exit 1
}

Write-Host "Starting Backend API in background..."
Start-Process powershell -ArgumentList "-NoExit -Command `"title FastAPI Backend; Set-Location '$PSScriptRoot'; .\venv\Scripts\Activate.ps1; uvicorn backend_api:app --reload`""

Write-Host "Starting HR Chat App..."
streamlit run chat_app.py --server.port 8501
