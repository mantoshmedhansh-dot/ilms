# ILMS.AI Project References

## CRITICAL SETUP RULES

### Database Configuration
- **This project uses Supabase ONLY for database**
- **DO NOT use Docker for database**
- **DO NOT use local PostgreSQL server**
- **DO NOT use docker-compose for any database operations**
- All development and production environments connect directly to Supabase
- Database URL is configured via environment variables pointing to Supabase

### Development Setup
1. Clone the repository
2. Set up environment variables with Supabase connection string
3. Run backend directly: `uvicorn app.main:app --reload`
4. Run frontend: `cd frontend && npm run dev`

### Why Supabase Only?
- Consistent data across all environments
- No local database setup required
- Multi-tenant schema management handled by Supabase
- Real-time capabilities built-in

---

## Deployment & Infrastructure Links

### GitHub Repository
- **URL:** https://github.com/mantoshmedhansh-dot/ilms
- **Branch:** main
- **Account:** mantoshmedhansh-dot

### Vercel (Frontend)
- **Dashboard:** https://vercel.com/ilms/frontend
- **Team:** ilms
- **Project:** frontend
- **Production URL:** https://frontend-ilms.vercel.app
- **Account:** mantoshmedhansh-dot

### Render (Backend API)
- **Dashboard:** https://dashboard.render.com/web/srv-d611qb7pm1nc73c94ar0
- **Environment:** https://dashboard.render.com/web/srv-d611qb7pm1nc73c94ar0/env
- **Service ID:** srv-d611qb7pm1nc73c94ar0
- **Production URL:** https://ilms-z6dz.onrender.com
- **API Docs:** https://ilms-z6dz.onrender.com/docs
- **Region:** Singapore

### Supabase (Database)
- **Dashboard:** https://supabase.com/dashboard/project/dhosrcfdjyuxozcxfbyh
- **Project ID:** dhosrcfdjyuxozcxfbyh
- **Pooler Host:** aws-1-ap-southeast-2.pooler.supabase.com
- **Session Mode (recommended):** Port 5432 - for schema creation and long transactions
- **Transaction Mode:** Port 6543 - for short queries only
- **DATABASE_URL Format:** `postgresql+psycopg://postgres.dhosrcfdjyuxozcxfbyh:[PASSWORD]@aws-1-ap-southeast-2.pooler.supabase.com:5432/postgres`

---

## Auto-Deploy Configuration

### Frontend (Vercel)
- Linked via `.vercel/project.json`
- Auto-deploys on push to `main` (via Vercel GitHub integration)

### Backend (Render)
- Auto-deploys via GitHub Actions workflow
- Workflow file: `.github/workflows/deploy-render.yml`
- Secret required: `RENDER_API_KEY` (stored in GitHub Secrets)

---

## Quick Commands

### Deploy Frontend
```bash
npx vercel --prod
```

### Deploy Backend (Manual)
```bash
curl -X POST -H "Authorization: Bearer $RENDER_API_KEY" \
  "https://api.render.com/v1/services/srv-d611qb7pm1nc73c94ar0/deploys"
```

### Check Backend Health
```bash
curl https://ilms-z6dz.onrender.com/health
```

---

## Environment Variables

### Frontend (.env.local)
```
NEXT_PUBLIC_API_URL=https://ilms-z6dz.onrender.com
```

### Backend (Render Environment)
- DATABASE_URL: Supabase connection string
- SECRET_KEY: JWT secret
- ENVIRONMENT: production
- ALLOWED_ORIGINS: Frontend URLs

---

## Important Notes

1. **Always push to `main` branch** - Both Vercel and Render auto-deploy from main
2. **Frontend changes** - Vercel deploys automatically via GitHub integration
3. **Backend changes** - Render deploys via GitHub Actions workflow
4. **Database** - Hosted on Supabase (project: dhosrcfdjyuxozcxfbyh)

## Known Issues - RESOLVED

### Backend 502 Errors - FIXED (2026-02-04)
**Root Cause:** DATABASE_URL was pointing to old Supabase host format (`db.{project}.supabase.co`) which no longer exists.
**Fix:** Updated to new Supabase Pooler format (`aws-1-ap-southeast-2.pooler.supabase.com`)

### Action Required on Render:
Update `DATABASE_URL` in Render Dashboard to:
```
postgresql+psycopg://postgres.dhosrcfdjyuxozcxfbyh:Aquapurite2026@aws-1-ap-southeast-2.pooler.supabase.com:6543/postgres
```

### render.yaml Security Fix Applied
- Removed hardcoded DATABASE_URL and SECRET_KEY from render.yaml
- These should ONLY be set in Render Dashboard Environment Variables
- Never commit secrets to git

# Last verified: Wed Feb  4 17:26:18 IST 2026

# Vercel connected to correct repo: Wed Feb  4 19:19:47 IST 2026

# Root directory fix verified: Wed Feb  4 19:33:31 IST 2026

# API URL env var added: Wed Feb  4 20:22:54 IST 2026
