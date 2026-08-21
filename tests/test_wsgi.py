import io
import unittest

from passenger_wsgi import application


def request(path="/", method="GET", body=b"", content_type=""):
    captured = {}

    def start_response(status, headers):
        captured["status"] = status
        captured["headers"] = dict(headers)

    environ = {
        "PATH_INFO": path,
        "REQUEST_METHOD": method,
        "CONTENT_LENGTH": str(len(body)),
        "CONTENT_TYPE": content_type,
        "wsgi.input": io.BytesIO(body),
    }
    captured["body"] = b"".join(application(environ, start_response))
    return captured


class PassengerWsgiTests(unittest.TestCase):
    def test_homepage_is_served(self):
        response = request()
        self.assertTrue(response["status"].startswith("200 "))
        self.assertIn("text/html", response["headers"]["Content-Type"])
        self.assertIn(b"AION", response["body"])

    def test_health_endpoint_is_available(self):
        response = request("/api/health")
        self.assertTrue(response["status"].startswith("200 "))
        self.assertIn(b'"status": "ok"', response["body"])

    def test_head_has_the_get_content_length_but_no_body(self):
        get_response = request("/privacy.html")
        head_response = request("/privacy.html", method="HEAD")
        self.assertEqual(head_response["headers"]["Content-Length"], str(len(get_response["body"])))
        self.assertEqual(head_response["body"], b"")

    def test_private_and_traversal_paths_are_not_served(self):
        for path in ("/server.py", "/assets/../../.env"):
            with self.subTest(path=path):
                self.assertTrue(request(path)["status"].startswith("404 "))

    def test_invalid_enquiry_json_is_rejected(self):
        response = request(
            "/api/enquiries",
            method="POST",
            body=b"not-json",
            content_type="application/json",
        )
        self.assertTrue(response["status"].startswith("400 "))


if __name__ == "__main__":
    unittest.main()
