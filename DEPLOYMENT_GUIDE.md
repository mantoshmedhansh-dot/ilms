# 🚀 Production Deployment Guide
## Vercel + Render + Supabase

**Your Stack (Perfect Choice!):**
- ✅ **Vercel** - Frontend (Next.js) - Best for React/Next.js
- ✅ **Render** - Backend (FastAPI) - Free tier available
- ✅ **Supabase** - Database (PostgreSQL) - Already configured

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│              VERCEL (Frontend)                      │
│         https://ilms.vercel.app                     │
│         or https://your-domain.com                  │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼ API Calls
┌─────────────────────────────────────────────────────┐
│              RENDER (Backend)                       │
│      https://ilms-api.onrender.com                  │
│             FastAPI + Uvicorn                       │
└───────────────────┬─────────────────────────────────┘
                    │
                    ▼ SQL Queries
┌─────────────────────────────────────────────────────┐
│             SUPABASE (Database)                     │
│  db.ywiurorfxrjvftcnenyk.supabase.co               │
│         PostgreSQL + 237 Tables                     │
└─────────────────────────────────────────────────────┘
```

---

## STEP 1: Prepare Backend for Render 🔧

### 1.1 Check/Create requirements.txt
Already exists, but verify it includes all dependencies.

### 1.2 Create Render Build Script
Create a startup script for Render.

### 1.3 Verify Environment Variables
Backend needs these env vars on Render.

---

## STEP 2: Deploy Backend to Render 🚀

### 2.1 Login to Render
1. Go to https://render.com
2. Sign up or login with GitHub
3. Connect your GitHub account

### 2.2 Create New Web Service
1. Click "New +" → "Web Service"
2. Connect Repository: `ilms.ai`
3. Configure:
   - **Name:** `ilms-api` (or your choice)
   - **Region:** Choose closest to your users
   - **Branch:** `main`
   - **Root Directory:** `.` (leave empty or specify if needed)
   - **Runtime:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free (or paid for production)

### 2.3 Add Environment Variables on Render
Go to Environment tab and add:

```bash
# Database (CRITICAL)
DATABASE_URL=postgresql+psycopg://postgres:Aquapurite2026@db.ywiurorfxrjvftcnenyk.supabase.co:6543/postgres

# Security (CRITICAL - Generate new secret!)
SECRET_KEY=your-super-secret-key-change-this-in-production-min-32-chars
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7

# Environment
ENVIRONMENT=production
DEBUG=False

# CORS (CRITICAL - Your Vercel URL)
ALLOWED_ORIGINS=https://your-app.vercel.app,https://your-domain.com

# Optional: Email (for notifications)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password

# Optional: Payment Gateway
RAZORPAY_KEY_ID=your_key_id
RAZORPAY_KEY_SECRET=your_key_secret
```

### 2.4 Deploy
1. Click "Create Web Service"
2. Wait 5-10 minutes for build
3. Note your URL: `https://ilms-api.onrender.com`

### 2.5 Test Backend
```bash
# Health check
curl https://ilms-api.onrender.com/health

# API docs
open https://ilms-api.onrender.com/docs
```

**⚠️ IMPORTANT:** First request may take 50 seconds (cold start). Subsequent requests are fast.

---

## STEP 3: Prepare Frontend for Vercel 🔧

### 3.1 Create/Update Environment Variables File

### 3.2 Fix Build Issues (Optional Dependencies)
The build errors are from optional pages using dependencies.

### 3.3 Update CORS in Backend
Make sure your Render backend allows Vercel domain.

---

## STEP 4: Deploy Frontend to Vercel 🚀

### 4.1 Login to Vercel
1. Go to https://vercel.com
2. Sign up or login with GitHub
3. Connect your GitHub account

### 4.2 Import Project
1. Click "Add New" → "Project"
2. Import Git Repository: `ilms.ai`
3. Configure:
   - **Framework Preset:** Next.js (auto-detected)
   - **Root Directory:** `frontend`
   - **Build Command:** `pnpm build` (or leave default)
   - **Output Directory:** `.next` (default)
   - **Install Command:** `pnpm install`

### 4.3 Add Environment Variables on Vercel
Go to Settings → Environment Variables:

```bash
# API URL (CRITICAL - Your Render URL)
NEXT_PUBLIC_API_URL=https://ilms-api.onrender.com

# Optional: Google Maps (if used)
NEXT_PUBLIC_GOOGLE_MAPS_KEY=your_key_here
```

### 4.4 Deploy
1. Click "Deploy"
2. Wait 2-5 minutes for build
3. Note your URL: `https://ilms-xxxxx.vercel.app`

### 4.5 Test Frontend
```bash
# Open in browser
open https://your-app.vercel.app

# Test registration
open https://your-app.vercel.app/register
```

---

## STEP 5: Connect Everything Together 🔗

### 5.1 Update Backend CORS
In Render dashboard, update environment variable:
```bash
ALLOWED_ORIGINS=https://your-app.vercel.app,https://your-domain.com
```

### 5.2 Test Complete Flow
1. Open: `https://your-app.vercel.app/register`
2. Register a new tenant
3. Wait for 4-minute tenant creation
4. Verify login works
5. Check dashboard access

### 5.3 Verify Database
```bash
# Check Supabase for new tenant schema
# Should see: tenant_{subdomain} with 237 tables
```

---

## STEP 6: Custom Domain (Optional) 🌐

### 6.1 Add Domain to Vercel
1. Go to Project Settings → Domains
2. Add your domain: `ilms.ai` or `www.ilms.ai`
3. Follow DNS configuration instructions

### 6.2 Update Environment Variables
Update both Vercel and Render with new domain:
```bash
# Vercel: No change needed (auto-detects)

# Render: Update CORS
ALLOWED_ORIGINS=https://ilms.ai,https://www.ilms.ai
```

