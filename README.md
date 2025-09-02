# FPL Chatbot
A modern Fantasy Premier League chatbot with AI-powered responses and RAG (Retrieval-Augmented Generation) capabilities.

## Features
- 🤖 AI-powered FPL advice using Groq (Llama 3.1)
- 📊 Live FPL data integration
- 🎯 Smart captaincy recommendations with fixture analysis
- ⚡ Transfer rules and strategy guidance
- 🏆 Player analysis and differential picks
- 💰 Budget optimization suggestions

## Live Demo
[Deploy on Render](https://render.com) - Instructions below

## Quick Start
1. Clone the repository
2. Set up environment variables
3. Install dependencies: `pip install -r requirements.txt`
4. Run: `python backend/app.py`

## Environment Variables
```
GROQ_API_KEY=your_groq_api_key_here
```

## Deployment
This app is configured for easy deployment on Render, Railway, or Heroku.

## Tech Stack
- Backend: Flask (Python)
- AI: Groq API (Llama 3.1-8b-instant)
- Data: Fantasy Premier League API
- Frontend: HTML/CSS/JavaScript
