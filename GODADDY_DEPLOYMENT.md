# Deploy AION Tech Career to GoDaddy

## Hosting requirement

Use **GoDaddy Web Hosting (cPanel)** or a GoDaddy VPS. In cPanel, confirm that
**Setup Python App** appears under **Software** before uploading. GoDaddy's
Websites + Marketing and Managed WordPress products cannot run this Python API.

The application must be mounted at the domain root because the browser submits
forms to `/api/enquiries` and `/api/applications`.

## 1. Upload the application

1. In GoDaddy, open **My Products > Web Hosting > Manage > File Manager**.
2. Create an application directory such as `aion_app` in your account home.
3. Upload `aion-godaddy-deploy.zip` into it and extract the ZIP.
4. Do not upload the local `.env` file or any local `data` directory.

## 2. Create the Python application

Open cPanel **Setup Python App**, select **Create Application**, and use:

- Python version: `3.11`
- Application root: `aion_app`
- Application URL: your production domain, at `/` (no subpath)
- Application startup file: `passenger_wsgi.py`
- Application entry point: `application`

No packages need to be installed; the app uses Python's standard library.

Add these environment variables in the Python application screen:

```text
SMTP_HOST=localhost
SMTP_PORT=25
SMTP_FROM_EMAIL=careers@aioncareer.in
SMTP_USE_TLS=false
ADMIN_EMAIL=careers@aioncareer.in
```

Leave `SMTP_USERNAME` and `SMTP_PASSWORD` unset for GoDaddy's local relay. The
sender address should be a mailbox on a domain whose DNS you manage. Add or
merge this value into the domain's SPF TXT record:

```text
v=spf1 include:secureserver.net -all
```

Restart the Python application after changing files or environment variables.

## 3. Connect the domain

In GoDaddy DNS, point:

- `A` record `@` to the Web Hosting (cPanel) IP address.
- `CNAME` record `www` to the root domain.

Back up the existing DNS records before changing them. DNS updates often appear
within a few hours but can take up to 48 hours globally.

## 4. Enable HTTPS and verify

Run cPanel **AutoSSL** after the domain points to the hosting account. Then open:

- `https://YOUR-DOMAIN/`
- `https://YOUR-DOMAIN/api/health`

The health response should contain `"status": "ok"` and
`"emailNotifications": "configured"`. Submit one enquiry and one test
application, confirm both emails arrive, and then remove the test records/files
from `data/` if necessary.

If **Setup Python App** is absent, ask GoDaddy to enable Python Selector for the
plan or use a VPS. Uploading only the HTML files would display the website, but
both forms would fail because their Python API would be missing.
