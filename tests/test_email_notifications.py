import os
import unittest
from unittest.mock import patch

from server import build_application_emails, email_notifications_configured, send_application_emails


class ApplicationEmailTests(unittest.TestCase):
    def setUp(self):
        self.settings = {
            "SMTP_HOST": "smtp.example.com",
            "SMTP_PORT": "587",
            "SMTP_USERNAME": "sender@example.com",
            "SMTP_PASSWORD": "app-password",
            "SMTP_FROM_EMAIL": "sender@example.com",
            "SMTP_USE_TLS": "true",
            "ADMIN_EMAIL": "careers@example.com",
        }
        self.fields = {
            "role": "Branch Operations Executive",
            "fullName": "Test Candidate",
            "email": "candidate@example.com",
            "phone": "+91 9876543210",
            "location": "Bengaluru",
            "qualification": "Graduate",
            "experience": "Fresher",
            "message": "Ready to join.",
        }
        self.resume = ("resume.pdf", "application/pdf", b"%PDF-1.4 test")
        self.photo = ("photo.jpg", "image/jpeg", b"JPEG test")

    def test_configuration_requires_every_setting(self):
        with patch.dict(os.environ, self.settings, clear=False):
            self.assertTrue(email_notifications_configured())
            os.environ["SMTP_PASSWORD"] = ""
            self.assertFalse(email_notifications_configured())

    def test_configuration_accepts_godaddy_relay_without_login(self):
        settings = {
            **self.settings,
            "SMTP_HOST": "localhost",
            "SMTP_PORT": "25",
            "SMTP_USERNAME": "",
            "SMTP_PASSWORD": "",
            "SMTP_USE_TLS": "false",
        }
        with patch.dict(os.environ, settings, clear=False):
            self.assertTrue(email_notifications_configured())

    def test_general_application_email_does_not_reference_a_missing_role(self):
        fields = {key: value for key, value in self.fields.items() if key != "role"}
        with patch.dict(os.environ, self.settings, clear=False):
            admin_message, candidate_message = build_application_emails(
                "AION-TEST-002", fields, self.resume, self.photo
            )

        self.assertIn("Graduate", str(admin_message["Subject"]))
        self.assertIn("received your application.", candidate_message.get_content())
        self.assertNotIn("General application", candidate_message.get_content())

    @patch("server.smtplib.SMTP")
    def test_sends_admin_notification_and_candidate_confirmation(self, smtp):
        client = smtp.return_value
        with patch.dict(os.environ, self.settings, clear=False):
            send_application_emails("AION-TEST-001", self.fields, self.resume, self.photo)

        smtp.assert_called_once_with("smtp.example.com", 587, timeout=20)
        client.starttls.assert_called_once()
        client.login.assert_called_once_with("sender@example.com", "app-password")
        self.assertEqual(client.send_message.call_count, 2)

        admin_message = client.send_message.call_args_list[0].args[0]
        candidate_message = client.send_message.call_args_list[1].args[0]
        self.assertEqual(str(admin_message["To"]), "careers@example.com")
        self.assertEqual(str(admin_message["Reply-To"]), "candidate@example.com")
        self.assertEqual(len(list(admin_message.iter_attachments())), 2)
        self.assertEqual(str(candidate_message["To"]), "candidate@example.com")
        self.assertIn("AION-TEST-001", candidate_message.get_content())

    @patch("server.smtplib.SMTP")
    def test_godaddy_relay_does_not_attempt_smtp_login(self, smtp):
        client = smtp.return_value
        settings = {
            **self.settings,
            "SMTP_HOST": "localhost",
            "SMTP_PORT": "25",
            "SMTP_USERNAME": "",
            "SMTP_PASSWORD": "",
            "SMTP_USE_TLS": "false",
        }
        with patch.dict(os.environ, settings, clear=False):
            send_application_emails("AION-TEST-003", self.fields, self.resume, self.photo)

        smtp.assert_called_once_with("localhost", 25, timeout=20)
        client.starttls.assert_not_called()
        client.login.assert_not_called()
        self.assertEqual(client.send_message.call_count, 2)


if __name__ == "__main__":
    unittest.main()
