# 🚀 Production Deployment Guide

This guide covers deploying the FPL Chatbot to various production environments.

## 📋 Pre-Deployment Checklist

### ✅ **Required Environment Variables**
```bash
# Essential for AI functionality
GROQ_API_KEY=your_groq_api_key_here

# Recommended for production performance
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your_supabase_anon_key

# Production security
SECRET_KEY=your-secure-secret-key-here
FLASK_ENV=production
```

### ✅ **System Requirements**
- Python 3.8+
- 512MB RAM minimum (1GB+ recommended)
- PostgreSQL database (Supabase recommended)
- HTTPS enabled domain

---

## 🌊 Railway Deployment (Recommended)

Railway offers the easiest deployment with automatic builds and scaling.

### **Step 1: Setup Railway**
```bash
# Install Railway CLI
npm install -g @railway/cli

# Login to Railway
railway login
```

### **Step 2: Deploy**
```bash
# In your project directory
railway link
railway up

# Set environment variables
railway variables set GROQ_API_KEY=your_key_here
railway variables set SUPABASE_URL=your_supabase_url
railway variables set SUPABASE_ANON_KEY=your_supabase_key
railway variables set SECRET_KEY=your_secure_secret_key
```

### **Step 3: Configure Domain**
```bash
# Generate Railway domain
railway domain

# Or add custom domain
railway domain add yourdomain.com
```

**✅ Expected Result**: Your FPL Chatbot will be live at `https://your-app.railway.app`

---

## 🟣 Heroku Deployment

### **Step 1: Heroku Setup**
```bash
# Install Heroku CLI
# Create new Heroku app
heroku create your-fpl-chatbot

# Configure buildpack
heroku buildpacks:set heroku/python
```

### **Step 2: Environment Configuration**
```bash
# Set required environment variables
heroku config:set GROQ_API_KEY=your_groq_api_key
heroku config:set SUPABASE_URL=your_supabase_url
heroku config:set SUPABASE_ANON_KEY=your_supabase_key
heroku config:set SECRET_KEY=$(openssl rand -base64 32)
heroku config:set FLASK_ENV=production
```

### **Step 3: Deploy**
```bash
# Deploy to Heroku
git push heroku main

# Open your deployed app
heroku open
```

**✅ Expected Result**: Your FPL Chatbot will be live at `https://your-fpl-chatbot.herokuapp.com`

---

## 🐳 Docker Deployment

### **Step 1: Build Container**
```bash
# Build the Docker image
docker build -t fpl-chatbot .

# Test locally
docker run -p 8080:8080 \
  -e GROQ_API_KEY=your_key \
  -e SUPABASE_URL=your_url \
  -e SUPABASE_ANON_KEY=your_key \
  fpl-chatbot
```

### **Step 2: Production Deployment**
```bash
# Tag for registry
docker tag fpl-chatbot your-registry/fpl-chatbot:latest

# Push to registry
docker push your-registry/fpl-chatbot:latest

# Deploy (example with docker-compose)
docker-compose up -d
```

### **Docker Compose Example**
```yaml
version: '3.8'
services:
  fpl-chatbot:
    image: your-registry/fpl-chatbot:latest
    ports:
      - "8080:8080"
    environment:
      - GROQ_API_KEY=${GROQ_API_KEY}
      - SUPABASE_URL=${SUPABASE_URL}
      - SUPABASE_ANON_KEY=${SUPABASE_ANON_KEY}
      - SECRET_KEY=${SECRET_KEY}
      - FLASK_ENV=production
    restart: unless-stopped
```

---

## ☁️ Cloud Platform Deployment

### **Google Cloud Run**
```bash
# Build and deploy
gcloud run deploy fpl-chatbot \
  --source . \
  --platform managed \
  --region us-central1 \
  --allow-unauthenticated \
  --set-env-vars GROQ_API_KEY=your_key,SUPABASE_URL=your_url
```

### **AWS Elastic Beanstalk**
```bash
# Install EB CLI
pip install awsebcli

# Initialize and deploy
eb init fpl-chatbot
eb create production
eb setenv GROQ_API_KEY=your_key SUPABASE_URL=your_url
eb deploy
```

### **DigitalOcean App Platform**
1. Connect your GitHub repository
2. Select Python app type
3. Set environment variables in the dashboard
4. Deploy automatically on git push

