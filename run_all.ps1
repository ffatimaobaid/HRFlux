cd d:\Downloads\HR_Chatbot_version2
if (Test-Path "venv\Scripts\Activate.ps1") {
    . .\venv\Scripts\Activate.ps1
}
else {
    Write-Host "Virtual environment not found, creating one..."
    python -m venv venv
    . .\venv\Scripts\Activate.ps1
}
python -m pip install -r requirements.txt

Write-Host "Starting Backend API..."
Start-Process powershell -ArgumentList "-NoExit -Command `"title FastAPI Backend; cd d:\Downloads\HR_Chatbot_version2; .\venv\Scripts\Activate.ps1; python -m uvicorn backend_api:app --reload`""

Write-Host "Starting Chat App JS..."
Start-Process powershell -ArgumentList "-NoExit -Command `"title HR Chat App; cd d:\Downloads\HR_Chatbot_version2; .\venv\Scripts\Activate.ps1; python -m streamlit run chat_app.py --server.port 8501`""

Write-Host "Starting Admin App..."
Start-Process powershell -ArgumentList "-NoExit -Command `"title HR Admin App; cd d:\Downloads\HR_Chatbot_version2; .\venv\Scripts\Activate.ps1; python -m streamlit run admin_app.py --server.port 8502`""

Write-Host "All services started successfully in separate windows."
