# AION Tech Career

Landing website and application API for AION Technology. Python 3.10 or newer
is required.

## Run locally

```powershell
python server.py
```

Open `http://127.0.0.1:8000`. Enquiries and job applications are stored in
`data/applications.db`; uploaded résumés and photos are stored under `data/`.

Copy `.env.example` to `.env` when configuring email locally. Never commit the
real `.env` file. Gmail SMTP is supported by setting the Gmail host, port,
username, app password, sender address, and TLS values. GoDaddy's local relay
works without a username or password.

## Deploy to GoDaddy

The production entry point is `passenger_wsgi.py`, callable `application`, for
GoDaddy Web Hosting (cPanel) Python Selector. Follow `GODADDY_DEPLOYMENT.md` for
the required hosting plan, upload, Python application, email, DNS, and SSL steps.

Run the checks before deployment:

```powershell
python -m unittest discover -s tests -v
```
