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

    def test_cross_project_isolation_and_no_cache_headers(self):
        """Test that updating one project never affects another project, and API responses have no-cache headers."""
        import io
        self.app.post('/admin/login', data={'email': 'sales.earthxd@gmail.com', 'password': 'EarthX@123'})

        # 1. Verify API endpoints return no-store, no-cache headers
        res_api = self.app.get('/api/projects')
        self.assertIn('no-store', res_api.headers.get('Cache-Control', ''))
        self.assertIn('no-cache', res_api.headers.get('Cache-Control', ''))

        # 2. Create Project A ("3D Pre Sales")
        p_a = {
            'title': '3D Pre Sales Design Concept',
            'category_id': '1',
            'capacity': '100 kWp',
            'location': 'Mumbai, India',
            'client_name': 'PreSales Client',
            'description': 'Preliminary 3D solar model.',
            'services_delivered': '3D Modeling, Shadow Analysis',
            'completion_date': '2026-09-01',
            'status': 'published',
            'featured_image': (io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'), 'presales_feat.png')
        }
        res_a = self.app.post('/api/projects', data=p_a, content_type='multipart/form-data')
        id_a = res_a.get_json()['id']

        # 3. Create Project B ("CEIG Drawings")
        p_b = {
            'title': 'CEIG Drawing Package Electrical',
            'category_id': '2',
            'capacity': '500 kWp',
            'location': 'Ahmedabad, India',
            'client_name': 'CEIG Client',
            'description': 'Statutory drawings package.',
            'services_delivered': 'CEIG Approval, SLD',
            'completion_date': '2026-09-02',
            'status': 'published',
            'featured_image': (io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'), 'ceig_feat.png')
        }
        res_b = self.app.post('/api/projects', data=p_b, content_type='multipart/form-data')
        id_b = res_b.get_json()['id']

        # 4. Upload gallery drawing ONLY to Project A
        gal_a = {
            'gallery_images': [
                (io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'), 'presales_drawing.png')
            ]
        }
        res_gal_a = self.app.post(f'/api/projects/{id_a}/gallery', data=gal_a, content_type='multipart/form-data')
        self.assertEqual(res_gal_a.status_code, 201)

        # 5. Verify Project A has 1 gallery drawing and Project B has 0
        get_a = self.app.get(f'/api/projects/{id_a}').get_json()
        get_b = self.app.get(f'/api/projects/{id_b}').get_json()
        self.assertEqual(len(get_a['gallery']), 1)
        self.assertEqual(len(get_b['gallery']), 0)
        self.assertNotEqual(get_a['featured_image'], get_b['featured_image'])

        # 6. Clean up test projects
        self.app.delete(f'/api/projects/{id_a}')
        self.app.delete(f'/api/projects/{id_b}')

    def test_home_who_we_are_image_settings(self):
        """Test the Admin CRM controls to add, replace, and remove the Home page Who We Are featured image."""
        import io
        # 1. Login
        self.app.post('/admin/login', data={'email': 'sales.earthxd@gmail.com', 'password': 'EarthX@123'})

        # 2. GET current home settings
        res = self.app.get('/api/admin/home-settings')
        self.assertEqual(res.status_code, 200)
        data = res.get_json()
        self.assertTrue(data.get('success'))

        # 3. Replace image with a preset (Ground Mount)
        res_preset = self.app.post('/api/admin/home-settings', data={'preset_image': '/uploads/ground_mount_featured.png'})
        self.assertEqual(res_preset.status_code, 200)
        self.assertEqual(res_preset.get_json()['who_we_are_image'], '/uploads/ground_mount_featured.png')

        # Check Home page displays updated ground mount image
        home_res = self.app.get('/')
        self.assertEqual(home_res.status_code, 200)
        self.assertIn(b'/uploads/ground_mount_featured.png', home_res.data)

        # 4. Remove image (empty state)
        res_remove = self.app.post('/api/admin/home-settings', data={'remove_image': '1'})
        self.assertEqual(res_remove.status_code, 200)
        self.assertEqual(res_remove.get_json()['who_we_are_image'], '')

        # Check Home page handles removed image gracefully (full width text, no img tag for who we are)
        home_res2 = self.app.get('/')
        self.assertEqual(home_res2.status_code, 200)
        self.assertIn(b'about-home-no-image', home_res2.data)
        self.assertNotIn(b'about-home-image-col', home_res2.data)

        # 5. Upload / Replace with custom file
        fake_img = (io.BytesIO(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'), 'custom_who_we_are.png')
        res_upload = self.app.post('/api/admin/home-settings', data={'who_we_are_image': fake_img}, content_type='multipart/form-data')
        self.assertEqual(res_upload.status_code, 200)
        uploaded_path = res_upload.get_json()['who_we_are_image']
        self.assertTrue('home_who_we_are' in uploaded_path)

        # Check Home page displays new uploaded image
        home_res3 = self.app.get('/')
        self.assertEqual(home_res3.status_code, 200)
        self.assertIn(uploaded_path.encode('utf-8'), home_res3.data)

        # 6. Reset to default (Commercial Solar)
        res_reset = self.app.post('/api/admin/home-settings', data={'preset_image': '/uploads/commercial_solar_featured.png'})
        self.assertEqual(res_reset.status_code, 200)
        self.assertEqual(res_reset.get_json()['who_we_are_image'], '/uploads/commercial_solar_featured.png')

        home_res4 = self.app.get('/')
        self.assertEqual(home_res4.status_code, 200)
        self.assertIn(b'/uploads/commercial_solar_featured.png', home_res4.data)

if __name__ == '__main__':
    unittest.main()
