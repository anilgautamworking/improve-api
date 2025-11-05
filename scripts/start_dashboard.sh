#!/bin/bash
# Start the dashboard server

cd "$(dirname "$0")/.."
source venv/bin/activate

echo "🚀 Starting Daily Question Bank Dashboard..."
echo "📊 Dashboard will be available at: http://localhost:5000"
echo ""
echo "Press Ctrl+C to stop the server"
echo ""

# Add project root to Python path
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
python src/dashboard/app.py


