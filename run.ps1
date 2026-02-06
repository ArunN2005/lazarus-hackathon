# Start Backend
Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory "backend" -WindowStyle Normal

# Start Frontend
Start-Process -FilePath "npm" -ArgumentList "run dev" -WorkingDirectory "frontend" -WindowStyle Normal

Write-Host "Lazarus Protocol Initialized (Recovery Mode)..."
Write-Host "Backend: http://localhost:8000"
Write-Host "Frontend: http://localhost:3000"
