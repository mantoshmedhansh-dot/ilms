# 🚀 DEPLOY NOW - Step-by-Step Checklist

**Generated:** 2026-02-01
**Stack:** Vercel + Render + Supabase
**Status:** Ready to Deploy

---

## ✅ PRE-DEPLOYMENT CHECKLIST

### Database (Supabase) - Already Configured ✅
- [x] Supabase project created
- [x] Database connection string ready
- [x] 237 operational tables schema verified
- [x] Control plane tables created

**Connection String:**
```
postgresql+psycopg://postgres:Aquapurite2026@db.ywiurorfxrjvftcnenyk.supabase.co:6543/postgres
```

### Backend Code - Ready ✅
- [x] FastAPI application complete
- [x] All APIs tested locally
- [x] requirements.txt up to date
- [x] Health check endpoint working

### Frontend Code - Ready ✅
- [x] Next.js 16 application
- [x] Registration page complete
- [x] API client configured
- [x] All components working

---

## 🎯 STEP 1: DEPLOY BACKEND TO RENDER (15 minutes)

### 1.1 Login to Render
```
1. Go to: https://render.com
2. Click "Get Started" or "Login"
3. Sign in with GitHub
4. Authorize Render to access your repositories
```

### 1.2 Create Web Service
```
1. Click "New +" button (top right)
2. Select "Web Service"
3. Connect your repository (if not connected)
4. Search for: ilms.ai
5. Click "Connect"
```

### 1.3 Configure Service
```
Name: ilms-api (or your choice)
Region: Singapore (or closest to you)
Branch: main
Root Directory: (leave blank)
Runtime: Python 3
Build Command: pip install -r requirements.txt
Start Command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
Instance Type: Free (for testing) or Starter (for production)
```

### 1.4 Add Environment Variables
Click "Advanced" → "Add Environment Variable"

**CRITICAL - Copy these EXACTLY:**
```env
DATABASE_URL=postgresql+psycopg://postgres:Aquapurite2026@db.ywiurorfxrjvftcnenyk.supabase.co:6543/postgres

SECRET_KEY=BxjvQKVUCLFVjJKVfeNTRjpDCNkvqwiHpPqBMlFiips

ACCESS_TOKEN_EXPIRE_MINUTES=60

REFRESH_TOKEN_EXPIRE_DAYS=7

ENVIRONMENT=production

DEBUG=False

ALLOWED_ORIGINS=*
```

**Note:** We'll update ALLOWED_ORIGINS after deploying frontend.

### 1.5 Deploy
```
1. Click "Create Web Service"
2. Wait 5-10 minutes for first deployment
3. Watch the logs for any errors
```

### 1.6 Get Your Backend URL
```
After deployment completes, you'll see:
"Your service is live at https://ilms-api.onrender.com"

Save this URL - you'll need it for frontend!
```

### 1.7 Test Backend
```bash
# Replace with your actual Render URL
curl https://ilms-api.onrender.com/health

# Should return:
# {"status":"healthy","app":"Consumer Durable Backend",...}

# Test API docs
open https://ilms-api.onrender.com/docs
```

**✅ Backend Deployed!** Copy your URL: `https://______.onrender.com`

---

## 🎯 STEP 2: DEPLOY FRONTEND TO VERCEL (10 minutes)

### 2.1 Login to Vercel
```
1. Go to: https://vercel.com
2. Click "Sign Up" or "Login"
3. Sign in with GitHub
4. Authorize Vercel to access your repositories
```

### 2.2 Import Project
```
1. Click "Add New..." → "Project"
2. Search for: ilms.ai
3. Click "Import"
```

### 2.3 Configure Project
```
Framework Preset: Next.js (auto-detected)
Root Directory: frontend
Build Command: pnpm build (default)
Output Directory: .next (default)
Install Command: pnpm install (default)
```

### 2.4 Add Environment Variables
Click "Environment Variables" section

**CRITICAL - Add this variable:**
```env
Name: NEXT_PUBLIC_API_URL
Value: https://your-render-url.onrender.com (from Step 1.6)

Example:
NEXT_PUBLIC_API_URL=https://ilms-api.onrender.com
```

### 2.5 Deploy
```
1. Click "Deploy"
2. Wait 2-5 minutes for build
3. Watch for any build errors
```

### 2.6 Get Your Frontend URL
```
After deployment completes:
"Congratulations! Your deployment is ready at:"
https://ilms-xxxxx.vercel.app

Save this URL!
```

**✅ Frontend Deployed!** Copy your URL: `https://______.vercel.app`

---

## 🎯 STEP 3: CONNECT FRONTEND & BACKEND (5 minutes)

### 3.1 Update Backend CORS
```
1. Go back to Render dashboard
2. Open your ilms-api service
3. Go to "Environment" tab
4. Find ALLOWED_ORIGINS variable
5. Click "Edit"
6. Update value to your Vercel URL:

ALLOWED_ORIGINS=https://your-app.vercel.app

Example:
ALLOWED_ORIGINS=https://ilms-kk7s2.vercel.app

7. Click "Save Changes"
8. Service will automatically redeploy (2-3 minutes)
```

### 3.2 Wait for Redeploy
```
Wait for backend to redeploy with new CORS settings
Check logs for: "Service is live"
```

**✅ CORS Configured!**

---

## 🎯 STEP 4: TEST COMPLETE SYSTEM (10 minutes)

### 4.1 Open Registration Page
```
URL: https://your-app.vercel.app/register

Example: https://ilms-kk7s2.vercel.app/register
```

