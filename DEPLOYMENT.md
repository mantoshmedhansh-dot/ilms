# AQUAPURITE Deployment Guide

## Architecture
```
Vercel (Frontend) → Render (Backend) → Supabase (Database)
     ↑
 Your Domain
```

---

## Step 1: Supabase Setup (Database)

1. Go to https://supabase.com → Create new project
2. Choose a region close to you (e.g., Singapore)
3. Set a strong database password
4. After creation, go to **Settings → Database**
5. Copy the connection string:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.[PROJECT-REF].supabase.co:5432/postgres
   ```

---

## Step 2: Push Code to GitHub

```bash
# Initialize git if not already done
git init
git add .
git commit -m "Initial commit for deployment"

# Create repo on GitHub, then:
git remote add origin https://github.com/YOUR_USERNAME/aquapurite.git
git branch -M main
git push -u origin main
```

---

## Step 3: Deploy Backend to Render

1. Go to https://render.com → New → Web Service
2. Connect your GitHub repository
3. Configure:
   - **Name**: `aquapurite-api`
   - **Root Directory**: `.` (leave empty)
   - **Runtime**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`

4. Add Environment Variables:
   | Key | Value |
   |-----|-------|
   | `DATABASE_URL` | `postgresql://postgres:[PASSWORD]@db.[PROJECT].supabase.co:5432/postgres` |
   | `SECRET_KEY` | (auto-generate or use a strong random string) |
   | `DEBUG` | `false` |
   | `CORS_ORIGINS` | `["https://yourdomain.com","https://www.yourdomain.com"]` |
   | `FRONTEND_URL` | `https://yourdomain.com` |

5. Deploy and note the URL: `https://aquapurite-api.onrender.com`

---

## Step 4: Run Database Migrations

After Render deployment, you need to run migrations to create tables:

**Option A: Via Render Shell**
1. Go to Render dashboard → Your service → Shell
2. Run:
   ```bash
   python -c "from app.database import init_db; import asyncio; asyncio.run(init_db())"
   ```

**Option B: Connect to Supabase directly**
1. Go to Supabase → SQL Editor
2. Run the schema migration SQL

---

## Step 5: Deploy Frontend to Vercel

1. Go to https://vercel.com → New Project
2. Import your GitHub repository
3. Configure:
   - **Framework Preset**: Next.js
   - **Root Directory**: `frontend`

4. Add Environment Variables:
   | Key | Value |
   |-----|-------|
   | `NEXT_PUBLIC_API_URL` | `https://aquapurite-api.onrender.com` |

5. Deploy

---

## Step 6: Connect Your Domain

### On Vercel:
1. Go to Project Settings → Domains
2. Add your domain (e.g., `aquapurite.com`)
3. Add `www.aquapurite.com` as well

### DNS Settings (at your domain registrar):
| Type | Name | Value |
|------|------|-------|
| A | @ | `76.76.21.21` |
| CNAME | www | `cname.vercel-dns.com` |

---

## Step 7: Seed Initial Data

After database is ready, create admin user and company:

```bash
# Via Render Shell or local with production DATABASE_URL
python scripts/seed_data.py
```

Or use the API to create:
1. Register first user at `/api/v1/auth/register`
2. Create company at `/api/v1/companies`

---

## Environment Variables Summary

### Backend (Render)
```env
DATABASE_URL=postgresql://postgres:PASSWORD@db.PROJECT.supabase.co:5432/postgres
SECRET_KEY=your-super-secret-key
DEBUG=false
CORS_ORIGINS=["https://yourdomain.com","https://www.yourdomain.com"]
FRONTEND_URL=https://yourdomain.com
RAZORPAY_KEY_ID=your_razorpay_key
RAZORPAY_KEY_SECRET=your_razorpay_secret
```

### Frontend (Vercel)
```env
NEXT_PUBLIC_API_URL=https://aquapurite-api.onrender.com
```

---

## Troubleshooting

### CORS Errors
- Ensure `CORS_ORIGINS` includes your exact domain with `https://`
- Check both `www` and non-www versions are listed

### Database Connection Issues
- Verify Supabase connection string is correct
- Ensure password doesn't have special chars that need URL encoding

### 502/503 Errors on Render
- Check Render logs for errors
- Ensure all required env vars are set
- Free tier sleeps after 15 min inactivity (first request may take 30s)

---

## Quick Reference

| Service | URL |
|---------|-----|
| Frontend | https://yourdomain.com |
| Backend API | https://aquapurite-api.onrender.com |
| API Docs | https://aquapurite-api.onrender.com/docs |
| Supabase | https://app.supabase.com |
