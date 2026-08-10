# AION

Single-page landing website for Aion Career.

## Project structure

```text
index.html
assets/
  css/styles.css
  images/
  js/script.js
  videos/splash-video.mp4
```

## Run locally

Python 3.10 or newer is required. Start the website and application API together:

```powershell
python server.py
```

Open `http://127.0.0.1:8000`. Enquiries and job applications are stored in
`data/applications.db`, with uploaded resumes under `data/resumes/`.

## Application email notifications

Copy `.env.example` to `.env` and fill in the SMTP username, app password and
sender address. When an application succeeds, the server emails the complete
application and attached resume to `ADMIN_EMAIL`, then sends a confirmation to
the candidate. The application remains saved if email delivery temporarily
fails, and the failure is written to the server log.

Never commit a real SMTP password. For an existing Render service, add
`SMTP_USERNAME`, `SMTP_PASSWORD` and `SMTP_FROM_EMAIL` manually under the
service's **Environment** settings. The non-secret settings are declared in
`render.yaml`.

## Deploy on Render

Deploy the repository as a **Web Service** (not a Static Site). The included
`render.yaml` starts `python server.py`, uses Render's assigned port, and checks
`/api/health` after deployment.
