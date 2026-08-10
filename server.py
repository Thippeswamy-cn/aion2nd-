"""Aion Career development server and job application API."""

from __future__ import annotations

import json
import os
import posixpath
import re
import secrets
import smtplib
import sqlite3
import ssl
from datetime import datetime, timezone
from email.message import EmailMessage
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parent


def load_local_environment(path: Path) -> None:
    """Load local development settings without overriding real environment variables."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if key:
            os.environ.setdefault(key, value)


load_local_environment(ROOT / ".env")

DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "resumes"
PHOTO_DIR = DATA_DIR / "photos"
DATABASE = DATA_DIR / "applications.db"
MAX_REQUEST_SIZE = 10 * 1024 * 1024
MAX_RESUME_SIZE = 5 * 1024 * 1024
MAX_PHOTO_SIZE = 3 * 1024 * 1024
ALLOWED_RESUMES = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".doc": {"application/msword", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
}
ALLOWED_PHOTOS = {
    ".jpg": {"image/jpeg", "application/octet-stream"},
    ".jpeg": {"image/jpeg", "application/octet-stream"},
    ".png": {"image/png", "application/octet-stream"},
    ".webp": {"image/webp", "application/octet-stream"},
}
ROLES_BY_QUALIFICATION = {
    "Graduate": {
        "Branch Operations Executive", "Customer Success Associate",
        "Business Development Associate", "Other",
    },
    "Skilled graduate": {
        "Software Engineer", "Data Analyst", "Healthcare Administration Associate",
        "Customer Success Associate", "Quality Assurance Executive", "Other",
    },
    "Postgraduate": {
        "Data Analyst", "Branch Operations Executive", "Customer Success Associate",
        "Business Development Associate", "Other",
    },
    "Skilled postgraduate": {
        "Software Engineer", "Data Analyst", "Branch Operations Executive",
        "Customer Success Associate", "Quality Assurance Executive",
        "Business Development Associate", "Other",
    },
    "Diploma / Other": {
        "Customer Success Associate", "Quality Assurance Executive", "Other",
    },
}
QUALIFICATIONS = set(ROLES_BY_QUALIFICATION)
ROLES = set().union(*ROLES_BY_QUALIFICATION.values())
ENQUIRY_CATEGORIES = QUALIFICATIONS | {"Employer / recruiter", "Not sure"}
EXPERIENCE_LEVELS = {
    "Fresher", "Less than 1 year", "1–3 years", "3–5 years", "5+ years",
}


def email_notifications_configured() -> bool:
    required = ("SMTP_HOST", "SMTP_PORT", "SMTP_USERNAME", "SMTP_PASSWORD", "SMTP_FROM_EMAIL", "ADMIN_EMAIL")
    return all(os.environ.get(name, "").strip() for name in required)


def _email_header(value: str, limit: int = 120) -> str:
    return " ".join(value.splitlines())[:limit]


def requested_role(fields: dict[str, str]) -> str:
    if fields.get("role") == "Other":
        return fields.get("otherRole", "").strip()
    return fields.get("role", "").strip()


def build_application_emails(application_id: str, fields: dict[str, str], resume, photo):
    sender = os.environ["SMTP_FROM_EMAIL"].strip()
    admin_email = os.environ["ADMIN_EMAIL"].strip()
    candidate_email = fields["email"].strip()
    candidate_name = _email_header(fields["fullName"])
    role = _email_header(requested_role(fields))

    admin_message = EmailMessage()
    admin_message["Subject"] = f"New application: {role} - {candidate_name}"
    admin_message["From"] = sender
    admin_message["To"] = admin_email
    admin_message["Reply-To"] = candidate_email
    admin_message.set_content(
        "A new application was submitted.\n\n"
        f"Application ID: {application_id}\n"
        f"Name: {fields['fullName']}\n"
        f"Email: {candidate_email}\n"
        f"Phone: {fields['phone']}\n"
        f"Location: {fields['location']}\n"
        f"Qualification: {fields['qualification']}\n"
        f"Experience: {fields['experience']}\n"
        f"Role: {requested_role(fields)}\n\n"
        f"Candidate message:\n{fields.get('message', '').strip() or 'Not provided'}\n"
    )
    filename, content_type, content = resume
    maintype, subtype = content_type.split("/", 1)
    admin_message.add_attachment(
        content,
        maintype=maintype,
        subtype=subtype,
        filename=Path(filename).name,
    )
    photo_filename, photo_content_type, photo_content = photo
    photo_maintype, photo_subtype = photo_content_type.split("/", 1)
    admin_message.add_attachment(
        photo_content,
        maintype=photo_maintype,
        subtype=photo_subtype,
        filename=Path(photo_filename).name,
    )

    candidate_message = EmailMessage()
    candidate_message["Subject"] = f"Application received - {application_id}"
    candidate_message["From"] = sender
    candidate_message["To"] = candidate_email
    candidate_message["Reply-To"] = admin_email
    candidate_message.set_content(
        f"Hello {fields['fullName']},\n\n"
        "Thank you for applying through AION Technology. We have received your application "
        f"for {requested_role(fields)}.\n\n"
        f"Application reference: {application_id}\n\n"
        "Our team will review your profile and contact you with the next steps.\n\n"
        "AION Technology\n"
    )
    return admin_message, candidate_message


def send_application_emails(application_id: str, fields: dict[str, str], resume, photo) -> None:
    if not email_notifications_configured():
        raise RuntimeError("SMTP email notifications are not configured.")
    try:
        port = int(os.environ["SMTP_PORT"])
    except ValueError as exc:
        raise RuntimeError("SMTP_PORT must be a number.") from exc

    host = os.environ["SMTP_HOST"].strip()
    username = os.environ["SMTP_USERNAME"].strip()
    password = os.environ["SMTP_PASSWORD"]
    use_tls = os.environ.get("SMTP_USE_TLS", "true").strip().lower() in {"1", "true", "yes", "on"}
    context = ssl.create_default_context()
    messages = build_application_emails(application_id, fields, resume, photo)

    if port == 465:
        client = smtplib.SMTP_SSL(host, port, timeout=20, context=context)
    else:
        client = smtplib.SMTP(host, port, timeout=20)
    with client:
        client.ehlo()
        if use_tls and port != 465:
            client.starttls(context=context)
            client.ehlo()
        client.login(username, password)
        for message in messages:
            client.send_message(message)


def initialize_database() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
    PHOTO_DIR.mkdir(parents=True, exist_ok=True)
    with sqlite3.connect(DATABASE) as connection:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS applications (
                id TEXT PRIMARY KEY,
                role TEXT NOT NULL,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                location TEXT NOT NULL,
                qualification TEXT NOT NULL,
                experience TEXT NOT NULL,
                message TEXT NOT NULL DEFAULT '',
                resume_path TEXT NOT NULL,
                resume_original_name TEXT NOT NULL,
                photo_path TEXT NOT NULL DEFAULT '',
                photo_original_name TEXT NOT NULL DEFAULT '',
                submitted_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new',
                UNIQUE(email, role)
            )
            """
        )
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS enquiries (
                id TEXT PRIMARY KEY,
                full_name TEXT NOT NULL,
                email TEXT NOT NULL,
                phone TEXT NOT NULL,
                enquiry_type TEXT NOT NULL,
                qualification TEXT NOT NULL DEFAULT '',
                message TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new'
            )
            """
        )
        application_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(applications)")
        }
        if "photo_path" not in application_columns:
            connection.execute(
                "ALTER TABLE applications ADD COLUMN photo_path TEXT NOT NULL DEFAULT ''"
            )
        if "photo_original_name" not in application_columns:
            connection.execute(
                "ALTER TABLE applications ADD COLUMN photo_original_name TEXT NOT NULL DEFAULT ''"
            )
        enquiry_columns = {
            row[1] for row in connection.execute("PRAGMA table_info(enquiries)")
        }
        if "qualification" not in enquiry_columns:
            connection.execute(
                "ALTER TABLE enquiries ADD COLUMN qualification TEXT NOT NULL DEFAULT ''"
            )


class ApplicationHandler(SimpleHTTPRequestHandler):
    server_version = "AionCareer/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:
        """Run safely without an attached console or stderr stream."""
        return

    def end_headers(self) -> None:
        """Apply baseline security headers to API and static responses."""
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("X-Frame-Options", "DENY")
        self.send_header("Referrer-Policy", "strict-origin-when-cross-origin")
        self.send_header("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
        self.send_header("Cross-Origin-Opener-Policy", "same-origin")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; script-src 'self'; "
            "style-src 'self' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; img-src 'self' data:; "
            "connect-src 'self'; object-src 'none'; base-uri 'self'; "
            "form-action 'self'; frame-ancestors 'none'",
        )
        if self._request_path().startswith("/assets/"):
            self.send_header("Cache-Control", "public, max-age=86400")
        super().end_headers()

    def _request_path(self) -> str:
        """Return a decoded, normalized URL path for allowlist checks."""
        path = unquote(urlsplit(self.path).path)
        return posixpath.normpath("/" + path.lstrip("/"))

    def _is_public_path(self) -> bool:
        path = self._request_path()
        return path in {"/", "/index.html", "/privacy.html", "/terms.html"} or path.startswith("/assets/")

    def _serve_public_file(self) -> None:
        if not self._is_public_path():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        super().do_GET()

    def do_GET(self) -> None:
        if self._request_path() == "/api/health":
            self.send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "emailNotifications": "configured" if email_notifications_configured() else "not_configured",
                },
            )
            return
        self._serve_public_file()

    def do_HEAD(self) -> None:
        if not self._is_public_path():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        super().do_HEAD()

    def do_POST(self) -> None:
        endpoint = urlsplit(self.path).path
        if endpoint == "/api/applications":
            self.create_application()
            return
        if endpoint == "/api/enquiries":
            self.create_enquiry()
            return
        self.send_json(HTTPStatus.NOT_FOUND, {"error": "Endpoint not found."})

    def create_enquiry(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0 or length > 32 * 1024:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid enquiry."})
            return
        try:
            fields = json.loads(self.rfile.read(length))
        except (json.JSONDecodeError, UnicodeDecodeError):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Invalid enquiry data."})
            return

        required = ("fullName", "email", "phone", "enquiryType", "qualification", "message")
        if any(not isinstance(fields.get(name), str) or not fields[name].strip() for name in required):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Please complete all required fields."})
            return
        fields = {key: value.strip() for key, value in fields.items() if isinstance(value, str)}
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", fields["email"]):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Please enter a valid email address."})
            return
        if not re.fullmatch(r"[0-9+() -]{10,18}", fields["phone"]):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Please enter a valid phone number."})
            return
        enquiry_types = {"Job opportunities", "Eligibility", "Application status", "Employer enquiry", "Other"}
        if (
            fields["enquiryType"] not in enquiry_types
            or fields["qualification"] not in ENQUIRY_CATEGORIES
            or len(fields["fullName"]) > 100
            or len(fields["message"]) > 2000
        ):
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Please check your enquiry details."})
            return

        enquiry_id = f"ENQ-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"
        with sqlite3.connect(DATABASE) as connection:
            connection.execute(
                """INSERT INTO enquiries
                (id, full_name, email, phone, enquiry_type, qualification, message, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    enquiry_id, fields["fullName"], fields["email"].lower(), fields["phone"],
                    fields["enquiryType"], fields["qualification"], fields["message"],
                    datetime.now(timezone.utc).isoformat(),
                ),
            )
        self.send_json(HTTPStatus.CREATED, {"message": "Enquiry received.", "enquiryId": enquiry_id})

    def create_application(self) -> None:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        content_type = self.headers.get("Content-Type", "")
        if length <= 0 or length > MAX_REQUEST_SIZE:
            self.send_json(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, {"error": "Application is too large."})
            return
        if not content_type.lower().startswith("multipart/form-data;"):
            self.send_json(HTTPStatus.UNSUPPORTED_MEDIA_TYPE, {"error": "Form upload required."})
            return

        body = self.rfile.read(length)
        message = BytesParser(policy=default).parsebytes(
            f"Content-Type: {content_type}\r\nMIME-Version: 1.0\r\n\r\n".encode() + body
        )
        fields: dict[str, str] = {}
        resume = None
        photo = None
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            filename = part.get_filename()
            if name == "resume" and filename:
                resume = (Path(filename).name, part.get_content_type(), part.get_payload(decode=True) or b"")
            elif name == "photo" and filename:
                photo = (Path(filename).name, part.get_content_type(), part.get_payload(decode=True) or b"")
            elif name:
                fields[name] = (part.get_content() or "").strip()

        error = self.validate(fields, resume, photo)
        if error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": error})
            return

        application_id = f"AION-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"
        original_name, _, resume_bytes = resume
        extension = Path(original_name).suffix.lower()
        resume_path = UPLOAD_DIR / f"{application_id}{extension}"
        photo_original_name, _, photo_bytes = photo
        photo_extension = Path(photo_original_name).suffix.lower()
        photo_path = PHOTO_DIR / f"{application_id}{photo_extension}"
        resume_path.write_bytes(resume_bytes)
        photo_path.write_bytes(photo_bytes)
        role = requested_role(fields)
        try:
            with sqlite3.connect(DATABASE) as connection:
                connection.execute(
                    """INSERT INTO applications
                    (id, role, full_name, email, phone, location, qualification,
                     experience, message, resume_path, resume_original_name, photo_path,
                     photo_original_name, submitted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        application_id, role, fields["fullName"],
                        fields["email"].lower(), fields["phone"], fields["location"],
                        fields["qualification"], fields["experience"], fields.get("message", ""),
                        str(resume_path.relative_to(ROOT)), original_name,
                        str(photo_path.relative_to(ROOT)), photo_original_name,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
        except sqlite3.IntegrityError:
            resume_path.unlink(missing_ok=True)
            photo_path.unlink(missing_ok=True)
            self.send_json(
                HTTPStatus.CONFLICT,
                {"error": "An application for this role already exists for that email address."},
            )
            return

        email_notification_sent = False
        try:
            send_application_emails(application_id, fields, resume, photo)
            email_notification_sent = True
        except Exception as exc:
            print(
                f"Email notification failed for {application_id}: {type(exc).__name__}: {exc}",
                flush=True,
            )

        self.send_json(
            HTTPStatus.CREATED,
            {
                "message": "Application received.",
                "applicationId": application_id,
                "emailNotificationSent": email_notification_sent,
            },
        )

    @staticmethod
    def validate(fields, resume, photo) -> str | None:
        required = ("role", "fullName", "email", "phone", "location", "qualification", "experience")
        if any(not fields.get(name) for name in required):
            return "Please complete all required fields."
        if fields.get("consent") != "on":
            return "Consent is required to submit an application."
        if fields["qualification"] not in QUALIFICATIONS or fields["experience"] not in EXPERIENCE_LEVELS:
            return "Please select valid qualification and experience values."
        if fields["role"] not in ROLES:
            return "Please select a valid open role."
        if fields["role"] not in ROLES_BY_QUALIFICATION[fields["qualification"]]:
            return "Please select a role related to your qualification."
        if fields["role"] == "Other" and not fields.get("otherRole", "").strip():
            return "Please enter the role you are looking for."
        if len(fields.get("otherRole", "")) > 100:
            return "The requested role must be 100 characters or fewer."
        if len(fields["fullName"]) > 100 or len(fields["location"]) > 100 or len(fields.get("message", "")) > 2000:
            return "One or more fields are too long."
        if not re.fullmatch(r"[^\s@]+@[^\s@]+\.[^\s@]+", fields["email"]):
            return "Please enter a valid email address."
        if not re.fullmatch(r"[0-9+() -]{10,18}", fields["phone"]):
            return "Please enter a valid phone number."
        if not resume:
            return "Please attach your résumé."
        filename, content_type, content = resume
        extension = Path(filename).suffix.lower()
        if extension not in ALLOWED_RESUMES or content_type not in ALLOWED_RESUMES[extension]:
            return "Résumé must be a PDF, DOC or DOCX file."
        if not content or len(content) > MAX_RESUME_SIZE:
            return "Résumé must be smaller than 5 MB."
        if not photo:
            return "Please attach your photo."
        photo_filename, photo_content_type, photo_content = photo
        photo_extension = Path(photo_filename).suffix.lower()
        if photo_extension not in ALLOWED_PHOTOS or photo_content_type not in ALLOWED_PHOTOS[photo_extension]:
            return "Photo must be a JPG, PNG or WebP file."
        if not photo_content or len(photo_content) > MAX_PHOTO_SIZE:
            return "Photo must be smaller than 3 MB."
        return None

    def send_json(self, status: HTTPStatus, payload: dict) -> None:
        encoded = json.dumps(payload).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(encoded)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(encoded)


if __name__ == "__main__":
    initialize_database()
    host = os.environ.get("HOST", "0.0.0.0")
    port = int(os.environ.get("PORT", "8000"))
    server = ThreadingHTTPServer((host, port), ApplicationHandler)
    print(f"Aion Career is running at http://{host}:{port}", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.server_close()
