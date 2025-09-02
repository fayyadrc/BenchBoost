# 🚀 Deployment Guide: FPL Chatbot

## Option 1: Render (Recommended) ⭐

### Step 1: Prepare Repository
1. Push your code to GitHub
2. Ensure all files are committed:
   - `requirements.txt`
   - `Procfile` 
   - `wsgi.py`
   - `runtime.txt`

### Step 2: Deploy on Render
1. Go to [render.com](https://render.com) and sign up
2. Click "New" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `fpl-chatbot-[yourname]`
   - **Environment**: `Python`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn wsgi:app`
   - **Plan**: Free

### Step 3: Environment Variables
In Render dashboard, add:
- **Key**: `GROQ_API_KEY`
- **Value**: `your_groq_api_key_here`

### Step 4: Deploy!
- Click "Create Web Service"
- Wait for build to complete (~5 minutes)
- Your app will be live at: `https://fpl-chatbot-yourname.onrender.com`

---

## Option 2: Railway 🚂

### Quick Deploy
1. Go to [railway.app](https://railway.app)
2. Click "Deploy from GitHub repo"
3. Connect repository
4. Add environment variable: `GROQ_API_KEY`
5. Deploy!

---

## Option 3: Heroku (Classic) 

### Deploy Steps
```bash
# Install Heroku CLI
# Login to Heroku
heroku login

# Create app
heroku create your-fpl-chatbot

# Set environment variable
heroku config:set GROQ_API_KEY=your_key_here

# Deploy
git push heroku main
```

---

## 🔧 Troubleshooting

### Common Issues:
1. **Build fails**: Check `requirements.txt` versions
2. **App crashes**: Check logs for missing environment variables
3. **Import errors**: Verify all files are in correct directories

### Render Logs:
- Go to your service dashboard
- Click "Logs" to see real-time output
- Look for startup errors

### Test Deployment:
```bash
# Test locally first
python wsgi.py
# Visit http://localhost:5002
```

---

## 📊 Post-Deployment

### Monitor Usage:
- Check deployment platform dashboards
- Monitor response times
- Review error logs

### Share for Testing:
- Send URL to friends/FPL community
- Collect feedback
- Monitor API usage (Groq free tier limits)

### Scaling:
- Render: Upgrade to paid plan for 24/7 uptime
- Add custom domain
- Enable CDN for faster loading

---

## 🎯 Success Checklist
- [ ] Repository pushed to GitHub
- [ ] Deployment files created
- [ ] Environment variables set
- [ ] App builds successfully
- [ ] All routes working
- [ ] RAG system functioning
- [ ] FPL API integration working

Your FPL chatbot is now ready for user testing! 🏆
