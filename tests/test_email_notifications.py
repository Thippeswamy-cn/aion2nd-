import os
import unittest
from unittest.mock import patch

from server import email_notifications_configured, send_application_emails


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


if __name__ == "__main__":
    unittest.main()