### 4.2 Register Test Tenant
```
1. Enter subdomain: test123
2. Check shows "Available" (green check)
3. Fill form:
   - Company: Test Company
   - First Name: Test
   - Last Name: User
   - Email: test@example.com
   - Phone: +919876543210
   - Password: TestPass123!
4. Select modules:
   - System Admin (FREE)
   - OMS & Fulfillment
5. Choose Monthly billing
6. Click "Create My Tenant"
```

### 4.3 Watch Progress
```
Progress bar should show:
- 0-30%: Creating tenant schema...
- 30-60%: Setting up database tables...
- 60-90%: Configuring modules...
- 90-100%: Finalizing setup...

Total time: 3-5 minutes
```

### 4.4 Verify Success
```
After completion:
✅ You should be automatically logged in
✅ Redirected to /dashboard
✅ Dashboard loads successfully
✅ Can navigate to Settings → Subscriptions
✅ Can see billing information
```

### 4.5 Check Database
```
1. Go to Supabase dashboard
2. Open SQL Editor
3. Run query:
   SELECT schema_name
   FROM information_schema.schemata
   WHERE schema_name LIKE 'tenant_%';

4. Should see: tenant_test123

5. Count tables:
   SELECT COUNT(*)
   FROM information_schema.tables
   WHERE table_schema = 'tenant_test123';

6. Should return: 237
```

**✅ System Working!**

---

## 🎯 STEP 5: OPTIONAL - CUSTOM DOMAIN

### 5.1 Add Domain to Vercel (If you have one)
```
1. Go to Vercel Project Settings
2. Click "Domains"
3. Add your domain: ilms.ai or www.ilms.ai
4. Follow DNS configuration:
   - Type: A Record
   - Name: @ (or www)
   - Value: 76.76.21.21 (Vercel IP)

5. Or use CNAME:
   - Type: CNAME
   - Name: www
   - Value: cname.vercel-dns.com
```

### 5.2 Update Backend CORS
```
1. Go to Render → Environment
2. Update ALLOWED_ORIGINS:

ALLOWED_ORIGINS=https://ilms.ai,https://www.ilms.ai,https://your-app.vercel.app

3. Save and redeploy
```

---

## 📊 DEPLOYMENT URLS

Fill these in as you deploy:

```
Backend (Render):  https://_____________________.onrender.com
Frontend (Vercel): https://_____________________.vercel.app
Database (Supabase): db.ywiurorfxrjvftcnenyk.supabase.co:6543

Custom Domain (Optional): https://_____________________
```

---

## 🔥 TROUBLESHOOTING

### Issue: Backend takes 50 seconds to respond
**Cause:** Render free tier cold start
**Solutions:**
1. Upgrade to Starter plan ($7/mo) - keeps instance alive
2. Or wait 50s on first request after inactivity
3. Or use cron job to ping every 10 min

### Issue: CORS Error in Browser Console
**Symptom:** "Access to fetch blocked by CORS policy"
**Solution:**
```
1. Check ALLOWED_ORIGINS in Render includes exact Vercel URL
2. Include https:// in the URL
3. No trailing slash
4. Redeploy backend after changing
```

### Issue: Registration Timeout
**Symptom:** "Request timeout after 60 seconds"
**Cause:** Creating 237 tables takes 3-5 minutes
**Solution:**
- This is normal! Wait for full 4-5 minutes
- Progress bar shows status
- Don't refresh the page

### Issue: Build Fails on Vercel
**Symptom:** "Module not found: Can't resolve '@dnd-kit/accessibility'"
**Solution:**
```bash
cd frontend
pnpm install @dnd-kit/accessibility @tiptap/core
git add .
git commit -m "Add missing dependencies"
git push origin main

# Vercel will auto-redeploy
```

---

## ✅ SUCCESS CHECKLIST

Mark each as you complete:

- [ ] Render account created
- [ ] Backend deployed to Render
- [ ] Backend health check returns 200
- [ ] Backend API docs accessible
- [ ] Vercel account created
- [ ] Frontend deployed to Vercel
- [ ] Frontend loads in browser
- [ ] Registration page accessible
- [ ] CORS configured correctly
- [ ] Test registration completes
- [ ] 237 tables created in Supabase
- [ ] Auto-login works
- [ ] Dashboard accessible
- [ ] Subscriptions page works
- [ ] Billing page works
- [ ] No console errors

---

## 🎉 POST-DEPLOYMENT

### Share Your App
```
Registration: https://your-app.vercel.app/register
Login: https://your-app.vercel.app/login
```

### Monitor
```
Vercel Analytics: https://vercel.com/dashboard/analytics
Render Logs: https://dashboard.render.com (select service)
Supabase Dashboard: https://supabase.com/dashboard
```

### Next Steps
- Set up custom domain
- Enable Vercel Analytics
- Configure email notifications (SMTP)
- Add payment gateway (Razorpay)
- Set up monitoring alerts
- Enable database backups

---

## 💡 QUICK REFERENCE

**Your Stack:**
```
Frontend:  Vercel (Next.js 16)
Backend:   Render (FastAPI + Python 3.13)
Database:  Supabase (PostgreSQL)
```

**Deployment Time:**
- Backend: ~10 minutes
- Frontend: ~5 minutes
- Testing: ~10 minutes
- **Total: ~25 minutes**

**Costs:**
- Free Tier: $0/month (perfect for testing)
- Production: ~$52/month (Vercel Pro + Render Starter + Supabase Pro)

---

**Ready? Start with Step 1!** 🚀

Need help? The system is ready - just follow the steps above!
