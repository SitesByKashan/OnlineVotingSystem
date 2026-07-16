# SmartVote Deployment Guide

Recommended setup:

- Frontend: Vercel
- Backend: Render Web Service
- Database: SQLite on a Render persistent disk for exhibition/demo use

## 1. Push Project To GitHub

Commit and push the `online-voting-system` folder to GitHub.

Do not commit these files:

- `backend/.env`
- Firebase service account JSON
- `smartvote.db`
- `node_modules`
- `.next`

## 2. Deploy Backend On Render

Create a new Render Web Service from the GitHub repo.

Use these settings if you configure manually:

- Runtime: Python
- Build Command: `pip install -r backend/requirements.txt`
- Start Command: `uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT`
- Health Check Path: `/health`

Add a persistent disk:

- Name: `smartvote-data`
- Mount Path: `/var/data`
- Size: `1 GB`

Environment variables:

```env
APP_SECRET=use-a-long-random-secret
DATABASE_PATH=/var/data/smartvote.db
FRONTEND_ORIGIN=https://your-vercel-app.vercel.app
ACCESS_TOKEN_MINUTES=480
OTP_EXPIRY_MINUTES=10
OTP_MAX_ATTEMPTS=5
SHOW_DEV_OTP=false
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-gmail-app-password
SMTP_FROM=SmartVote <your-email@gmail.com>
```

Optional Firebase:

```env
FIREBASE_PROJECT_ID=smartvote-exhibition
FIREBASE_CREDENTIALS_JSON=paste-the-full-service-account-json-in-one-line
```

After deploy, open:

```text
https://your-render-service.onrender.com/health
```

You should see:

```json
{"status":"ok","service":"smartvote-api","version":"2.0.0"}
```

## 3. Deploy Frontend On Vercel

Create a Vercel project from the same GitHub repo.

Settings:

- Framework: Next.js
- Build Command: `npm run build`
- Output Directory: leave default

Environment variable:

```env
NEXT_PUBLIC_API_BASE=https://your-render-service.onrender.com
```

Deploy the frontend.

## 4. Connect Frontend And Backend

After Vercel gives you a URL, update Render backend env:

```env
FRONTEND_ORIGIN=https://your-vercel-app.vercel.app
```

Redeploy the backend.

## 5. Admin Login

Default admin:

```text
Email: admin@gmail.com
Password: admin
```

Change the admin password before a real public demo.

## Notes

- Render free services can sleep after inactivity, so the first request may be slow.
- SQLite with a persistent disk is fine for an exhibition/demo. For heavy real public usage, migrate to Postgres.
- Gmail SMTP needs an App Password, not your normal Gmail password.
