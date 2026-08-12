import unittest

from server import ApplicationHandler, ROLES_BY_QUALIFICATION


class ApplicationRoleValidationTests(unittest.TestCase):
    def setUp(self):
        self.fields = {
            "role": "Branch Operations Executive",
            "fullName": "Test Candidate",
            "email": "candidate@example.com",
            "phone": "+91 9876543210",
            "location": "Bengaluru",
            "qualification": "Graduate",
            "experience": "Fresher",
            "consent": "on",
        }
        self.resume = ("resume.pdf", "application/pdf", b"%PDF-1.4 test")
        self.photo = ("photo.jpg", "image/jpeg", b"JPEG test")

    def validate(self, qualification, role):
        fields = {**self.fields, "qualification": qualification, "role": role}
        return ApplicationHandler.validate(fields, self.resume, self.photo)

    def test_general_graduate_accepts_related_business_role(self):
        self.assertIsNone(self.validate("Graduate", "Branch Operations Executive"))

    def test_general_graduate_rejects_technical_role(self):
        self.assertEqual(
            self.validate("Graduate", "Software Engineer"),
            "Please select a role related to your qualification.",
        )

    def test_skilled_graduate_accepts_technical_role(self):
        self.assertIsNone(self.validate("Skilled graduate", "Software Engineer"))

    def test_other_role_is_available_for_every_qualification(self):
        for qualification in ROLES_BY_QUALIFICATION:
            with self.subTest(qualification=qualification):
                fields = {
                    **self.fields,
                    "qualification": qualification,
                    "role": "Other",
                    "otherRole": "Operations Coordinator",
                }
                self.assertIsNone(ApplicationHandler.validate(fields, self.resume, self.photo))

    def test_other_role_requires_a_role_name(self):
        self.assertEqual(
            self.validate("Graduate", "Other"),
            "Please enter the role you are looking for.",
        )

    def test_general_application_does_not_require_a_role(self):
        fields = {key: value for key, value in self.fields.items() if key != "role"}
        self.assertIsNone(ApplicationHandler.validate(fields, self.resume, self.photo))


if __name__ == "__main__":
    unittest.main()
