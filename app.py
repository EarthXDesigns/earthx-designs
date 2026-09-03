import os
import csv
import io
import datetime
import secrets
import string
import sqlite3
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response, send_from_directory
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'earthx_designs_secret_2026_super_key')

import shutil

# --- DATA ARCHITECTURE ---
# Use /tmp on serverless environments like Vercel where root filesystem is read-only
IS_VERCEL = bool(os.environ.get('VERCEL'))
if IS_VERCEL:
    DATA_DIR = os.environ.get('DATA_DIR', '/tmp/data')
    os.makedirs(DATA_DIR, exist_ok=True)
    src_data_dir = os.path.join(app.root_path, 'data')
    if os.path.exists(src_data_dir):
        for item in os.listdir(src_data_dir):
            s = os.path.join(src_data_dir, item)
            d = os.path.join(DATA_DIR, item)
            if os.path.isdir(s) and not os.path.exists(d):
                try: shutil.copytree(s, d)
                except Exception: pass
            elif os.path.isfile(s) and not os.path.exists(d):
                try: shutil.copy2(s, d)
                except Exception: pass
else:
    DATA_DIR = os.environ.get('DATA_DIR', os.path.join(app.root_path, 'data'))
    os.makedirs(DATA_DIR, exist_ok=True)

app.config['UPLOAD_FOLDER'] = os.path.join(DATA_DIR, 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 100 * 1024 * 1024  # 100MB max upload size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg', 'mp4', 'webm', 'mov', 'ogg'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Auto-initialize database and seed admin user if needed
init_db(DATA_DIR)


# Helper function for allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Serve uploaded files from persistent storage (with fallback to default images)
@app.route('/uploads/<path:filename>')
def serve_uploads(filename):
    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(file_path):
        return send_from_directory(app.config['UPLOAD_FOLDER'], filename)
    default_path = os.path.join(app.root_path, 'static', 'default_images', filename)
    if os.path.exists(default_path):
        return send_from_directory(os.path.join(app.root_path, 'static', 'default_images'), filename)
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Login decorator
def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Mock Email Notification function
def send_email_notification(inquiry):
    log_dir = os.path.join(app.root_path, 'logs')
    os.makedirs(log_dir, exist_ok=True)
    log_file = os.path.join(log_dir, 'emails.log')
    
    timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    email_body = f"""
============================================================
NEW INQUIRY RECEIVED - {timestamp}
============================================================
Name:         {inquiry['name']}
Company:      {inquiry['company_name']}
Email:        {inquiry['email']}
Phone:        {inquiry['phone']}
Project Type: {inquiry['project_type']}
Message:
{inquiry['message']}
============================================================
"""
    # 1. Log to local file
    try:
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(email_body)
        print(f"[EMAIL SYSTEM] Inquiry logged successfully to {log_file}")
    except Exception as e:
        print(f"[EMAIL SYSTEM] Error logging email: {e}")
        
    # 2. Real SMTP Dispatcher placeholder (User can configure standard env vars)
    smtp_host = os.environ.get('SMTP_HOST')
    smtp_port = os.environ.get('SMTP_PORT')
    smtp_user = os.environ.get('SMTP_USER')
    smtp_password = os.environ.get('SMTP_PASSWORD')
    smtp_to = os.environ.get('SMTP_TO', 'sales.earthxd@gmail.com')
    
    if smtp_host and smtp_user and smtp_password:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        
        msg = MIMEMultipart()
        msg['From'] = smtp_user
        msg['To'] = smtp_to
        msg['Subject'] = f"EarthX Designs: New Lead from {inquiry['name']}"
        msg.attach(MIMEText(email_body, 'plain'))
        
        try:
            with smtplib.SMTP(smtp_host, int(smtp_port or 587)) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_mail(smtp_user, [smtp_to], msg.as_string())
            print("[EMAIL SYSTEM] Notification email dispatched successfully.")
        except Exception as e:
            print(f"[EMAIL SYSTEM] SMTP send error: {e}")

# Context processor for global templates
@app.context_processor
def inject_global_data():
    conn = get_db_connection()
    nav_services = conn.execute(
        'SELECT name, slug FROM service_categories WHERE is_published = 1 ORDER BY display_order'
    ).fetchall()
    conn.close()
    return {
        'now': datetime.datetime.now(),
        'nav_services': nav_services
    }

# ==========================================
# PUBLIC ROUTES
# ==========================================

@app.route('/')
def home():
    conn = get_db_connection()
    # Featured projects (3 most recent)
    projects = conn.execute('''
        SELECT p.*, c.name as category_name 
        FROM projects p 
        LEFT JOIN categories c ON p.category_id = c.id 
        WHERE p.status = 'published' 
        ORDER BY p.completion_date DESC LIMIT 3
    ''').fetchall()
    
    # Testimonials
    testimonials = conn.execute('SELECT * FROM testimonials ORDER BY id DESC LIMIT 5').fetchall()
    
    # Blog posts
    blogs = conn.execute("SELECT * FROM blog_posts WHERE status = 'published' ORDER BY created_at DESC LIMIT 3").fetchall()
    
    # Client logos for auto-scroll marquee
    client_logos = conn.execute("SELECT * FROM client_logos WHERE is_published = 1 ORDER BY display_order ASC, id ASC").fetchall()
    
    conn.close()
    return render_template('home.html', projects=projects, testimonials=testimonials, blogs=blogs, client_logos=client_logos)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM service_categories WHERE is_published = 1 ORDER BY display_order').fetchall()
    
    # We will pass a dict of category -> services to the template
    services_by_cat = {}
    for cat in categories:
        services_by_cat[cat['id']] = conn.execute('SELECT * FROM services WHERE category_id = ? AND is_published = 1 ORDER BY display_order', (cat['id'],)).fetchall()
        
    conn.close()
    return render_template('services.html', categories=categories, services_by_cat=services_by_cat)

@app.route('/services/<slug>')
def service_category(slug):
    conn = get_db_connection()
    category = conn.execute('SELECT * FROM service_categories WHERE slug = ? AND is_published = 1', (slug,)).fetchone()
    
    if not category:
        conn.close()
        return "Service category not found or unpublished", 404
        
    services = conn.execute('SELECT * FROM services WHERE category_id = ? AND is_published = 1 ORDER BY display_order', (category['id'],)).fetchall()
    conn.close()
    
    # Need to parse json for features/benefits/deliverables
    import json
    parsed_services = []
    for svc in services:
        svc_dict = dict(svc)
        svc_dict['features'] = json.loads(svc_dict['features']) if svc_dict['features'] else []
        svc_dict['benefits'] = json.loads(svc_dict['benefits']) if svc_dict['benefits'] else []
        svc_dict['deliverables'] = json.loads(svc_dict['deliverables']) if svc_dict['deliverables'] else []
        parsed_services.append(svc_dict)
        
    return render_template('service_category.html', category=category, services=parsed_services)

@app.route('/portfolio')
def portfolio():
    category_slug = request.args.get('category')
    search_query = request.args.get('q', '').strip()
    
    conn = get_db_connection()
    categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
    
    query = '''
        SELECT p.*, c.name as category_name, c.slug as category_slug 
        FROM projects p 
        LEFT JOIN categories c ON p.category_id = c.id 
        WHERE p.status = 'published'
    '''
    params = []
    
    if category_slug:
        query += ' AND c.slug = ?'
        params.append(category_slug)
        
    if search_query:
        query += ' AND (p.title LIKE ? OR p.description LIKE ? OR p.location LIKE ? OR p.services_delivered LIKE ?)'
        like_q = f'%{search_query}%'
        params.extend([like_q, like_q, like_q, like_q])
        
    query += ' ORDER BY p.completion_date DESC'
    projects = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('portfolio.html', projects=projects, categories=categories, active_category=category_slug, search_query=search_query)

@app.route('/portfolio/<int:project_id>')
def project_detail(project_id):
    conn = get_db_connection()
    project = conn.execute('''
        SELECT p.*, c.name as category_name, c.slug as category_slug 
        FROM projects p 
        LEFT JOIN categories c ON p.category_id = c.id 
        WHERE p.id = ? AND p.status = 'published'
    ''', (project_id,)).fetchone()
    
    if not project:
        conn.close()
        return "Project not found", 404
        
    # Gallery images
    images = conn.execute('SELECT * FROM project_images WHERE project_id = ? ORDER BY display_order ASC', (project_id,)).fetchall()
    
    # Related projects
    related = conn.execute('''
        SELECT p.*, c.name as category_name 
        FROM projects p 
        LEFT JOIN categories c ON p.category_id = c.id 
        WHERE p.category_id = ? AND p.id != ? AND p.status = 'published' 
        ORDER BY p.completion_date DESC LIMIT 3
    ''', (project['category_id'], project_id)).fetchall()
    
    conn.close()
    
    # Parse services delivered
    services_delivered = [s.strip() for s in project['services_delivered'].split(',')] if project['services_delivered'] else []
    
    return render_template('project_detail.html', project=project, images=images, related=related, services_delivered=services_delivered)

@app.route('/testimonials')
def testimonials():
    conn = get_db_connection()
    reviews = conn.execute('SELECT * FROM testimonials ORDER BY id DESC').fetchall()
    conn.close()
    return render_template('testimonials.html', testimonials=reviews)

@app.route('/blog')
def blog():
    category = request.args.get('category')
    search_query = request.args.get('q', '').strip()
    
    conn = get_db_connection()
    # Unique blog categories
    categories = conn.execute('SELECT DISTINCT category FROM blog_posts WHERE status = "published"').fetchall()
    categories = [row['category'] for row in categories]
    
    query = 'SELECT * FROM blog_posts WHERE status = "published"'
    params = []
    
    if category:
        query += ' AND category = ?'
        params.append(category)
        
    if search_query:
        query += ' AND (title LIKE ? OR content LIKE ? OR excerpt LIKE ?)'
        like_q = f'%{search_query}%'
        params.extend([like_q, like_q, like_q])
        
    query += ' ORDER BY created_at DESC'
    posts = conn.execute(query, params).fetchall()
    conn.close()
    
    return render_template('blog.html', posts=posts, categories=categories, active_category=category, search_query=search_query)

@app.route('/blog/<slug>')
def blog_detail(slug):
    conn = get_db_connection()
    post = conn.execute('SELECT * FROM blog_posts WHERE slug = ? AND status = "published"', (slug,)).fetchone()
    
    if not post:
        conn.close()
        return "Blog article not found", 404
        
    # Recent posts for sidebar
    recent = conn.execute('SELECT * FROM blog_posts WHERE slug != ? AND status = "published" ORDER BY created_at DESC LIMIT 3', (slug,)).fetchall()
    conn.close()
    return render_template('blog_detail.html', post=post, recent=recent)

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        company_name = request.form.get('company_name', '').strip()
        email = request.form.get('email', '').strip()
        phone = request.form.get('phone', '').strip()
        project_type = request.form.get('project_type', '').strip()
        message = request.form.get('message', '').strip()
        
        if not name or not email or not message:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for('contact'))
            
        conn = get_db_connection()
        conn.execute('''
            INSERT INTO contact_inquiries (name, company_name, email, phone, project_type, message)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (name, company_name, email, phone, project_type, message))
        conn.commit()
        conn.close()
        
        # Dispatch email notification
        inquiry_data = {
            'name': name,
            'company_name': company_name,
            'email': email,
            'phone': phone,
            'project_type': project_type,
            'message': message
        }
        send_email_notification(inquiry_data)
        
        flash("Thank you! Your request has been received. Our team will contact you shortly.", "success")
        return redirect(url_for('contact'))
        
    return render_template('contact.html')

# ==========================================
# ADMIN AUTHENTICATION
# ==========================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if 'user_id' in session:
        return redirect(url_for('admin_dashboard'))
        
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '').strip()
        
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND is_active = 1', (email,)).fetchone()
        conn.close()
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['id']
            session['user_email'] = user['email']
            session['user_role'] = user['role']
            session['user_name'] = user['name'] or user['email']
            return redirect(url_for('admin_dashboard'))
        else:
            flash("Invalid email or password.", "error")
            
    return render_template('admin/login.html')

@app.route('/admin/forgot-password', methods=['GET', 'POST'])
def admin_forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip()
        conn = get_db_connection()
        user = conn.execute('SELECT * FROM users WHERE email = ? AND is_active = 1', (email,)).fetchone()
        
        if user:
            # Generate a reset token
            token = secrets.token_urlsafe(32)
            expiry = (datetime.datetime.now() + datetime.timedelta(hours=1)).strftime('%Y-%m-%d %H:%M:%S')
            conn.execute('UPDATE users SET reset_token = ?, reset_token_expiry = ? WHERE id = ?', (token, expiry, user['id']))
            conn.commit()
            
            # Generate a temporary password instead (since we don't have real SMTP)
            temp_password = ''.join(secrets.choice(string.ascii_letters + string.digits) for _ in range(10))
            hashed = generate_password_hash(temp_password)
            conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed, user['id']))
            conn.commit()
            
            # Log the temp password (in production, this would be emailed)
            log_dir = os.path.join(app.root_path, 'logs')
            os.makedirs(log_dir, exist_ok=True)
            log_file = os.path.join(log_dir, 'password_resets.log')
            timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            with open(log_file, 'a', encoding='utf-8') as f:
                f.write(f"[{timestamp}] Password reset for {email}. Temporary password: {temp_password}\n")
            
            flash(f"Password has been reset. Your temporary password is: {temp_password} — Please change it after logging in.", "success")
        else:
            flash("If this email exists in our system, a reset link has been sent.", "success")
        
        conn.close()
        return redirect(url_for('admin_forgot_password'))
    
    return render_template('admin/forgot_password.html')

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash("You have logged out successfully.", "success")
    return redirect(url_for('admin_login'))

@app.route('/admin')
@login_required
def admin_dashboard():
    return render_template('admin/dashboard.html')

# ==========================================
# ADMIN REST API ENDPOINTS
# ==========================================

# 1. CATEGORIES API
@app.route('/api/categories', methods=['GET', 'POST'])
@login_required
def api_categories():
    conn = get_db_connection()
    if request.method == 'GET':
        categories = conn.execute('SELECT * FROM categories ORDER BY name ASC').fetchall()
        conn.close()
        return jsonify([dict(c) for c in categories])
        
    elif request.method == 'POST':
        data = request.json or {}
        name = data.get('name', '').strip()
        slug = data.get('slug', '').strip()
        
        if not name or not slug:
            return jsonify({'error': 'Name and Slug are required'}), 400
            
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO categories (name, slug) VALUES (?, ?)', (name, slug))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            return jsonify({'id': new_id, 'name': name, 'slug': slug}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Category name or slug already exists.'}), 400

@app.route('/api/categories/<int:cat_id>', methods=['PUT', 'DELETE'])
@login_required
def api_category_detail(cat_id):
    conn = get_db_connection()
    if request.method == 'PUT':
        data = request.json or {}
        name = data.get('name', '').strip()
        slug = data.get('slug', '').strip()
        
        if not name or not slug:
            return jsonify({'error': 'Name and Slug are required'}), 400
            
        try:
            conn.execute('UPDATE categories SET name = ?, slug = ? WHERE id = ?', (name, slug, cat_id))
            conn.commit()
            conn.close()
            return jsonify({'id': cat_id, 'name': name, 'slug': slug})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Category name or slug already exists.'}), 400
            
    elif request.method == 'DELETE':
        conn.execute('DELETE FROM categories WHERE id = ?', (cat_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Category deleted successfully'})

# 2. PROJECTS API
@app.route('/api/projects', methods=['GET', 'POST'])
@login_required
def api_projects():
    conn = get_db_connection()
    if request.method == 'GET':
        projects = conn.execute('''
            SELECT p.*, c.name as category_name 
            FROM projects p 
            LEFT JOIN categories c ON p.category_id = c.id 
            ORDER BY p.created_at DESC
        ''').fetchall()
        
        result = []
        for p in projects:
            p_dict = dict(p)
            # Fetch gallery count
            images = conn.execute('SELECT COUNT(*) FROM project_images WHERE project_id = ?', (p['id'],)).fetchone()
            p_dict['gallery_count'] = images[0]
            result.append(p_dict)
            
        conn.close()
        return jsonify(result)
        
    elif request.method == 'POST':
        title = request.form.get('title', '').strip()
        category_id = request.form.get('category_id')
        capacity = request.form.get('capacity', '').strip()
        location = request.form.get('location', '').strip()
        client_name = request.form.get('client_name', '').strip()
        description = request.form.get('description', '').strip()
        services_delivered = request.form.get('services_delivered', '').strip()
        completion_date = request.form.get('completion_date', '').strip()
        status = request.form.get('status', 'published')
        
        # Check required fields
        if not title or not category_id or not capacity or not location or not description or not services_delivered or not completion_date:
            return jsonify({'error': 'Please fill all required fields.'}), 400
            
        # File handling for featured image
        file = request.files.get('featured_image')
        if not file or file.filename == '':
            return jsonify({'error': 'Featured image is required.'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid image format.'}), 400
            
        filename = secure_filename(f"proj_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        featured_image_url = f"/uploads/{filename}"
        
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO projects (title, category_id, capacity, location, client_name, description, services_delivered, featured_image, completion_date, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (title, category_id, capacity, location, client_name or None, description, services_delivered, featured_image_url, completion_date, status))
        conn.commit()
        project_id = cursor.lastrowid
        
        # Handle multiple gallery uploads if present
        gallery_files = request.files.getlist('gallery_images')
        for i, gfile in enumerate(gallery_files):
            if gfile and gfile.filename != '' and allowed_file(gfile.filename):
                gfilename = secure_filename(f"gal_{project_id}_{i}_{datetime.datetime.now().strftime('%M%S')}_{gfile.filename}")
                gfile.save(os.path.join(app.config['UPLOAD_FOLDER'], gfilename))
                gurl = f"/uploads/{gfilename}"
                cursor.execute('INSERT INTO project_images (project_id, image_path, display_order) VALUES (?, ?, ?)', (project_id, gurl, i))
                
        conn.commit()
        conn.close()
        return jsonify({'message': 'Project created successfully', 'id': project_id}), 201

@app.route('/api/projects/<int:proj_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_project_detail(proj_id):
    conn = get_db_connection()
    if request.method == 'GET':
        project = conn.execute('SELECT * FROM projects WHERE id = ?', (proj_id,)).fetchone()
        if not project:
            conn.close()
            return jsonify({'error': 'Project not found'}), 404
            
        images = conn.execute('SELECT * FROM project_images WHERE project_id = ? ORDER BY display_order ASC', (proj_id,)).fetchall()
        result = dict(project)
        result['gallery'] = [dict(img) for img in images]
        conn.close()
        return jsonify(result)
        
    elif request.method == 'POST':
        # POST here represents editing (to support multipart form uploads in HTML5 forms easily)
        title = request.form.get('title', '').strip()
        category_id = request.form.get('category_id')
        capacity = request.form.get('capacity', '').strip()
        location = request.form.get('location', '').strip()
        client_name = request.form.get('client_name', '').strip()
        description = request.form.get('description', '').strip()
        services_delivered = request.form.get('services_delivered', '').strip()
        completion_date = request.form.get('completion_date', '').strip()
        status = request.form.get('status', 'published')
        
        if not title or not category_id or not capacity or not location or not description or not services_delivered or not completion_date:
            return jsonify({'error': 'Please fill all required fields.'}), 400
            
        # Get existing image
        project = conn.execute('SELECT featured_image FROM projects WHERE id = ?', (proj_id,)).fetchone()
        if not project:
            conn.close()
            return jsonify({'error': 'Project not found'}), 404
            
        featured_image_url = project['featured_image']
        
        # Check if new featured image was uploaded
        file = request.files.get('featured_image')
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(f"proj_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                featured_image_url = f"/uploads/{filename}"
                
        conn.execute('''
            UPDATE projects SET title = ?, category_id = ?, capacity = ?, location = ?, client_name = ?, description = ?, services_delivered = ?, featured_image = ?, completion_date = ?, status = ?
            WHERE id = ?
        ''', (title, category_id, capacity, location, client_name or None, description, services_delivered, featured_image_url, completion_date, status, proj_id))
        
        # Add new gallery images if uploaded
        gallery_files = request.files.getlist('gallery_images')
        # Get maximum display order
        max_order = conn.execute('SELECT MAX(display_order) FROM project_images WHERE project_id = ?', (proj_id,)).fetchone()[0] or 0
        
        for i, gfile in enumerate(gallery_files):
            if gfile and gfile.filename != '' and allowed_file(gfile.filename):
                gfilename = secure_filename(f"gal_{proj_id}_{max_order + i + 1}_{datetime.datetime.now().strftime('%M%S')}_{gfile.filename}")
                gfile.save(os.path.join(app.config['DATA_DIR'], gfilename))
                gurl = f"/uploads/{gfilename}"
                conn.execute('INSERT INTO project_images (project_id, image_path, display_order) VALUES (?, ?, ?)', (proj_id, gurl, max_order + i + 1))
                
        conn.commit()
        conn.close()
        return jsonify({'message': 'Project updated successfully'})
        
    elif request.method == 'DELETE':
        # Select all images for physical deletion
        images = conn.execute('SELECT image_path FROM project_images WHERE project_id = ?', (proj_id,)).fetchall()
        project = conn.execute('SELECT featured_image FROM projects WHERE id = ?', (proj_id,)).fetchone()
        
        # Delete project row (cascade deletes gallery rows from database constraint)
        conn.execute('DELETE FROM projects WHERE id = ?', (proj_id,))
        conn.commit()
        conn.close()
        
        # Clean up files from disk
        if project and project['featured_image'].startswith('/uploads/'):
            filepath = os.path.join(app.root_path, project['featured_image'].lstrip('/'))
            if os.path.exists(filepath) and os.path.basename(filepath) not in ['commercial_solar_featured.png', 'ground_mount_featured.png', 'residential_3d_featured.png', 'sld_blueprint.png']:
                try: os.remove(filepath)
                except Exception: pass
                
        for img in images:
            if img['image_path'].startswith('/uploads/'):
                filepath = os.path.join(app.root_path, img['image_path'].lstrip('/'))
                if os.path.exists(filepath) and os.path.basename(filepath) not in ['commercial_solar_featured.png', 'ground_mount_featured.png', 'residential_3d_featured.png', 'sld_blueprint.png']:
                    try: os.remove(filepath)
                    except Exception: pass
                    
        return jsonify({'message': 'Project deleted successfully'})

# Delete a single gallery image
@app.route('/api/projects/gallery/<int:img_id>', methods=['DELETE'])
@login_required
def api_delete_gallery_image(img_id):
    conn = get_db_connection()
    img = conn.execute('SELECT image_path FROM project_images WHERE id = ?', (img_id,)).fetchone()
    if not img:
        conn.close()
        return jsonify({'error': 'Image not found'}), 404
        
    conn.execute('DELETE FROM project_images WHERE id = ?', (img_id,))
    conn.commit()
    conn.close()
    
    # Delete from file system if not a seed file
    if img['image_path'].startswith('/uploads/'):
        filepath = os.path.join(app.root_path, img['image_path'].lstrip('/'))
        if os.path.exists(filepath) and os.path.basename(filepath) not in ['commercial_solar_featured.png', 'ground_mount_featured.png', 'residential_3d_featured.png', 'sld_blueprint.png']:
            try: os.remove(filepath)
            except Exception: pass
            
    return jsonify({'message': 'Gallery image deleted successfully'})

# Reorder gallery images
@app.route('/api/projects/gallery/reorder', methods=['POST'])
@login_required
def api_reorder_gallery():
    data = request.json or {}
    orders = data.get('orders', []) # List of {id: X, display_order: Y}
    
    conn = get_db_connection()
    for o in orders:
        conn.execute('UPDATE project_images SET display_order = ? WHERE id = ?', (o['display_order'], o['id']))
    conn.commit()
    conn.close()
    
    return jsonify({'message': 'Gallery order updated'})

# Update image caption
@app.route('/api/projects/gallery/<int:img_id>/caption', methods=['PUT'])
@login_required
def api_caption_gallery(img_id):
    data = request.json or {}
    caption = data.get('caption', '').strip()
    
    conn = get_db_connection()
    conn.execute('UPDATE project_images SET caption = ? WHERE id = ?', (caption, img_id))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Caption updated'})

# 3. BLOGS API
@app.route('/api/blogs', methods=['GET', 'POST'])
@login_required
def api_blogs():
    conn = get_db_connection()
    if request.method == 'GET':
        posts = conn.execute('SELECT * FROM blog_posts ORDER BY created_at DESC').fetchall()
        conn.close()
        return jsonify([dict(p) for p in posts])
        
    elif request.method == 'POST':
        title = request.form.get('title', '').strip()
        slug = request.form.get('slug', '').strip()
        category = request.form.get('category', '').strip()
        excerpt = request.form.get('excerpt', '').strip()
        content = request.form.get('content', '').strip()
        status = request.form.get('status', 'published')
        
        if not title or not slug or not category or not excerpt or not content:
            return jsonify({'error': 'Please fill all required fields.'}), 400
            
        file = request.files.get('featured_image')
        if not file or file.filename == '':
            return jsonify({'error': 'Featured image is required.'}), 400
            
        if not allowed_file(file.filename):
            return jsonify({'error': 'Invalid image format.'}), 400
            
        filename = secure_filename(f"blog_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        featured_image_url = f"/uploads/{filename}"
        
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO blog_posts (title, slug, category, excerpt, content, featured_image, status)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (title, slug, category, excerpt, content, featured_image_url, status))
            conn.commit()
            post_id = cursor.lastrowid
            conn.close()
            return jsonify({'message': 'Blog post created successfully', 'id': post_id}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Blog slug already exists.'}), 400

@app.route('/api/blogs/<int:post_id>', methods=['GET', 'POST', 'DELETE'])
@login_required
def api_blog_detail(post_id):
    conn = get_db_connection()
    if request.method == 'GET':
        post = conn.execute('SELECT * FROM blog_posts WHERE id = ?', (post_id,)).fetchone()
        conn.close()
        if not post:
            return jsonify({'error': 'Blog post not found'}), 404
        return jsonify(dict(post))
        
    elif request.method == 'POST':
        # representing PUT edits
        title = request.form.get('title', '').strip()
        slug = request.form.get('slug', '').strip()
        category = request.form.get('category', '').strip()
        excerpt = request.form.get('excerpt', '').strip()
        content = request.form.get('content', '').strip()
        status = request.form.get('status', 'published')
        
        if not title or not slug or not category or not excerpt or not content:
            return jsonify({'error': 'Please fill all required fields.'}), 400
            
        post = conn.execute('SELECT featured_image FROM blog_posts WHERE id = ?', (post_id,)).fetchone()
        if not post:
            conn.close()
            return jsonify({'error': 'Blog post not found'}), 404
            
        featured_image_url = post['featured_image']
        
        file = request.files.get('featured_image')
        if file and file.filename != '':
            if allowed_file(file.filename):
                filename = secure_filename(f"blog_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                featured_image_url = f"/uploads/{filename}"
                
        try:
            conn.execute('''
                UPDATE blog_posts SET title = ?, slug = ?, category = ?, excerpt = ?, content = ?, featured_image = ?, status = ?
                WHERE id = ?
            ''', (title, slug, category, excerpt, content, featured_image_url, status, post_id))
            conn.commit()
            conn.close()
            return jsonify({'message': 'Blog post updated successfully'})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Blog slug already exists.'}), 400
            
    elif request.method == 'DELETE':
        post = conn.execute('SELECT featured_image FROM blog_posts WHERE id = ?', (post_id,)).fetchone()
        conn.execute('DELETE FROM blog_posts WHERE id = ?', (post_id,))
        conn.commit()
        conn.close()
        
        if post and post['featured_image'].startswith('/uploads/'):
            filepath = os.path.join(app.root_path, post['featured_image'].lstrip('/'))
            if os.path.exists(filepath) and os.path.basename(filepath) not in ['commercial_solar_featured.png', 'ground_mount_featured.png', 'residential_3d_featured.png', 'sld_blueprint.png']:
                try: os.remove(filepath)
                except Exception: pass
                
        return jsonify({'message': 'Blog post deleted successfully'})

# 4. TESTIMONIALS API
@app.route('/api/testimonials', methods=['GET', 'POST'])
@login_required
def api_testimonials():
    conn = get_db_connection()
    if request.method == 'GET':
        reviews = conn.execute('SELECT * FROM testimonials ORDER BY id DESC').fetchall()
        conn.close()
        return jsonify([dict(r) for r in reviews])
        
    elif request.method == 'POST':
        data = request.json or {}
        client_name = data.get('client_name', '').strip()
        client_role = data.get('client_role', '').strip()
        company_name = data.get('company_name', '').strip()
        rating = data.get('rating', 5)
        feedback = data.get('feedback', '').strip()
        
        if not client_name or not client_role or not company_name or not feedback:
            return jsonify({'error': 'Please fill all required fields.'}), 400
            
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO testimonials (client_name, client_role, company_name, rating, feedback)
            VALUES (?, ?, ?, ?, ?)
        ''', (client_name, client_role, company_name, rating, feedback))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return jsonify({'message': 'Testimonial created successfully', 'id': new_id}), 201

