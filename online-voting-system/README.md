# SmartVote - Online Smart Voting System

SmartVote is a semester exhibition-ready voting system with a 3D Next.js frontend and a Python FastAPI backend. It includes voter signup, email OTP verification, signin, secure vote casting, admin results, audit logs, and an AI-agent inspired command center UI.

## Tech Stack

- Frontend: Next.js, React, Tailwind CSS
- Backend: Python, FastAPI
- Database: SQLite
- Auth: Secure password hashing, signed access tokens
- Email OTP: SMTP when configured, development OTP fallback when SMTP is missing

## Frontend Setup

```bash
npm install
npm run dev
```

Open:

```text
http://localhost:3000
```

## Backend Setup

Install Python dependencies:

```bash
python -m pip install -r backend/requirements.txt
```

Create backend environment file:

```bash
copy backend\.env.example backend\.env
```

Run the API:

```bash
python -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```

Health check:

```text
http://127.0.0.1:8000/health
```

## Email OTP

Set these values in `backend/.env` for real email delivery. Gmail requires an App Password; your normal Gmail password usually will not work.

```text
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your-email@gmail.com
SMTP_PASSWORD=your-app-password
SMTP_FROM=SmartVote <your-email@gmail.com>
```

If SMTP is not configured, the backend prints the OTP in the terminal and returns `dev_otp` in the signup response. This is useful for local demos and exhibition backup.

Admin panel shows SMTP status at `/admin`, so you can quickly confirm whether real OTP email is ready.

## Demo Accounts

Normal voter:

```text
Use any normal email address.
```

Admin:

```text
Email: admin@gmail.com
Password: admin
```

This admin account is seeded automatically in SQLite and is already verified.

## Pages

- `/` - 3D exhibition landing page
- `/signup` - voter/admin registration
- `/verify-email` - OTP verification
- `/signin` - login
- `/voter` - candidate voting dashboard
- `/admin` - admin results and audit dashboard

## Verified

These commands were run successfully:

```bash
npm run lint
npm run build
python -m compileall backend\app
```

The backend auth smoke test also passed: signup, OTP verification, signin, and candidate fetch.
