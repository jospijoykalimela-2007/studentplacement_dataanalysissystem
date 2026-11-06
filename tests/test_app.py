import unittest
from unittest.mock import patch

from app import app


class PlacementDashboardTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, WTF_CSRF_ENABLED=False)
        self.client = app.test_client()

    @patch("app.database_available", return_value=False)
    def test_dashboard_uses_demo_cohort_and_hides_identifiers(self, _database_available):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertIn(b"50.0%", response.data)
        self.assertIn(b"Preview data", response.data)
        self.assertNotIn(b"CS-26", response.data)
        self.assertIn(b"eligible students", response.data)

    def test_student_management_requires_staff_login(self):
        response = self.client.get("/students")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    def test_placement_management_requires_staff_login(self):
        response = self.client.get("/placements")

        self.assertEqual(response.status_code, 302)
        self.assertIn("/login", response.location)

    @patch("app.database_available", return_value=False)
    def test_staff_pages_render_without_a_database(self, _database_available):
        with self.client.session_transaction() as browser_session:
            browser_session["authenticated"] = True

        student_page = self.client.get("/students")
        placement_page = self.client.get("/placements")

        self.assertEqual(student_page.status_code, 200)
        self.assertIn(b"Add a student", student_page.data)
        self.assertEqual(placement_page.status_code, 200)
        self.assertIn(b"Record an outcome", placement_page.data)


if __name__ == "__main__":
    unittest.main()