@app.route('/api/testimonials/<int:test_id>', methods=['GET', 'PUT', 'DELETE'])
@login_required
def api_testimonial_detail(test_id):
    conn = get_db_connection()
    if request.method == 'GET':
        review = conn.execute('SELECT * FROM testimonials WHERE id = ?', (test_id,)).fetchone()
        conn.close()
        if not review:
            return jsonify({'error': 'Testimonial not found'}), 404
        return jsonify(dict(review))
        
    elif request.method == 'PUT':
        data = request.json or {}
        client_name = data.get('client_name', '').strip()
        client_role = data.get('client_role', '').strip()
        company_name = data.get('company_name', '').strip()
        rating = data.get('rating', 5)
        feedback = data.get('feedback', '').strip()
        
        if not client_name or not client_role or not company_name or not feedback:
            return jsonify({'error': 'Please fill all required fields.'}), 400
            
        conn.execute('''
            UPDATE testimonials SET client_name = ?, client_role = ?, company_name = ?, rating = ?, feedback = ?
            WHERE id = ?
        ''', (client_name, client_role, company_name, rating, feedback, test_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Testimonial updated successfully'})
        
    elif request.method == 'DELETE':
        conn.execute('DELETE FROM testimonials WHERE id = ?', (test_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Testimonial deleted successfully'})

# 5. CONTACT INQUIRIES API
@app.route('/api/inquiries', methods=['GET'])
@login_required
def api_inquiries():
    conn = get_db_connection()
    inquiries = conn.execute('SELECT * FROM contact_inquiries ORDER BY created_at DESC').fetchall()
    conn.close()
    return jsonify([dict(i) for i in inquiries])

@app.route('/api/inquiries/<int:inq_id>/contacted', methods=['PUT'])
@login_required
def api_inquiry_contacted(inq_id):
    data = request.json or {}
    status = data.get('status', 'contacted') # 'unread' or 'contacted'
    
    conn = get_db_connection()
    conn.execute('UPDATE contact_inquiries SET status = ? WHERE id = ?', (status, inq_id))
    conn.commit()
    conn.close()
    return jsonify({'message': f'Inquiry status updated to {status}'})

@app.route('/api/inquiries/export', methods=['GET'])
@login_required
def api_export_inquiries():
    conn = get_db_connection()
    inquiries = conn.execute('SELECT * FROM contact_inquiries ORDER BY created_at DESC').fetchall()
    conn.close()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Header
    writer.writerow(['ID', 'Name', 'Company Name', 'Email', 'Phone', 'Project Type', 'Message', 'Status', 'Submitted At'])
    
    # Rows
    for i in inquiries:
        writer.writerow([i['id'], i['name'], i['company_name'], i['email'], i['phone'], i['project_type'], i['message'], i['status'], i['created_at']])
        
    response = make_response(output.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename=earthx_leads_{datetime.datetime.now().strftime('%Y%m%d')}.csv"
    response.headers["Content-type"] = "text/csv"
    return response

# 6. SERVICE CATEGORIES API
import json

@app.route('/api/service-categories', methods=['GET', 'POST'])
@login_required
def api_service_categories():
    conn = get_db_connection()
    if request.method == 'GET':
        categories = conn.execute('SELECT * FROM service_categories ORDER BY display_order ASC').fetchall()
        result = []
        for c in categories:
            c_dict = dict(c)
            # Count services in this category
            svc_count = conn.execute('SELECT COUNT(*) FROM services WHERE category_id = ?', (c['id'],)).fetchone()[0]
            c_dict['service_count'] = svc_count
            result.append(c_dict)
        conn.close()
        return jsonify(result)
    
    elif request.method == 'POST':
        data = request.form if request.form else request.json
        if not data:
            data = {}
        
        name = data.get('name', '').strip()
        slug = data.get('slug', '').strip()
        short_description = data.get('short_description', '').strip()
        full_description = data.get('full_description', '').strip()
        icon = data.get('icon', 'briefcase').strip()
        hero_heading = data.get('hero_heading', '').strip()
        hero_subtitle = data.get('hero_subtitle', '').strip()
        cta_heading = data.get('cta_heading', '').strip()
        cta_description = data.get('cta_description', '').strip()
        cta_button_text = data.get('cta_button_text', '').strip()
        seo_title = data.get('seo_title', '').strip()
        seo_description = data.get('seo_description', '').strip()
        is_published = int(data.get('is_published', 1))
        
        if not name or not slug:
            conn.close()
            return jsonify({'error': 'Name and slug are required.'}), 400
            
        # Hero Background Image handling
        preset_hero_bg = data.get('preset_hero_bg', '').strip()
        hero_bg_image = ''
        file_bg = request.files.get('hero_bg_image') if hasattr(request, 'files') else None
        if file_bg and file_bg.filename != '' and allowed_file(file_bg.filename):
            filename_bg = secure_filename(f"svccat_bg_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file_bg.filename}")
            file_bg.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_bg))
            hero_bg_image = f"/uploads/{filename_bg}"
        elif preset_hero_bg:
            hero_bg_image = preset_hero_bg

        # Overview Section Media handling
        preset_media = data.get('preset_media', '').strip()
        hero_image = ''
        file = request.files.get('hero_image') if hasattr(request, 'files') else None
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"svccat_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            hero_image = f"/uploads/{filename}"
        elif preset_media:
            hero_image = preset_media
            
        max_order = conn.execute('SELECT MAX(display_order) FROM service_categories').fetchone()[0]
        display_order = (max_order or 0) + 1
            
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO service_categories (
                    name, slug, short_description, full_description, icon, hero_image, hero_bg_image,
                    hero_heading, hero_subtitle, cta_heading, cta_description, cta_button_text,
                    seo_title, seo_description, display_order, is_published
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                name, slug, short_description, full_description, icon, hero_image, hero_bg_image,
                hero_heading, hero_subtitle, cta_heading, cta_description, cta_button_text,
                seo_title, seo_description, display_order, is_published
            ))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            return jsonify({'message': 'Service category created successfully', 'id': new_id}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Category with this slug already exists.'}), 400

@app.route('/api/service-categories/<int:cat_id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def api_service_category_detail(cat_id):
    conn = get_db_connection()
    if request.method == 'GET':
        cat = conn.execute('SELECT * FROM service_categories WHERE id = ?', (cat_id,)).fetchone()
        conn.close()
        if not cat:
            return jsonify({'error': 'Category not found'}), 404
        return jsonify(dict(cat))
        
    elif request.method in ['PUT', 'POST']:
        data = request.form if request.form else request.json
        if not data:
            data = {}
            
        name = data.get('name', '').strip()
        slug = data.get('slug', '').strip()
        short_description = data.get('short_description', '').strip()
        full_description = data.get('full_description', '').strip()
        icon = data.get('icon', 'briefcase').strip()
        hero_heading = data.get('hero_heading', '').strip()
        hero_subtitle = data.get('hero_subtitle', '').strip()
        cta_heading = data.get('cta_heading', '').strip()
        cta_description = data.get('cta_description', '').strip()
        cta_button_text = data.get('cta_button_text', '').strip()
        seo_title = data.get('seo_title', '').strip()
        seo_description = data.get('seo_description', '').strip()
        is_published = int(data.get('is_published', 1))
        remove_hero_image = str(data.get('remove_hero_image', '0')).lower() in ['1', 'true']
        remove_hero_bg = str(data.get('remove_hero_bg', '0')).lower() in ['1', 'true']
        
        if not name or not slug:
            conn.close()
            return jsonify({'error': 'Name and slug are required.'}), 400
            
        cat = conn.execute('SELECT * FROM service_categories WHERE id = ?', (cat_id,)).fetchone()
        if not cat:
            conn.close()
            return jsonify({'error': 'Category not found'}), 404
            
        cat_dict = dict(cat)
        
        # Hero Background Image
        preset_hero_bg = data.get('preset_hero_bg', '').strip()
        hero_bg_image = '' if remove_hero_bg else cat_dict.get('hero_bg_image', '')
        file_bg = request.files.get('hero_bg_image') if hasattr(request, 'files') else None
        if file_bg and file_bg.filename != '' and allowed_file(file_bg.filename):
            filename_bg = secure_filename(f"svccat_bg_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file_bg.filename}")
            file_bg.save(os.path.join(app.config['UPLOAD_FOLDER'], filename_bg))
            hero_bg_image = f"/uploads/{filename_bg}"
        elif preset_hero_bg and not remove_hero_bg:
            hero_bg_image = preset_hero_bg

        # Overview Section Media
        preset_media = data.get('preset_media', '').strip()
        hero_image = '' if remove_hero_image else cat_dict.get('hero_image', '')
        file = request.files.get('hero_image') if hasattr(request, 'files') else None
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"svccat_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            hero_image = f"/uploads/{filename}"
        elif preset_media and not remove_hero_image:
            hero_image = preset_media
            
        try:
            conn.execute('''
                UPDATE service_categories SET
                    name = ?, slug = ?, short_description = ?, full_description = ?, icon = ?, hero_image = ?, hero_bg_image = ?,
                    hero_heading = ?, hero_subtitle = ?, cta_heading = ?, cta_description = ?, cta_button_text = ?,
                    seo_title = ?, seo_description = ?, is_published = ?
                WHERE id = ?
            ''', (
                name, slug, short_description, full_description, icon, hero_image, hero_bg_image,
                hero_heading, hero_subtitle, cta_heading, cta_description, cta_button_text,
                seo_title, seo_description, is_published, cat_id
            ))
            conn.commit()
            conn.close()
            return jsonify({'message': 'Service category updated successfully'})
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Slug must be unique.'}), 400
            
    elif request.method == 'DELETE':
        conn.execute('DELETE FROM service_categories WHERE id = ?', (cat_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Service category deleted successfully'})

@app.route('/api/service-categories/reorder', methods=['POST'])
@login_required
def api_service_categories_reorder():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({'error': 'Invalid data'}), 400
        
    conn = get_db_connection()
    for item in data:
        conn.execute('UPDATE service_categories SET display_order = ? WHERE id = ?', (item.get('display_order', 0), item.get('id')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Categories reordered'})

# 7. SERVICES API
@app.route('/api/services', methods=['GET', 'POST'])
@login_required
def api_services():
    conn = get_db_connection()
    if request.method == 'GET':
        cat_id = request.args.get('category_id')
        if cat_id:
            services = conn.execute('''
                SELECT s.*, c.name as category_name 
                FROM services s 
                LEFT JOIN service_categories c ON s.category_id = c.id 
                WHERE s.category_id = ? 
                ORDER BY s.display_order ASC
            ''', (cat_id,)).fetchall()
        else:
            services = conn.execute('''
                SELECT s.*, c.name as category_name 
                FROM services s 
                LEFT JOIN service_categories c ON s.category_id = c.id 
                ORDER BY c.display_order ASC, s.display_order ASC
            ''').fetchall()
        conn.close()
        return jsonify([dict(s) for s in services])
        
    elif request.method == 'POST':
        data = request.form if request.form else request.json
        if not data:
            data = {}
            
        category_id = data.get('category_id')
        name = data.get('name', '').strip()
        slug = data.get('slug', '').strip()
        short_description = data.get('short_description', '').strip()
        full_description = data.get('full_description', '').strip()
        icon = data.get('icon', 'sun').strip()
        
        # Parse features, benefits, deliverables if sent as string or list
        def format_json_field(val):
            if not val:
                return '[]'
            if isinstance(val, list):
                return json.dumps(val)
            val = val.strip()
            if val.startswith('[') and val.endswith(']'):
                return val
            # If newline or comma separated
            items = [line.strip() for line in val.replace('\r', '').split('\n') if line.strip()]
            if not items and ',' in val:
                items = [item.strip() for item in val.split(',') if item.strip()]
            return json.dumps(items)

        features = format_json_field(data.get('features'))
        benefits = format_json_field(data.get('benefits'))
        deliverables = format_json_field(data.get('deliverables'))
        is_published = int(data.get('is_published', 1))
        
        if not name or not slug or not category_id:
            conn.close()
            return jsonify({'error': 'Name, slug and category are required.'}), 400
            
        image = ''
        file = request.files.get('image') if hasattr(request, 'files') else None
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"svc_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = f"/uploads/{filename}"
            
        max_order = conn.execute('SELECT MAX(display_order) FROM services WHERE category_id = ?', (category_id,)).fetchone()[0]
        display_order = (max_order or 0) + 1
        
        try:
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO services (
                    category_id, name, slug, short_description, full_description, icon, image,
                    features, benefits, deliverables, display_order, is_published
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                category_id, name, slug, short_description, full_description, icon, image,
                features, benefits, deliverables, display_order, is_published
            ))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            return jsonify({'message': 'Service created successfully', 'id': new_id}), 201
        except sqlite3.IntegrityError:
            conn.close()
            return jsonify({'error': 'Service with this slug already exists.'}), 400

@app.route('/api/services/<int:svc_id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def api_service_detail(svc_id):
    conn = get_db_connection()
    if request.method == 'GET':
        svc = conn.execute('''
            SELECT s.*, c.name as category_name 
            FROM services s 
            LEFT JOIN service_categories c ON s.category_id = c.id 
            WHERE s.id = ?
        ''', (svc_id,)).fetchone()
        conn.close()
        if not svc:
            return jsonify({'error': 'Service not found'}), 404
        return jsonify(dict(svc))

    elif request.method in ['PUT', 'POST']:
        data = request.form if request.form else request.json
        if not data:
            data = {}
            
        category_id = data.get('category_id')
        name = data.get('name', '').strip()
        slug = data.get('slug', '').strip()
        short_description = data.get('short_description', '').strip()
        full_description = data.get('full_description', '').strip()
        icon = data.get('icon', 'sun').strip()
        
        def format_json_field(val):
            if not val:
                return '[]'
            if isinstance(val, list):
                return json.dumps(val)
            val = val.strip()
            if val.startswith('[') and val.endswith(']'):
                return val
            items = [line.strip() for line in val.replace('\r', '').split('\n') if line.strip()]
            if not items and ',' in val:
                items = [item.strip() for item in val.split(',') if item.strip()]
            return json.dumps(items)

        features = format_json_field(data.get('features'))
        benefits = format_json_field(data.get('benefits'))
        deliverables = format_json_field(data.get('deliverables'))
        is_published = int(data.get('is_published', 1))
        remove_image = str(data.get('remove_image', '0')).lower() in ['1', 'true']
        
        if not name or not slug:
            conn.close()
            return jsonify({'error': 'Name and slug are required.'}), 400
            
        svc = conn.execute('SELECT image, category_id FROM services WHERE id = ?', (svc_id,)).fetchone()
        if not svc:
            conn.close()
            return jsonify({'error': 'Service not found'}), 404
            
        target_cat_id = category_id if category_id else svc['category_id']
        image = '' if remove_image else svc['image']
        
        file = request.files.get('image') if hasattr(request, 'files') else None
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"svc_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = f"/uploads/{filename}"
            
        conn.execute('''
            UPDATE services SET
                category_id = ?, name = ?, slug = ?, short_description = ?, full_description = ?, icon = ?, image = ?,
                features = ?, benefits = ?, deliverables = ?, is_published = ?
            WHERE id = ?
        ''', (
            target_cat_id, name, slug, short_description, full_description, icon, image,
            features, benefits, deliverables, is_published, svc_id
        ))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Service updated successfully'})
        
    elif request.method == 'DELETE':
        conn.execute('DELETE FROM services WHERE id = ?', (svc_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Service deleted successfully'})

@app.route('/api/services/reorder', methods=['POST'])
@login_required
def api_services_reorder():
    data = request.json
    if not data or not isinstance(data, list):
        return jsonify({'error': 'Invalid data'}), 400
        
    conn = get_db_connection()
    for item in data:
        conn.execute('UPDATE services SET display_order = ? WHERE id = ?', (item.get('display_order', 0), item.get('id')))
    conn.commit()
    conn.close()
    return jsonify({'message': 'Services reordered'})

# 8. USERS MANAGEMENT API
@app.route('/api/users', methods=['GET', 'POST'])
@login_required
def api_users():
    # Only super_admin can manage users
    if session.get('user_role') != 'super_admin':
        return jsonify({'error': 'Access denied. Only super admin can manage users.'}), 403
    
    conn = get_db_connection()
    if request.method == 'GET':
        users = conn.execute('SELECT id, email, name, role, is_active, created_at FROM users ORDER BY id ASC').fetchall()
        conn.close()
        return jsonify([dict(u) for u in users])
    
    elif request.method == 'POST':
        data = request.json or {}
        email = data.get('email', '').strip()
        name = data.get('name', '').strip()
        password = data.get('password', '').strip()
        role = data.get('role', 'admin')
        
        if not email or not password:
            return jsonify({'error': 'Email and password are required.'}), 400
        
        hashed_pw = generate_password_hash(password)
        try:
            cursor = conn.cursor()
            cursor.execute('INSERT INTO users (email, password, name, role) VALUES (?, ?, ?, ?)', (email, hashed_pw, name, role))
            conn.commit()
            new_id = cursor.lastrowid
            conn.close()
            return jsonify({'message': 'User created successfully', 'id': new_id}), 201
        except Exception:
            conn.close()
            return jsonify({'error': 'Email already exists.'}), 400

@app.route('/api/users/<int:user_id>', methods=['PUT', 'DELETE'])
@login_required
def api_user_detail(user_id):
    if session.get('user_role') != 'super_admin':
        return jsonify({'error': 'Access denied.'}), 403
    
    conn = get_db_connection()
    if request.method == 'PUT':
        data = request.json or {}
        name = data.get('name', '').strip()
        role = data.get('role', 'admin')
        is_active = data.get('is_active', 1)
        new_password = data.get('password', '').strip()
        
        if new_password:
            hashed_pw = generate_password_hash(new_password)
            conn.execute('UPDATE users SET name = ?, role = ?, is_active = ?, password = ? WHERE id = ?', (name, role, is_active, hashed_pw, user_id))
        else:
            conn.execute('UPDATE users SET name = ?, role = ?, is_active = ? WHERE id = ?', (name, role, is_active, user_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'User updated successfully'})
    
    elif request.method == 'DELETE':
        # Prevent deleting yourself
        if user_id == session.get('user_id'):
            conn.close()
            return jsonify({'error': 'Cannot delete your own account.'}), 400
        
        conn.execute('DELETE FROM users WHERE id = ?', (user_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'User removed successfully'})

@app.route('/api/users/change-password', methods=['POST'])
@login_required
def api_change_password():
    data = request.json or {}
    current_password = data.get('current_password', '').strip()
    new_password = data.get('new_password', '').strip()
    
    if not current_password or not new_password:
        return jsonify({'error': 'Both current and new password are required.'}), 400
    
    if len(new_password) < 6:
        return jsonify({'error': 'New password must be at least 6 characters.'}), 400
    
    conn = get_db_connection()
    user = conn.execute('SELECT * FROM users WHERE id = ?', (session['user_id'],)).fetchone()
    
    if not user or not check_password_hash(user['password'], current_password):
        conn.close()
        return jsonify({'error': 'Current password is incorrect.'}), 400
    
    hashed = generate_password_hash(new_password)
    conn.execute('UPDATE users SET password = ? WHERE id = ?', (hashed, session['user_id']))
    conn.commit()
    conn.close()
# 9. CLIENT LOGOS MANAGEMENT API
@app.route('/api/client-logos', methods=['GET', 'POST'])
@login_required
def api_client_logos():
    conn = get_db_connection()
    if request.method == 'GET':
        logos = conn.execute('SELECT * FROM client_logos ORDER BY display_order ASC, id DESC').fetchall()
        result = [dict(row) for row in logos]
        conn.close()
        return jsonify(result)
        
    elif request.method == 'POST':
        data = request.form if request.form else request.json
        if not data:
            data = {}
            
        name = data.get('name', '').strip()
        website_url = data.get('website_url', '').strip()
        is_published = int(data.get('is_published', 1))
        
        if not name:
            conn.close()
            return jsonify({'error': 'Client/Partner name is required.'}), 400
            
        image = ''
        file = request.files.get('image') if hasattr(request, 'files') else None
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = f"/uploads/{filename}"
        elif data.get('preset_image'):
            image = data.get('preset_image').strip()
            
        if not image:
            conn.close()
            return jsonify({'error': 'Logo image is required.'}), 400
            
        max_order = conn.execute('SELECT MAX(display_order) FROM client_logos').fetchone()[0]
        display_order = (max_order or 0) + 1
        
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO client_logos (name, image, website_url, display_order, is_published)
            VALUES (?, ?, ?, ?, ?)
        ''', (name, image, website_url, display_order, is_published))
        conn.commit()
        new_id = cursor.lastrowid
        conn.close()
        return jsonify({'message': 'Client logo added successfully', 'id': new_id}), 201

@app.route('/api/client-logos/<int:logo_id>', methods=['GET', 'POST', 'PUT', 'DELETE'])
@login_required
def api_client_logo_detail(logo_id):
    conn = get_db_connection()
    if request.method == 'GET':
        logo = conn.execute('SELECT * FROM client_logos WHERE id = ?', (logo_id,)).fetchone()
        conn.close()
        if not logo:
            return jsonify({'error': 'Client logo not found'}), 404
        return jsonify(dict(logo))
        
    elif request.method in ['POST', 'PUT']:
        data = request.form if request.form else request.json
        if not data:
            data = {}
            
        name = data.get('name', '').strip()
        website_url = data.get('website_url', '').strip()
        is_published = int(data.get('is_published', 1))
        
        if not name:
            conn.close()
            return jsonify({'error': 'Client/Partner name is required.'}), 400
            
        logo = conn.execute('SELECT image FROM client_logos WHERE id = ?', (logo_id,)).fetchone()
        if not logo:
            conn.close()
            return jsonify({'error': 'Client logo not found'}), 404
            
        image = logo['image']
        file = request.files.get('image') if hasattr(request, 'files') else None
        if file and file.filename != '' and allowed_file(file.filename):
            filename = secure_filename(f"client_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            image = f"/uploads/{filename}"
        elif data.get('preset_image'):
            image = data.get('preset_image').strip()
            
        conn.execute('''
            UPDATE client_logos SET
                name = ?, image = ?, website_url = ?, is_published = ?
            WHERE id = ?
        ''', (name, image, website_url, is_published, logo_id))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Client logo updated successfully'})
        
    elif request.method == 'DELETE':
        conn.execute('DELETE FROM client_logos WHERE id = ?', (logo_id,))
        conn.commit()
        conn.close()
        return jsonify({'message': 'Client logo deleted successfully'})

# Main entrypoint setup
if __name__ == '__main__':
    # Initialize DB (if table users doesn't exist)
    init_db()
    
    # Run server locally
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting EarthX Designs CMS server at http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