---

## 🔒 Production Security

### **Environment Variables Security**
```bash
# Generate secure secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"

# Set proper environment
export FLASK_ENV=production
export DEBUG=False
```

### **HTTPS Configuration**
Most platforms (Railway, Heroku) provide HTTPS automatically. For custom deployments:

```nginx
# Nginx configuration example
server {
    listen 443 ssl;
    server_name yourdomain.com;
    
    ssl_certificate /path/to/certificate.crt;
    ssl_certificate_key /path/to/private.key;
    
    location / {
        proxy_pass http://localhost:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

---

## 📊 Performance Optimization

### **Production Configuration**
```python
# config.py - Production settings
class ProductionConfig(Config):
    DEBUG = False
    GROQ_API_KEY = os.getenv('GROQ_API_KEY')
    SUPABASE_URL = os.getenv('SUPABASE_URL')
    
    # Performance settings
    WEB_CONCURRENCY = int(os.getenv('WEB_CONCURRENCY', 4))
    CACHE_TTL = 1800  # 30 minutes
    MAX_CONVERSATION_HISTORY = 10
```

### **Scaling Configuration**
```python
# gunicorn.conf.py
workers = int(os.environ.get('WEB_CONCURRENCY', 4))
worker_class = "sync"
timeout = 30
keepalive = 2
max_requests = 1000
```

---

## 🔍 Health Checks & Monitoring

### **Health Check Endpoint**
The app includes a built-in health check at `/health`:

```bash
# Test health check
curl https://your-app.com/health

# Expected response:
{
  "status": "healthy",
  "timestamp": "2025-09-07T12:00:00Z",
  "services": {
    "groq": "connected",
    "supabase": "connected",
    "fpl_api": "connected"
  }
}
```

### **Monitoring Setup**
```bash
# Add monitoring environment variables
export MONITORING_ENABLED=true
export LOG_LEVEL=INFO

# View logs
railway logs  # Railway
heroku logs --tail  # Heroku
docker logs fpl-chatbot  # Docker
```

---

## 🐛 Troubleshooting

### **Common Issues**

#### **"GROQ_API_KEY not found"**
```bash
# Verify environment variable is set
echo $GROQ_API_KEY

# Set if missing
export GROQ_API_KEY=your_actual_key_here
```

#### **"Port already in use"**
```bash
# Find and kill process using port 8080
lsof -ti :8080 | xargs kill -9

# Or use different port
export PORT=8081
```

#### **Database Connection Issues**
```bash
# Test Supabase connection
curl -H "Authorization: Bearer $SUPABASE_ANON_KEY" \
     "$SUPABASE_URL/rest/v1/"

# Fallback to FPL API only
unset SUPABASE_URL
```

### **Performance Issues**
- **Slow responses**: Check cache hit rate in logs
- **Memory usage**: Reduce `WEB_CONCURRENCY` 
- **High CPU**: Enable Supabase caching

---

## 📈 Post-Deployment Verification

### **✅ Deployment Checklist**
1. **App loads**: Visit your domain, see landing page
2. **AI works**: Ask "Hello!" - get friendly response
3. **Data works**: Ask "Haaland price" - get current FPL data
4. **Context works**: Ask about player, then "how much does he cost?"
5. **Performance**: Responses under 2 seconds
6. **HTTPS**: SSL certificate valid
7. **Monitoring**: Health checks passing

### **🧪 Test Commands**
```bash
# Test basic functionality
curl -X POST https://your-app.com/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "Hello!"}'

# Test FPL data
curl -X POST https://your-app.com/ask \
  -H "Content-Type: application/json" \
  -d '{"message": "What is Salah current price?"}'
```

---

## 🔄 Continuous Deployment

### **GitHub Actions (Optional)**
```yaml
# .github/workflows/deploy.yml
name: Deploy to Production
on:
  push:
    branches: [main]
jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v3
      - run: pip install -r requirements.txt
      - run: python -m pytest tests/
      - uses: railwayapp/railway-deploy@v1
        with:
          api_token: ${{ secrets.RAILWAY_TOKEN }}
```

---

**🏆 Congratulations! Your FPL Chatbot is now production-ready!**

For support: Create an issue at [GitHub Issues](https://github.com/fayyadrc/FPLChatbot/issues)
