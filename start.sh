#!/bin/bash
"""
Production startup script for FPL Chatbot
"""

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
if [ -n "$SUPABASE_URL" ] && [ -n "$SUPABASE_ANON_KEY" ]; then
    echo "✅ Supabase configuration detected - enhanced performance enabled"
else
    echo "⚠️  Supabase not configured - using FPL API only"
fi

# Start with Gunicorn
echo "🔧 Starting Gunicorn WSGI server..."
exec gunicorn --config gunicorn.conf.py app:app
