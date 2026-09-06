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
        """Test that all public pages return a 200 OK status code and include mobile navigation components."""
        pages = [
            '/', 
            '/about', 
            '/services', 
            '/services/pre-sales-design',
            '/portfolio', 
            '/portfolio/1',
            '/testimonials', 
            '/blog', 
            '/contact', 
            '/admin/login'
        ]
        for page in pages:
            response = self.app.get(page)
            self.assertEqual(response.status_code, 200, f"Page {page} failed to load with status code {response.status_code}")
            if page != '/admin/login':
                self.assertIn(b'id="nav-backdrop"', response.data, f"nav-backdrop missing on {page}")
                self.assertIn(b'id="nav-toggle"', response.data, f"nav-toggle missing on {page}")

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

    def test_project_crud_and_gallery_isolation(self):
        """Test project creation, edit, and dedicated gallery upload isolation."""
        import io
        # 1. Login
        self.app.post('/admin/login', data={'email': 'sales.earthxd@gmail.com', 'password': 'EarthX@123'})

        # 2. Add Project
        add_data = {
            'title': 'Test Precision Solar Design',
            'category_id': '1',
            'capacity': '75 kWp',
            'location': 'Gujarat, India',
            'client_name': 'Solar Client Alpha',
            'description': 'Comprehensive 3D layout and shading design.',
            'services_delivered': 'CAD Design, Shading Analysis',
            'completion_date': '2026-09-01',
            'status': 'published',
            'featured_image': (io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'), 'project_alpha.png')
        }
        res_add = self.app.post('/api/projects', data=add_data, content_type='multipart/form-data')
        self.assertEqual(res_add.status_code, 201)
        proj_id = res_add.get_json()['id']

        # 3. Edit Project without new image (must preserve existing image and not touch others)
        edit_data = {
            'title': 'Test Precision Solar Design - Updated',
            'category_id': '1',
            'capacity': '80 kWp',
            'location': 'Gujarat, India',
            'client_name': 'Solar Client Alpha Updated',
            'description': 'Updated scope and specifications.',
            'services_delivered': 'CAD Design, Shading Analysis, SLD',
            'completion_date': '2026-09-01',
            'status': 'published'
        }
        res_edit = self.app.post(f'/api/projects/{proj_id}', data=edit_data, content_type='multipart/form-data')
        self.assertEqual(res_edit.status_code, 200)

        # 4. Upload drawings to dedicated gallery endpoint
        gal_data = {
            'gallery_images': [
                (io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'), 'drawing_1.png'),
                (io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'), 'drawing_2.png')
            ]
        }
        res_gal = self.app.post(f'/api/projects/{proj_id}/gallery', data=gal_data, content_type='multipart/form-data')
        self.assertEqual(res_gal.status_code, 201)

        # 5. Fetch project details and verify integrity
        res_get = self.app.get(f'/api/projects/{proj_id}')
        self.assertEqual(res_get.status_code, 200)
        proj_json = res_get.get_json()
        self.assertEqual(proj_json['title'], 'Test Precision Solar Design - Updated')
        self.assertEqual(len(proj_json['gallery']), 2)

        # 6. Test bulk deletion of gallery drawings
        img_ids = [img['id'] for img in proj_json['gallery']]
        res_bulk_del = self.app.post('/api/projects/gallery/bulk-delete', json={'image_ids': img_ids})
        self.assertEqual(res_bulk_del.status_code, 200)
        self.assertEqual(res_bulk_del.get_json()['deleted_count'], 2)

        # Verify gallery is now empty
        res_get2 = self.app.get(f'/api/projects/{proj_id}')
        self.assertEqual(len(res_get2.get_json()['gallery']), 0)

        # 7. Delete test project
        res_del = self.app.delete(f'/api/projects/{proj_id}')
        self.assertEqual(res_del.status_code, 200)

if __name__ == '__main__':
    unittest.main()