---

## STEP 7: Monitoring & Optimization 📊

### 7.1 Enable Vercel Analytics
1. Go to Project → Analytics
2. Enable Web Analytics
3. Monitor performance

### 7.2 Enable Render Health Checks
1. Go to Service → Settings
2. Set Health Check Path: `/health`
3. Enable Auto-Deploy from GitHub

### 7.3 Supabase Monitoring
1. Go to Supabase Dashboard
2. Check Database → Performance
3. Monitor query performance

---

## Environment Variables Summary

### Render (Backend) - REQUIRED
```env
DATABASE_URL=postgresql+psycopg://postgres:Aquapurite2026@db.ywiurorfxrjvftcnenyk.supabase.co:6543/postgres
SECRET_KEY=generate-a-new-secret-key-min-32-characters-long
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_DAYS=7
ENVIRONMENT=production
DEBUG=False
ALLOWED_ORIGINS=https://your-app.vercel.app
```

### Vercel (Frontend) - REQUIRED
```env
NEXT_PUBLIC_API_URL=https://ilms-api.onrender.com
```

---

## Troubleshooting 🔧

### Issue: Backend Cold Start (50 seconds)
**Solution:**
- Upgrade to paid Render plan ($7/mo keeps instance alive)
- Or use cron job to ping every 10 minutes:
  ```bash
  # Use cron-job.org or similar
  GET https://ilms-api.onrender.com/health
  ```

### Issue: CORS Error
**Problem:** Frontend can't connect to backend
**Solution:**
```bash
# In Render, update:
ALLOWED_ORIGINS=https://your-exact-vercel-url.vercel.app

# Redeploy backend
```

### Issue: Database Connection Error
**Problem:** Backend can't reach Supabase
**Solution:**
```bash
# Verify DATABASE_URL in Render matches exactly:
postgresql+psycopg://postgres:Aquapurite2026@db.ywiurorfxrjvftcnenyk.supabase.co:6543/postgres

# Check Supabase IP allowlist (if enabled)
```

### Issue: Build Fails on Vercel
**Problem:** Missing dependencies
**Solution:**
```bash
# In frontend directory:
pnpm install @dnd-kit/accessibility @tiptap/core
git add package.json pnpm-lock.yaml
git commit -m "Add missing dependencies"
git push
```

---

## Cost Breakdown 💰

### Free Tier (Perfect for Development/Testing)
- **Vercel:** Free (Hobby Plan)
  - Unlimited deployments
  - 100GB bandwidth/month
  - Serverless functions
- **Render:** Free
  - ⚠️ Spins down after 15 min inactivity (50s cold start)
  - 750 hours/month
- **Supabase:** Free
  - 500MB database
  - 2GB bandwidth
  - 50k API requests/month

**Total: $0/month** ✅

### Production Ready (Recommended)
- **Vercel:** $20/month (Pro Plan)
  - Custom domains
  - Analytics
  - Password protection
- **Render:** $7/month (Starter Plan)
  - No cold starts
  - Always-on instance
  - 512MB RAM
- **Supabase:** $25/month (Pro Plan)
  - 8GB database
  - 100GB bandwidth
  - Daily backups

**Total: $52/month** ✅

---

## Security Checklist 🔒

### Before Going Live
- [ ] Generate new SECRET_KEY (32+ characters)
- [ ] Change Supabase database password
- [ ] Enable HTTPS only
- [ ] Configure CORS properly
- [ ] Set DEBUG=False in production
- [ ] Enable rate limiting
- [ ] Set up database backups
- [ ] Configure firewall rules
- [ ] Enable 2FA on all accounts

---

## Post-Deployment Checklist ✅

- [ ] Backend deployed to Render
- [ ] Backend health check working
- [ ] Frontend deployed to Vercel
- [ ] Frontend loads correctly
- [ ] Registration flow works
- [ ] Login works
- [ ] Dashboard accessible
- [ ] Module management works
- [ ] Billing displays correctly
- [ ] Database connection stable
- [ ] CORS configured correctly
- [ ] Environment variables set
- [ ] Custom domain configured (optional)
- [ ] Analytics enabled
- [ ] Monitoring set up

---

## Quick Deploy Commands

### Deploy Backend (Render)
```bash
# Render auto-deploys from GitHub main branch
git add .
git commit -m "Deploy to production"
git push origin main

# Render will automatically:
# 1. Pull latest code
# 2. Install dependencies
# 3. Start uvicorn
# 4. Health check
```

### Deploy Frontend (Vercel)
```bash
# Vercel auto-deploys from GitHub main branch
git add .
git commit -m "Deploy to production"
git push origin main

# Vercel will automatically:
# 1. Pull latest code
# 2. Install dependencies
# 3. Build Next.js
# 4. Deploy to edge network
```

---

## Success Criteria 🎯

Your deployment is successful when:
1. ✅ You can access `https://your-app.vercel.app/register`
2. ✅ Subdomain check works in real-time
3. ✅ You can complete full registration flow
4. ✅ Backend creates 237 tables in ~4 minutes
5. ✅ You're automatically logged in
6. ✅ Dashboard loads with all sections
7. ✅ No CORS errors in console
8. ✅ API calls complete successfully

---

## Support Resources

### Vercel
- Docs: https://vercel.com/docs
- Discord: https://vercel.com/discord
- Status: https://vercel.com/status

### Render
- Docs: https://render.com/docs
- Community: https://community.render.com
- Status: https://status.render.com

### Supabase
- Docs: https://supabase.com/docs
- Discord: https://discord.supabase.com
- Status: https://status.supabase.com

---

**Ready to deploy? Let's go live!** 🚀
