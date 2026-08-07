import os
import csv
import io
import datetime
import secrets
import string
from flask import Flask, render_template, request, redirect, url_for, session, jsonify, flash, make_response
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from database import get_db_connection, init_db

app = Flask(__name__)
app.secret_key = os.environ.get('FLASK_SECRET_KEY', 'earthx_designs_secret_2026_super_key')
app.config['UPLOAD_FOLDER'] = os.path.join(app.root_path, 'static', 'uploads')
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max upload size
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}

# Ensure upload directory exists
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)

# Helper function for allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

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
    return {
        'now': datetime.datetime.now()
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
    
    conn.close()
    return render_template('home.html', projects=projects, testimonials=testimonials, blogs=blogs)

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/services')
def services():
    return render_template('services.html')

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
        featured_image_url = f"/static/uploads/{filename}"
        
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
                gurl = f"/static/uploads/{gfilename}"
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
                featured_image_url = f"/static/uploads/{filename}"
                
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
                gfile.save(os.path.join(app.config['UPLOAD_FOLDER'], gfilename))
                gurl = f"/static/uploads/{gfilename}"
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
        if project and project['featured_image'].startswith('/static/uploads/'):
            filepath = os.path.join(app.root_path, project['featured_image'].lstrip('/'))
            if os.path.exists(filepath) and os.path.basename(filepath) not in ['commercial_solar_featured.png', 'ground_mount_featured.png', 'residential_3d_featured.png', 'sld_blueprint.png']:
                try: os.remove(filepath)
                except Exception: pass
                
        for img in images:
            if img['image_path'].startswith('/static/uploads/'):
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
    if img['image_path'].startswith('/static/uploads/'):
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
        featured_image_url = f"/static/uploads/{filename}"
        
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
                featured_image_url = f"/static/uploads/{filename}"
                
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
        
        if post and post['featured_image'].startswith('/static/uploads/'):
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

# 6. USERS MANAGEMENT API
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
    return jsonify({'message': 'Password changed successfully'})

# Main entrypoint setup
if __name__ == '__main__':
    # Initialize DB (if table users doesn't exist)
    init_db()
    
    # Run server locally
    port = int(os.environ.get('PORT', 5000))
    print(f"Starting EarthX Designs CMS server at http://127.0.0.1:{port}")
    app.run(host='0.0.0.0', port=port, debug=True)
