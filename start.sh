#!/bin/bash
set -e

echo "🚀 Starting FPL Chatbot in Production Mode"

# Check required environment variables
if [ -z "$GROQ_API_KEY" ]; then
    echo "❌ Error: GROQ_API_KEY environment variable is required"
    exit 1
fi

# Set production environment
export FLASK_ENV=production
export PYTHONPATH="${PYTHONPATH}:."

# Optional: Check if Supabase is configured
if [ -n "$SUPABASE_URL" ]; then
    echo "✅ Supabase configured for enhanced performance"
else
    echo "⚠️  Supabase not configured, using FPL API only"
fi

# Use Gunicorn if available, otherwise fall back to Python
if command -v gunicorn >/dev/null 2>&1; then
    echo "✅ Using Gunicorn WSGI server for production"
    exec gunicorn --config gunicorn.conf.py --bind 0.0.0.0:${PORT:-8080} app:app
else
    echo "⚠️  Gunicorn not found, falling back to Python app"
    exec python app.py
fi
if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_ANON_KEY" ]; then
    echo "✅ Supabase configuration detected - enhanced performance enabled"
else
    echo "⚠️  Supabase not configured - using FPL API only"
fi

# Start with Gunicorn
echo "🔧 Starting Gunicorn WSGI server..."
exec gunicorn --config gunicorn.conf.py app:app
