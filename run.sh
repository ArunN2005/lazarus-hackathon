#!/bin/bash

# Start Backend
echo "Starting Backend (StdLib)..."
cd backend
python main.py &
BACKEND_PID=$!
cd ..

# Start Frontend
echo "Starting Frontend..."
cd frontend
npm run dev &
FRONTEND_PID=$!
cd ..

echo "Lazarus Engine running..."
echo "Backend: http://localhost:8000"
echo "Frontend: http://localhost:3000"

# Kill both on exit
trap "kill $BACKEND_PID $FRONTEND_PID" EXIT

wait
