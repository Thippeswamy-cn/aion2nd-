"""Aion Career development server and job application API."""

from __future__ import annotations

import json
import os
import re
import secrets
import sqlite3
from datetime import datetime, timezone
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parent
DATA_DIR = ROOT / "data"
UPLOAD_DIR = DATA_DIR / "resumes"
DATABASE = DATA_DIR / "applications.db"
MAX_REQUEST_SIZE = 6 * 1024 * 1024
MAX_RESUME_SIZE = 5 * 1024 * 1024
ALLOWED_RESUMES = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".doc": {"application/msword", "application/octet-stream"},
    ".docx": {
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "application/zip",
        "application/octet-stream",
    },
}
ROLES = {
    "Software Engineer",
    "Data Analyst",
    "Branch Operations Executive",
    "Customer Success Associate",
    "Quality Assurance Executive",
    "Business Development Associate",
}
QUALIFICATIONS = {
    "Graduate", "Skilled graduate", "Postgraduate",
    "Skilled postgraduate", "Diploma / Other",
}
EXPERIENCE_LEVELS = {
    "Fresher", "Less than 1 year", "1–3 years", "3–5 years", "5+ years",
}


def initialize_database() -> None:
    UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
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
                message TEXT NOT NULL,
                submitted_at TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'new'
            )
            """
        )


class ApplicationHandler(SimpleHTTPRequestHandler):
    server_version = "AionCareer/1.0"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def log_message(self, format: str, *args) -> None:
        """Run safely without an attached console or stderr stream."""
        return

    def do_GET(self) -> None:
        if urlsplit(self.path).path == "/api/health":
            self.send_json(HTTPStatus.OK, {"status": "ok"})
            return
        super().do_GET()

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

        required = ("fullName", "email", "phone", "enquiryType", "message")
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
        if fields["enquiryType"] not in enquiry_types or len(fields["fullName"]) > 100 or len(fields["message"]) > 2000:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": "Please check your enquiry details."})
            return

        enquiry_id = f"ENQ-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"
        with sqlite3.connect(DATABASE) as connection:
            connection.execute(
                """INSERT INTO enquiries
                (id, full_name, email, phone, enquiry_type, message, submitted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    enquiry_id, fields["fullName"], fields["email"].lower(), fields["phone"],
                    fields["enquiryType"], fields["message"], datetime.now(timezone.utc).isoformat(),
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
        for part in message.iter_parts():
            name = part.get_param("name", header="content-disposition")
            filename = part.get_filename()
            if name == "resume" and filename:
                resume = (Path(filename).name, part.get_content_type(), part.get_payload(decode=True) or b"")
            elif name:
                fields[name] = (part.get_content() or "").strip()

        error = self.validate(fields, resume)
        if error:
            self.send_json(HTTPStatus.BAD_REQUEST, {"error": error})
            return

        application_id = f"AION-{datetime.now(timezone.utc):%Y%m%d}-{secrets.token_hex(4).upper()}"
        original_name, _, resume_bytes = resume
        extension = Path(original_name).suffix.lower()
        resume_path = UPLOAD_DIR / f"{application_id}{extension}"
        resume_path.write_bytes(resume_bytes)
        try:
            with sqlite3.connect(DATABASE) as connection:
                connection.execute(
                    """INSERT INTO applications
                    (id, role, full_name, email, phone, location, qualification,
                     experience, message, resume_path, resume_original_name, submitted_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        application_id, fields["role"], fields["fullName"],
                        fields["email"].lower(), fields["phone"], fields["location"],
                        fields["qualification"], fields["experience"], fields.get("message", ""),
                        str(resume_path.relative_to(ROOT)), original_name,
                        datetime.now(timezone.utc).isoformat(),
                    ),
                )
        except sqlite3.IntegrityError:
            resume_path.unlink(missing_ok=True)
            self.send_json(
                HTTPStatus.CONFLICT,
                {"error": "An application for this role already exists for that email address."},
            )
            return

        self.send_json(
            HTTPStatus.CREATED,
            {"message": "Application received.", "applicationId": application_id},
        )

    @staticmethod
    def validate(fields, resume) -> str | None:
        required = ("role", "fullName", "email", "phone", "location", "qualification", "experience")
        if any(not fields.get(name) for name in required):
            return "Please complete all required fields."
        if fields.get("consent") != "on":
            return "Consent is required to submit an application."
        if fields["role"] not in ROLES:
            return "Please select a valid open role."
        if fields["qualification"] not in QUALIFICATIONS or fields["experience"] not in EXPERIENCE_LEVELS:
            return "Please select valid qualification and experience values."
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
