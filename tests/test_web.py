import unittest

from app import create_app


class WebIndexTests(unittest.TestCase):
    def setUp(self):
        self.client = create_app().test_client()

    def test_index_returns_form(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"Calculate DC Bias", response.data)
        self.assertIn(b'name="vcc"', response.data)
        self.assertIn(b'name="r1"', response.data)


if __name__ == "__main__":
    unittest.main()
