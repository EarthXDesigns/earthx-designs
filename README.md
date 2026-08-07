# EarthX Designs — Solar Engineering Design CMS

A full-featured content management system and marketing website for **EarthX Designs**, a solar engineering design company based in Ahmedabad, Gujarat. Built with Flask, SQLite, and vanilla JavaScript.

## 🌞 Features

### Public Website
- **Home** — Hero section, featured projects, testimonials carousel, blog feed, and CTA
- **About Us** — Company story, team, and mission
- **Services** — Solar 3D Design, 2D Layout, Shadow Analysis, SLD Drawings, BOQ Preparation, Ground Mount Design
- **Portfolio** — Filterable project gallery with category-based navigation and search
- **Project Detail** — Individual project pages with image gallery, service tags, and related projects
- **Testimonials** — Client reviews with star ratings
- **Blog** — Categorized articles with search
- **Contact** — Inquiry form with email notification logging
- **WhatsApp Integration** — Floating WhatsApp button and CTA links

### Admin CMS Panel (`/admin`)
- **Projects Management** — CRUD with featured image + multi-image gallery uploads
- **Categories Management** — Create/edit project categories
- **Testimonials** — Add/edit client reviews
- **Blog Posts** — Rich article management with image uploads
- **Contact Leads** — View inquiries, mark as contacted, export to CSV
- **User Access Management** — Add/remove admin users, role-based access (Super Admin / Admin)
- **Password Management** — Change password, forgot password with temporary password generation

## 🛠 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | Python 3, Flask |
| Database | SQLite3 |
| Frontend | HTML5, CSS3 (vanilla), JavaScript (vanilla) |
| Icons | Lucide Icons |
| Fonts | Google Fonts (Inter, Outfit) |
| Deployment | Cloudflare Tunnel / Any WSGI server |

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- pip

### Installation

```bash
# Clone the repository
git clone <your-repo-url>
cd EarthX_designs

# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

The server starts at `http://127.0.0.1:5000`.

### Default Admin Credentials
- **Email:** `sales.earthxd@gmail.com`
- **Password:** `EarthX@123`

> ⚠️ Change the default password after first login via the **User Access** tab in the admin panel.

## 📁 Project Structure

```
EarthX_designs/
├── app.py                  # Flask application with routes and API endpoints
├── database.py             # Database initialization and seeding
├── schema.sql              # SQLite schema definition
├── requirements.txt        # Python dependencies
├── Procfile                # Deployment process file
├── run.bat                 # Windows quick-start script
├── test_app.py             # Unit tests
├── static/
│   ├── css/
│   │   ├── style.css       # Main website styles
│   │   └── admin.css       # Admin panel styles
│   ├── js/
│   │   ├── main.js         # Website frontend logic
│   │   └── admin.js        # Admin panel client-side logic
│   ├── uploads/            # Uploaded and generated images
│   └── favicon.ico         # Browser tab icon
├── templates/
│   ├── base.html           # Base layout with navbar + footer
│   ├── home.html           # Homepage
│   ├── about.html          # About page
│   ├── services.html       # Services page
│   ├── portfolio.html      # Portfolio listing
│   ├── project_detail.html # Single project page
│   ├── testimonials.html   # Testimonials page
│   ├── blog.html           # Blog listing
│   ├── blog_detail.html    # Single blog post
│   ├── contact.html        # Contact form
│   └── admin/
│       ├── login.html            # Admin login
│       ├── forgot_password.html  # Password reset
│       └── dashboard.html        # CMS dashboard (all tabs)
└── logs/                   # Email and password reset logs (gitignored)
```

## 📧 Contact

- **Email:** sales.earthxd@gmail.com
- **WhatsApp:** +91 9978841256
- **Address:** 317, Devashish Business Park, Premchand Nagar Rd, Bodakdev, Ahmedabad, Gujarat 380015
