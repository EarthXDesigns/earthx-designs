-- SQLite Database Schema for EarthX Designs CMS

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    slug TEXT UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    category_id INTEGER,
    capacity TEXT NOT NULL,
    location TEXT NOT NULL,
    client_name TEXT,
    description TEXT NOT NULL,
    services_delivered TEXT NOT NULL,
    featured_image TEXT NOT NULL,
    completion_date TEXT NOT NULL,
    status TEXT DEFAULT 'published', -- 'draft', 'published'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY(category_id) REFERENCES categories(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS project_images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER,
    image_path TEXT NOT NULL,
    caption TEXT,
    display_order INTEGER DEFAULT 0,
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS testimonials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    client_name TEXT NOT NULL,
    client_role TEXT NOT NULL,
    company_name TEXT NOT NULL,
    rating INTEGER DEFAULT 5,
    feedback TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS blog_posts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    slug TEXT UNIQUE NOT NULL,
    category TEXT NOT NULL, -- e.g., Solar Design, Solar Engineering, etc.
    content TEXT NOT NULL,
    excerpt TEXT NOT NULL,
    featured_image TEXT NOT NULL,
    status TEXT DEFAULT 'published', -- 'draft', 'published'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS contact_inquiries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    company_name TEXT NOT NULL,
    email TEXT NOT NULL,
    phone TEXT NOT NULL,
    project_type TEXT NOT NULL,
    message TEXT NOT NULL,
    status TEXT DEFAULT 'unread', -- 'unread', 'contacted'
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
