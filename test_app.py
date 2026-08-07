import unittest
import os
import tempfile
import sqlite3
from flask import session
from app import app
from database import get_db_connection, init_db

class EarthXDesignsTestCase(unittest.TestCase):

    def setUp(self):
        # Configure app for testing
        app.config['TESTING'] = True
        app.config['WTF_CSRF_ENABLED'] = False
        self.app = app.test_client()
        
        # Initialize the database (this will seed it if it's empty)
        init_db()

    def test_public_pages(self):
        """Test that all public pages return a 200 OK status code."""
        pages = ['/', '/about', '/services', '/portfolio', '/testimonials', '/blog', '/contact', '/admin/login']
        for page in pages:
            response = self.app.get(page)
            self.assertEqual(response.status_code, 200, f"Page {page} failed to load with status code {response.status_code}")

    def test_admin_dashboard_requires_login(self):
        """Test that access to the admin dashboard is redirected when not logged in."""
        response = self.app.get('/admin')
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/admin/login' in response.headers['Location'])

    def test_contact_form_submission(self):
        """Test that submitting the contact form works and stores an entry in the database."""
        # Query count before post
        conn = get_db_connection()
        before_count = conn.execute('SELECT COUNT(*) FROM contact_inquiries').fetchone()[0]
        conn.close()

        # Submit inquiry
        payload = {
            'name': 'Test User',
            'company_name': 'Test Company LLC',
            'email': 'testuser@example.com',
            'phone': '1234567890',
            'project_type': 'Residential Solar Design',
            'message': 'This is a test message to verify form storage.'
        }
        response = self.app.post('/contact', data=payload, follow_redirects=True)
        self.assertEqual(response.status_code, 200)

        # Check DB count has increased
        conn = get_db_connection()
        after_count = conn.execute('SELECT COUNT(*) FROM contact_inquiries').fetchone()[0]
        conn.close()
        
        self.assertEqual(after_count, before_count + 1)

    def test_admin_login_success(self):
        """Test that login works with seeded admin credentials."""
        payload = {
            'email': 'sales.earthxd@gmail.com',
            'password': 'EarthX@123'
        }
        response = self.app.post('/admin/login', data=payload)
        # Should redirect to admin dashboard
        self.assertEqual(response.status_code, 302)
        self.assertTrue('/admin' in response.headers['Location'])

if __name__ == '__main__':
    unittest.main()
