# ILMS.AI Project References

## Deployment & Infrastructure Links

### GitHub Repository
- **URL:** https://github.com/mantoshmedhansh-dot/ilms
- **Branch:** main
- **Account:** mantoshmedhansh-dot

### Vercel (Frontend)
- **Dashboard:** https://vercel.com/ilms/ilmsfrontend
- **Team:** ilms
- **Project:** ilmsfrontend
- **Production URL:** https://ilmsfrontend.vercel.app
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

# Last verified: Wed Feb  4 17:26:18 IST 2026

# Vercel connected to correct repo: Wed Feb  4 19:19:47 IST 2026
