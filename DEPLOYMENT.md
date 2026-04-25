# SchemaGuard — Deployment Guide

Three options, ordered by how long they stay live:

| Option | Cost | Live time | Best for |
|---|---|---|---|
| A · Render (recommended) | Free tier | Always on | Course demo, sharing a link |
| B · Railway | Free $5 credit | Always on | Same, faster deploys |
| C · Vercel + Render split | Free | Always on | Frontend performance |

---

## Option A · Render (Recommended — Free, Always On)

Render runs the FastAPI backend as a Web Service and the Next.js frontend as a Static Site.
Both have free tiers. The live URL never sleeps on the Starter plan.

### Step 1 — Push clean code to GitHub

```bash
cd /Users/pragatinarote/Desktop/schema-guard-llm-validation

# Make sure .env is gitignored (it already is)
cat .gitignore | grep "\.env"   # should show .env

# Add and push everything except secrets
git add -A
git commit -m "deploy: production-ready"
git push origin main
```

### Step 2 — Deploy the backend on Render

1. Go to https://render.com → sign in with GitHub
2. Click **New → Web Service**
3. Connect the repo `PragatiAN1109/schema-guard-llm-validation`
4. Fill in these fields:

| Field | Value |
|---|---|
| Name | schemaguard-api |
| Root Directory | *(leave blank — root of repo)* |
| Runtime | Python 3 |
| Build Command | `pip install -r requirements.txt` |
| Start Command | `uvicorn api.main:app --host 0.0.0.0 --port $PORT` |
| Instance Type | Free |

5. Click **Advanced → Add Environment Variable** and add:

| Key | Value |
|---|---|
| `ANTHROPIC_API_KEY` | your actual key from console.anthropic.com |
| `PYTHON_VERSION` | 3.12.0 |

6. Click **Create Web Service**
7. Wait ~3 min for first deploy. You get a URL like:
   `https://schemaguard-api.onrender.com`

Test it:
```bash
curl https://schemaguard-api.onrender.com/health
```

### Step 3 — Update the frontend API URL

The frontend currently proxies to `localhost:8000`. Change it to point to Render:


```bash
# In frontend/next.config.js, change the destination line to your Render URL:
# destination: 'https://schemaguard-api.onrender.com/:path*',
```

Edit `frontend/next.config.js`:

```js
// Change this line:
destination: 'http://localhost:8000/api/:path*',

// To this (replace with your actual Render URL):
destination: 'https://schemaguard-api.onrender.com/api/:path*',
```

Then commit and push:
```bash
git add frontend/next.config.js
git commit -m "deploy: point frontend to Render backend"
git push origin main
```

### Step 4 — Deploy the frontend on Render

1. On Render → **New → Static Site**
2. Connect same repo
3. Fill in:

| Field | Value |
|---|---|
| Name | schemaguard-ui |
| Root Directory | `frontend` |
| Build Command | `npm install && npm run build && npm run export` |
| Publish Directory | `out` |

**Or deploy as a Node Web Service instead** (easier, handles Next.js routing):

| Field | Value |
|---|---|
| Name | schemaguard-ui |
| Root Directory | `frontend` |
| Runtime | Node |
| Build Command | `npm install && npm run build` |
| Start Command | `npm start` |
| Instance Type | Free |

4. Click **Create** → wait ~3 min
5. You get a URL like: `https://schemaguard-ui.onrender.com`

---

## Option B · Railway (Faster, $5 Free Credit)

Railway deploys both services from a single repo with zero config files needed.

### Backend

```bash
# Install Railway CLI
brew install railway

# Login
railway login

# From project root
cd /Users/pragatinarote/Desktop/schema-guard-llm-validation
railway init        # creates a new project
railway up          # deploys

# Set environment variables
railway variables set ANTHROPIC_API_KEY=your-key-here
railway variables set PORT=8000
```

Set the start command in Railway dashboard:
```
uvicorn api.main:app --host 0.0.0.0 --port $PORT
```

### Frontend

```bash
cd frontend
railway init --name schemaguard-ui
railway up
```

Set in Railway dashboard:
- Build: `npm install && npm run build`
- Start: `npm start`
- Env var: `NEXT_PUBLIC_API_URL=https://your-backend.railway.app`

---

## Option C · Vercel (frontend) + Render (backend)

Best option if you want the fastest frontend load times.

### Backend — same as Option A Step 2

### Frontend on Vercel

```bash
# Install Vercel CLI
npm install -g vercel

cd /Users/pragatinarote/Desktop/schema-guard-llm-validation/frontend

# Deploy
vercel

# Follow prompts:
# Project name: schemaguard-ui
# Framework: Next.js (auto-detected)
# Build command: npm run build (default)
# Output dir: .next (default)
```

Add environment variable in Vercel dashboard:
- `NEXT_PUBLIC_API_URL` = `https://schemaguard-api.onrender.com`

Then update `frontend/next.config.js`:
```js
destination: `${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/api/:path*`
```

Your frontend URL: `https://schemaguard-ui.vercel.app`

---

## Important: what to NOT commit

These are already in `.gitignore` but double-check before pushing:

```bash
# These must never be pushed:
.env                    # contains ANTHROPIC_API_KEY
.env.local
audit_logs/             # may contain real data
__pycache__/
frontend/.next/
frontend/node_modules/
```

Run this before pushing to verify:
```bash
git status              # .env should NOT appear here
git diff --cached       # check what's staged
```

---

## Free-tier limitations to know

| Platform | Limitation |
|---|---|
| Render Free | Spins down after 15 min inactivity, ~30s cold start |
| Render Starter ($7/mo) | Always on, no cold start |
| Railway | $5 free credit, then pay-as-you-go |
| Vercel Free | 100GB bandwidth/mo, hobby projects only |

**For a course demo:** Render free tier is fine. The cold start only happens if no one visits for 15 min. You can keep it warm by visiting the `/health` endpoint before your presentation.

Warm-up curl (run this 30 seconds before your demo):
```bash
curl https://schemaguard-api.onrender.com/health
```

---

## Quickest path to a live link (15 minutes total)

```bash
# 1. Push to GitHub (2 min)
cd /Users/pragatinarote/Desktop/schema-guard-llm-validation
git add -A && git commit -m "deploy" && git push origin main

# 2. Go to render.com → New Web Service → connect repo (5 min)
#    Start command: uvicorn api.main:app --host 0.0.0.0 --port $PORT
#    Add env var: ANTHROPIC_API_KEY=your-key

# 3. Update frontend/next.config.js with Render URL → push (2 min)

# 4. Render auto-redeploys, get live URL (5 min)
```

Total: ~15 minutes, free, permanent URL.
