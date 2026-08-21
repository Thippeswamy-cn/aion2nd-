"""WSGI entry point for GoDaddy Web Hosting (cPanel/Python Selector)."""

from __future__ import annotations

import json
import mimetypes
import posixpath
from email.parser import BytesParser
from email.policy import default
from http import HTTPStatus
from pathlib import Path
from urllib.parse import unquote

from server import (
    MAX_REQUEST_SIZE,
    ROOT,
    create_application_record,
    create_enquiry_record,
    email_notifications_configured,
    initialize_database,
)


SECURITY_HEADERS = [
    ("X-Content-Type-Options", "nosniff"),
    ("X-Frame-Options", "DENY"),
    ("Referrer-Policy", "strict-origin-when-cross-origin"),
    ("Permissions-Policy", "camera=(), microphone=(), geolocation=()"),
    ("Cross-Origin-Opener-Policy", "same-origin"),
    (
        "Content-Security-Policy",
        "default-src 'self'; script-src 'self'; "
        "style-src 'self' https://fonts.googleapis.com; "
        "font-src https://fonts.gstatic.com; img-src 'self' data:; "
        "connect-src 'self'; object-src 'none'; base-uri 'self'; "
        "form-action 'self'; frame-ancestors 'none'",
    ),
]


initialize_database()


def _normalized_path(environ) -> str:
    path = unquote(environ.get("PATH_INFO", "/"))
    return posixpath.normpath("/" + path.lstrip("/"))


def _respond(start_response, status: HTTPStatus, body: bytes, headers=None, method="GET"):
    response_headers = list(SECURITY_HEADERS)
    response_headers.extend(headers or [])
    response_headers.append(("Content-Length", str(len(body))))
    start_response(f"{status.value} {status.phrase}", response_headers)
    return [b"" if method == "HEAD" else body]


def _json_response(start_response, status: HTTPStatus, payload: dict, method="GET"):
    body = json.dumps(payload).encode("utf-8")
    return _respond(
        start_response,
        status,
        body,
        [
            ("Content-Type", "application/json; charset=utf-8"),
            ("Cache-Control", "no-store"),
        ],
        method,
    )


def _static_response(environ, start_response, path: str, method: str):
    if path == "/":
        relative_path = "index.html"
    elif path in {"/index.html", "/privacy.html", "/terms.html"}:
        relative_path = path.lstrip("/")
    elif path.startswith("/assets/"):
        relative_path = path.lstrip("/")
    else:
        return _json_response(start_response, HTTPStatus.NOT_FOUND, {"error": "Not found."}, method)

    file_path = (ROOT / relative_path).resolve()
    if not file_path.is_relative_to(ROOT) or not file_path.is_file():
        return _json_response(start_response, HTTPStatus.NOT_FOUND, {"error": "Not found."}, method)

    content_type, encoding = mimetypes.guess_type(file_path.name)
    headers = [
        ("Content-Type", content_type or "application/octet-stream"),
        ("Cache-Control", "public, max-age=86400" if path.startswith("/assets/") else "no-cache"),
    ]
    if encoding:
        headers.append(("Content-Encoding", encoding))
    return _respond(start_response, HTTPStatus.OK, file_path.read_bytes(), headers, method)


def _read_body(environ, maximum: int) -> bytes | None:
    try:
        length = int(environ.get("CONTENT_LENGTH") or "0")
    except ValueError:
        return None
    if length <= 0 or length > maximum:
        return None
    return environ["wsgi.input"].read(length)


def _create_enquiry(environ, start_response):
    body = _read_body(environ, 32 * 1024)
    if body is None:
        return _json_response(start_response, HTTPStatus.BAD_REQUEST, {"error": "Invalid enquiry."})
    try:
        fields = json.loads(body)
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _json_response(start_response, HTTPStatus.BAD_REQUEST, {"error": "Invalid enquiry data."})
    status, payload = create_enquiry_record(fields)
    return _json_response(start_response, status, payload)


def _create_application(environ, start_response):
    body = _read_body(environ, MAX_REQUEST_SIZE)
    if body is None:
        return _json_response(
            start_response,
            HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
            {"error": "Application is too large."},
        )

    content_type = environ.get("CONTENT_TYPE", "")
    if not content_type.lower().startswith("multipart/form-data;"):
        return _json_response(
            start_response,
            HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
            {"error": "Form upload required."},
        )

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

    status, payload = create_application_record(fields, resume, photo)
    return _json_response(start_response, status, payload)


def application(environ, start_response):
    """Serve the site and API through Passenger's WSGI interface."""
    method = environ.get("REQUEST_METHOD", "GET").upper()
    path = _normalized_path(environ)

    if method in {"GET", "HEAD"}:
        if path == "/api/health":
            return _json_response(
                start_response,
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "emailNotifications": (
                        "configured" if email_notifications_configured() else "not_configured"
                    ),
                },
                method,
            )
        return _static_response(environ, start_response, path, method)

    if method == "POST" and path == "/api/enquiries":
        return _create_enquiry(environ, start_response)
    if method == "POST" and path == "/api/applications":
        return _create_application(environ, start_response)
    return _json_response(start_response, HTTPStatus.NOT_FOUND, {"error": "Endpoint not found."})


__all__ = ["application"]
