import unittest

from app import app, greeting


class TestApp(unittest.TestCase):
    def test_greeting(self):
        self.assertEqual(greeting(), "Hello, CSK!")

    def test_index(self):
        response = app.test_client().get("/")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "Hello, CSK!\n")


if __name__ == "__main__":
    unittest.main()
