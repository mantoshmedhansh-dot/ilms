#!/bin/bash

# Phase 1 Testing Script
# Starts backend server and runs API tests

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$( dirname "$SCRIPT_DIR" )"

echo "======================================================================"
echo "PHASE 1: Multi-Tenant Infrastructure Testing"
echo "======================================================================"
echo "Project directory: $PROJECT_DIR"
echo ""

# Change to project directory
cd "$PROJECT_DIR"

# Activate virtual environment
echo "Activating virtual environment..."
source .venv/bin/activate

# Kill any existing server on port 8000
echo "Cleaning up port 8000..."
lsof -ti:8000 | xargs kill -9 2>/dev/null || true
sleep 2

# Start backend server in background
echo ""
echo "Starting backend server..."
uvicorn app.main:app --reload --port 8000 > /tmp/ilms_server.log 2>&1 &
SERVER_PID=$!
echo "Server PID: $SERVER_PID"

# Wait for server to be ready
echo "Waiting for server to start..."
MAX_ATTEMPTS=30
for i in $(seq 1 $MAX_ATTEMPTS); do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "✅ Server is ready!"
        break
    fi
    sleep 1
    if [ $((i % 5)) -eq 0 ]; then
        echo "  Still waiting... ($i/$MAX_ATTEMPTS)"
    fi
    if [ $i -eq $MAX_ATTEMPTS ]; then
        echo "❌ Server failed to start"
        cat /tmp/ilms_server.log
        kill $SERVER_PID 2>/dev/null || true
        exit 1
    fi
done

# Run API tests
echo ""
echo "======================================================================"
echo "Running API Tests"
echo "======================================================================"
python3 scripts/test_phase1_api.py
TEST_RESULT=$?

# Cleanup: stop server
echo ""
echo "Stopping server..."
kill $SERVER_PID 2>/dev/null || true
wait $SERVER_PID 2>/dev/null || true

# Print server logs if tests failed
if [ $TEST_RESULT -ne 0 ]; then
    echo ""
    echo "======================================================================"
    echo "Server Logs (last 50 lines)"
    echo "======================================================================"
    tail -50 /tmp/ilms_server.log
fi

echo ""
if [ $TEST_RESULT -eq 0 ]; then
    echo "✅ Phase 1 testing completed successfully!"
else
    echo "❌ Phase 1 testing failed. Please review errors above."
fi

exit $TEST_RESULT
