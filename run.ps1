# Start Backend with error handling
Start-Process powershell -ArgumentList "-NoExit", "-Command", "cd backend; python main.py; Write-Host 'Backend crashed. Press any key to close...'; Read-Host" -WindowStyle Normal

# Wait a moment for backend to start
Start-Sleep -Seconds 2

# Start Frontend
Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "frontend" -WindowStyle Normal

Write-Host "Lazarus Protocol Initialized (Recovery Mode)..."
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"

