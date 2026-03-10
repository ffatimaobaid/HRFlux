cd d:\Downloads\HR_Chatbot_version2
if (Test-Path "env2\Scripts\Activate.ps1") {
    . .\env2\Scripts\Activate.ps1
}
else {
    Write-Host "Virtual environment env2 not found."
    exit 1
}

Write-Host "Starting Backend API in background..."
Start-Process powershell -ArgumentList "-NoExit -Command `"title FastAPI Backend; cd d:\Downloads\HR_Chatbot_version2; .\env2\Scripts\Activate.ps1; uvicorn backend_api:app --reload`""

Write-Host "Starting HR Chat App..."
streamlit run chat_app.py --server.port 8501
