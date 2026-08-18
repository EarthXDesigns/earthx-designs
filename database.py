import sqlite3
import os
import shutil
import glob
from werkzeug.security import generate_password_hash

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

# We'll use a global variable to hold the configured DATA_DIR
CONFIGURED_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def get_db_connection():
    db_path = os.path.join(CONFIGURED_DATA_DIR, 'database.db')
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    return conn

def copy_generated_images(uploads_dir):
    """Locates generated images in the brain/artifacts folder and copies them to the uploads folder."""
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)

    # Search pattern in the brain directory (conversation ID)
    brain_dir = r"C:\Users\NACHI\.gemini\antigravity\brain\e427ce44-dc02-491a-93f4-00ff89515e60"
    
    mapping = {
        'india_commercial_solar': 'commercial_solar_featured.png',
        'india_ground_mount_solar': 'ground_mount_featured.png',
        'india_residential_solar': 'residential_3d_featured.png',
        'sld_blueprint': 'sld_blueprint.png'
    }

    # Copy files if found
    for prefix, target_name in mapping.items():
        target_path = os.path.join(uploads_dir, target_name)
        
        # Check if already copied
        if os.path.exists(target_path) and os.path.getsize(target_path) > 0:
            continue
            
        # Try to find file in brain folder
        matches = glob.glob(os.path.join(brain_dir, f"{prefix}_*.png"))
        if matches:
            # Get the latest matched file
            latest_file = max(matches, key=os.path.getctime)
            try:
                shutil.copy(latest_file, target_path)
                print(f"Copied {latest_file} to {target_path}")
            except Exception as e:
                print(f"Error copying {latest_file}: {e}")
        else:
            # Fallback empty files or copy a placeholder if not found
            print(f"Generated image matching {prefix} not found in brain directory.")
            # Create a simple placeholder if it doesn't exist
            if not os.path.exists(target_path):
                with open(target_path, 'wb') as f:
                    f.write(b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\rIDATx\x9cc`\x00\x00\x00\x02\x00\x01H\xaf\xa4q\x00\x00\x00\x00IEND\xaeB`\x82')

def init_db(data_dir=None):
    global CONFIGURED_DATA_DIR
    if data_dir:
        CONFIGURED_DATA_DIR = data_dir
        
    db_path = os.path.join(CONFIGURED_DATA_DIR, 'database.db')
    uploads_dir = os.path.join(CONFIGURED_DATA_DIR, 'uploads')
    
    copy_generated_images(uploads_dir)
    
    # Check if database already initialized
    db_exists = os.path.exists(db_path)
    
    conn = get_db_connection()
    
    with open(SCHEMA_PATH, 'r') as f:
        conn.executescript(f.read())
        
    cursor = conn.cursor()
    
    # Check if we need to seed
    cursor.execute("SELECT COUNT(*) FROM users")
    if cursor.fetchone()[0] == 0:
        # 1. Seed Admin User
        admin_email = 'sales.earthxd@gmail.com'
        admin_pw = 'EarthX@123'
        hashed_pw = generate_password_hash(admin_pw)
        cursor.execute("INSERT INTO users (email, password, name, role) VALUES (?, ?, ?, ?)", (admin_email, hashed_pw, 'EarthX Admin', 'super_admin'))
        print("Admin user seeded.")
        
        # 2. Seed Categories
        categories = [
            ('Residential', 'residential'),
            ('Commercial & Industrial', 'commercial-industrial'),
            ('Ground Mount', 'ground-mount')
        ]
        cursor.executemany("INSERT INTO categories (name, slug) VALUES (?, ?)", categories)
        print("Categories seeded.")
        
        # 3. Seed Projects
        projects = [
            (
                'Nexus Mall 350kW Commercial Rooftop Solar',
                2, # Commercial & Industrial
                '350 kWp',
                'Ahmedabad, Gujarat, India',
                'Nexus Commercial Ventures',
                'EarthX Designs completed the complete detailed engineering design for a 350kWp grid-connected rooftop solar PV project at Nexus Mall in Ahmedabad. The roof structure was complex with multiple HVAC units causing shadowing. Our engineering team performed a detailed shadow analysis to optimize the module placement and maximize energy yield. We delivered the full solar engineering package, including 3D model renderings, single line diagrams (SLD) with circuit protection specifications, structural layout drawings, and a detailed Bill of Quantities (BOQ). The design optimized cable routing to minimize DC losses to under 1.5% and ensured local DISCOM grid compliance.',
                'Solar 3D Design, Shadow Analysis, SLD Drawings, BOQ Preparation, Rooftop Solar Design',
                '/uploads/commercial_solar_featured.png',
                '2026-03-12',
                'published'
            ),
            (
                '10MW Utility-Scale Ground Mount Solar Farm',
                3, # Ground Mount
                '10 MW AC',
                'Assam, India',
                'Surya Power Developers',
                'This utility-scale project required complete ground-mount civil and electrical design support for a 10MW PV plant located in a hilly, lush green region of Assam. EarthX Designs prepared the detailed terrain modeling, solar tracker design optimization, and cable trench layout drawings. We conducted structural engineering calculations for the mounting structures to withstand high wind loads and monsoon conditions. The electrical package included DC/AC cabling layouts, central inverter station details, main single line diagrams (SLD) for the 33kV substation, earth grid design, and CEIG statutory clearance approval drawings. Our cost-optimized engineering saved the EPC client approximately 4% in balance-of-system (BOS) costs.',
                'Ground Mount Solar Design, Solar Engineering Consultancy, SLD Drawings, BOQ Preparation, CEIG Drawings',
                '/uploads/ground_mount_featured.png',
                '2026-05-20',
                'published'
            ),
            (
                'Premium Bungalow 12kW Solar Installation',
                1, # Residential
                '12.5 kWp',
                'Vadodara, Gujarat, India',
                'Mr. & Mrs. Patel',
                'For this luxury residential bungalow in Vadodara, EarthX Designs created an aesthetically pleasing solar integration design. The client requested hidden conduits and a neat layout that wouldn\'t compromise the architectural aesthetics. We developed a highly accurate solar 3D design using advanced modeling software. A detailed 365-day shadow analysis was carried out to select the optimal micro-inverter system layout. We provided the electrical single line diagram (SLD), site layout, structural racking details, and comprehensive DISCOM permit documentation. The system is designed to provide 100% net-zero energy offsetting for the estate.',
                'Solar 3D Design, Solar 2D Layout Design, Shadow Analysis, SLD Drawings, Rooftop Solar Design',
                '/uploads/residential_3d_featured.png',
                '2026-01-15',
                'published'
            )
        ]
        
        cursor.executemany("""
            INSERT INTO projects (
                title, category_id, capacity, location, client_name, 
                description, services_delivered, featured_image, completion_date, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, projects)
        print("Projects seeded.")
        
        # Get project ids for gallery seeding
        cursor.execute("SELECT id, title FROM projects")
        project_rows = cursor.fetchall()
        project_ids = {row['title']: row['id'] for row in project_rows}
        
        # 4. Seed Project Gallery Images (reusing generated files to keep it clean)
        gallery_images = [
            (project_ids['Nexus Mall 350kW Commercial Rooftop Solar'], '/uploads/sld_blueprint.png', 'Electrical Single Line Diagram (SLD) Design', 1),
            (project_ids['Nexus Mall 350kW Commercial Rooftop Solar'], '/uploads/commercial_solar_featured.png', '3D Shadow Analysis Layout Render', 2),
            
            (project_ids['10MW Utility-Scale Ground Mount Solar Farm'], '/uploads/sld_blueprint.png', '33kV Substation SLD Schematic', 1),
            (project_ids['10MW Utility-Scale Ground Mount Solar Farm'], '/uploads/ground_mount_featured.png', 'Tracker Mounting Layout Design', 2),
            
            (project_ids['Premium Bungalow 12kW Solar Installation'], '/uploads/residential_3d_featured.png', '3D Solar Panel Layout Rendering', 1),
            (project_ids['Premium Bungalow 12kW Solar Installation'], '/uploads/sld_blueprint.png', 'Residential Grid-Tie SLD Drawing', 2)
        ]
        
        cursor.executemany("""
            INSERT INTO project_images (project_id, image_path, caption, display_order)
            VALUES (?, ?, ?, ?)
        """, gallery_images)
        print("Project gallery seeded.")
        
        testimonials = [
            (
                'Vikram Desai',
                'Director of Engineering',
                'Vanguard Solar Solutions India',
                5,
                'EarthX Designs has been our go-to engineering partner for the last two years. Their 3D design and shadow analysis are incredibly accurate, helping us close commercial clients faster. Their turnaround time is outstanding, and local utility permit approvals have become a breeze thanks to their high-quality SLD drawings.'
            ),
            (
                'Ananya Sharma',
                'Chief Operations Officer',
                'Hind Renewable Power',
                5,
                'For our 15MW solar project in Rajasthan, EarthX Designs provided the entire CEIG electrical documentation and ground mount tracker civil design. Their cost optimization suggestions for structure design saved us lakhs of rupees in material costs. Excellent technical depth!'
            ),
            (
                'Rahul Shah',
                'Founder & President',
                'EcoVolt Residential Solar India',
                5,
                'Managing residential permits was taking up all our internal engineering time. Outsourcing 2D layout and SLD creation to EarthX Designs has doubled our installation capacity. Their drawings are neat, professional, and compliant with CEIG standards. Highly recommended.'
            )
        ]
        cursor.executemany("""
            INSERT INTO testimonials (client_name, client_role, company_name, rating, feedback)
            VALUES (?, ?, ?, ?, ?)
        """, testimonials)
        print("Testimonials seeded.")
        
        # 6. Seed Blog Posts
        blogs = [
            (
                'Understanding Shadow Analysis in Commercial Solar Design',
                'understanding-shadow-analysis-commercial-solar',
                'Shadow Analysis',
                'Commercial solar projects usually encounter multiple roof obstacles like HVAC systems, skylights, parapet walls, and neighboring buildings. Effective shadow analysis goes beyond checking visual obstacles; it models the solar path throughout the year. Utilizing advanced 3D simulations, solar engineers can determine the optimal setbacks and row spacing to avoid inter-row shading. This article explores the mathematical foundations of shade calculations and explains how EarthX Designs achieves sub-centimeter accuracy to ensure maximum project ROI.',
                'How commercial solar designs model HVAC shading, neighboring structures, and row-to-row solar panels to maximize yield.',
                '/uploads/residential_3d_featured.png',
                'published'
            ),
            (
                'Step-by-Step Guide to CEIG Drawings and Grid Compliances',
                'step-by-step-guide-ceig-drawings-grid-compliances',
                'Solar Engineering',
                'Obtaining Chief Electrical Inspector to the Government (CEIG) clearance is a critical milestone for solar project commissioning in India. A minor drafting error or non-compliance in single line diagrams, earthing layouts, or lightning protection calculations can delay approvals for months. In this article, we break down the list of mandatory drawings, including the main SLD, relay and metering schematics, equipment layouts, cable sizing, and earthing system design according to IS 3043 standards. We also share standard check-lists used by EarthX Designs to pass inspectors audits on the first attempt.',
                'A comprehensive checklist for solar installers to prepare error-free CEIG drawings for rapid project clearance.',
                '/uploads/sld_blueprint.png',
                'published'
            ),
            (
                'Ground Mount Structure Wind-Load Engineering: Best Practices',
                'ground-mount-structure-wind-load-engineering',
                'Ground Mount Design',
                'Utility-scale solar farms are exposed to severe weather elements for over 25 years. Structural failure due to high wind loads is one of the costliest risks in renewable energy assets. Our lead structural engineers explain how CFD (Computational Fluid Dynamics) simulations and wind-tunnel data are translated into racking structural design. We cover steel grade selection, hot-dip galvanization specifications, foundation pile depth analysis, and design standards like ASCE 7-16. Learn how EarthX Designs engineers robust structures while optimizing steel weight.',
                'An engineering-focused review of steel structural calculations, foundations, and wind-load design for solar farms.',
                '/uploads/ground_mount_featured.png',
                'published'
            )
        ]
        cursor.executemany("""
            INSERT INTO blog_posts (title, slug, category, content, excerpt, featured_image, status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, blogs)
        print("Blog posts seeded.")
        
        # 7. Seed Service Categories
        import json
        
        service_cats = [
            {
                'name': 'Pre Sales Design',
                'slug': 'pre-sales-design',
                'short_description': 'Professional solar design support for EPC companies during the pre-sales stage.',
                'full_description': 'EarthX provides comprehensive pre-sales design services that help EPC companies present compelling solar proposals to clients. Our pre-sales designs include realistic 3D visualizations and precise 2D layouts that improve sales conversion rates.',
                'icon': 'presentation',
                'hero_heading': 'Pre Sales Design',
                'hero_subtitle': 'Professional solar design support for EPC companies during the pre-sales stage. Win more projects with compelling visualizations and precise layouts.',
                'display_order': 1
            },
            {
                'name': 'Post Sales Design',
                'slug': 'post-sales-design',
                'short_description': 'Detailed execution-ready designs that convert approved solar concepts into installation-ready documentation.',
                'full_description': 'Once a project is approved, EarthX converts the concept into detailed, execution-ready engineering designs. Our post-sales services cover everything from detailed rooftop and ground mount layouts to CEIG approval documentation.',
                'icon': 'clipboard-check',
                'hero_heading': 'Post Sales Design',
                'hero_subtitle': 'Convert approved solar concepts into detailed, execution-ready designs with comprehensive engineering documentation.',
                'display_order': 2
            },
            {
                'name': 'Structure Design',
                'slug': 'structure-design',
                'short_description': 'Solar mounting structure design solutions based on project requirements and site conditions.',
                'full_description': 'EarthX provides solar mounting structure design solutions tailored to specific project requirements, site conditions, and installation needs. From standard rooftop mounting to custom solutions for complex sites.',
                'icon': 'warehouse',
                'hero_heading': 'Structure Design',
                'hero_subtitle': 'Solar mounting structure design solutions based on project requirements, site conditions, and installation requirements.',
                'display_order': 3
            }
        ]
        
        for cat in service_cats:
            cursor.execute("""
                INSERT INTO service_categories (name, slug, short_description, full_description, icon, hero_heading, hero_subtitle, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (cat['name'], cat['slug'], cat['short_description'], cat['full_description'], cat['icon'], cat['hero_heading'], cat['hero_subtitle'], cat['display_order']))
        
        print("Service categories seeded.")
        
        # Get category IDs
        cat_rows = cursor.execute("SELECT id, slug FROM service_categories").fetchall()
        cat_ids = {row['slug']: row['id'] for row in cat_rows}
        
        child_services = [
            # Pre Sales Design children
            {
                'category_id': cat_ids['pre-sales-design'],
                'name': '3D Pre Sales Design',
                'slug': '3d-pre-sales-design',
                'short_description': 'Realistic 3D solar visualizations for client presentations and sales proposals.',
                'full_description': 'Our 3D pre-sales design service creates photorealistic visualizations of proposed solar installations, helping EPC companies communicate their vision clearly and close deals faster.',
                'icon': 'box',
                'features': json.dumps([
                    'Detailed 3D modeling of the project site',
                    'Building and rooftop modeling',
                    'Solar panel placement visualization',
                    'Structure visualization',
                    'Client presentation-ready views',
                    'Helps EPC companies communicate proposed solar installations clearly',
                    'Improves sales conversion with realistic visualization before installation'
                ]),
                'benefits': json.dumps(['Higher client conversion rates', 'Professional proposal presentations', 'Clear project visualization']),
                'deliverables': json.dumps(['3D rendered views', 'Site model', 'Presentation-ready images']),
                'display_order': 1
            },
            {
                'category_id': cat_ids['pre-sales-design'],
                'name': '2D GA Layout',
                'slug': '2d-ga-layout',
                'short_description': 'Professional 2D General Arrangement layouts for project planning and client proposals.',
                'full_description': 'Our 2D GA layout service provides precise, professional solar layouts that are perfect for client presentations and initial project planning.',
                'icon': 'layout-grid',
                'features': json.dumps([
                    'Professional 2D General Arrangement layouts',
                    'Solar module placement optimization',
                    'Row spacing and panel orientation',
                    'Roof boundaries and setbacks',
                    'Walkways and equipment placement',
                    'Dimensioning and layout optimization',
                    'Clear drawings for client presentations and project planning'
                ]),
                'benefits': json.dumps(['Optimized panel layouts', 'Professional documentation', 'Clear project planning']),
                'deliverables': json.dumps(['2D GA layout drawings', 'Module arrangement plans', 'Dimensioned layouts']),
                'display_order': 2
            },
            # Post Sales Design children
            {
                'category_id': cat_ids['post-sales-design'],
                'name': '3D Post Design',
                'slug': '3d-post-design',
                'short_description': 'Detailed 3D solar installation models for execution-ready project documentation.',
                'full_description': 'Our 3D post-sales design creates highly detailed, accurate models of the solar installation for construction and execution planning.',
                'icon': 'box',
                'features': json.dumps([
                    'Detailed 3D solar installation model',
                    'Accurate rooftop/site representation',
                    'Module placement visualization',
                    'Structure visualization',
                    'Equipment positioning',
                    'Client/project presentation views',
                    'Detailed installation visualization'
                ]),
                'benefits': json.dumps(['Execution-ready visualization', 'Accurate site representation', 'Construction planning support']),
                'deliverables': json.dumps(['3D installation model', 'Equipment layout views', 'Construction reference renders']),
                'display_order': 1
            },
            {
                'category_id': cat_ids['post-sales-design'],
                'name': 'Rooftop Detailed Design',
                'slug': 'rooftop-detailed-design',
                'short_description': 'Comprehensive rooftop solar layouts with detailed engineering specifications.',
                'full_description': 'Complete detailed rooftop solar design covering every aspect of the installation from module arrangement to equipment placement.',
                'icon': 'home',
                'features': json.dumps([
                    'Detailed rooftop solar layout',
                    'Module arrangement and row spacing',
                    'Setbacks and walkways',
                    'Roof obstacle considerations (AC units, chimneys, parapets)',
                    'Equipment placement planning',
                    'Detailed dimensions',
                    'Optimized usable roof area'
                ]),
                'benefits': json.dumps(['Maximum roof utilization', 'Code-compliant designs', 'Installation-ready documentation']),
                'deliverables': json.dumps(['Detailed rooftop layout', 'Module arrangement plan', 'Equipment placement drawings']),
                'display_order': 2
            },
            {
                'category_id': cat_ids['post-sales-design'],
                'name': 'Ground Mount Detailed Design',
                'slug': 'ground-mount-detailed-design',
                'short_description': 'Detailed ground-mounted solar layouts with complete site engineering.',
                'full_description': 'Comprehensive ground mount solar design covering site layout, structure arrangement, and detailed engineering documentation.',
                'icon': 'mountain',
                'features': json.dumps([
                    'Ground-mounted solar layout design',
                    'Module/table arrangement',
                    'Row spacing optimization',
                    'Site boundaries and access pathways',
                    'Structure arrangement',
                    'Inverter/equipment positioning',
                    'Site optimization and detailed visualization'
                ]),
                'benefits': json.dumps(['Optimized site utilization', 'Cost-effective layouts', 'Construction-ready plans']),
                'deliverables': json.dumps(['Ground mount layout', 'Structure arrangement drawings', 'Site plans']),
                'display_order': 3
            },
            {
                'category_id': cat_ids['post-sales-design'],
                'name': 'CEIG Approvals',
                'slug': 'ceig-approvals',
                'short_description': 'CEIG approval drawing support and professional documentation for regulatory processes.',
                'full_description': 'EarthX provides design and documentation support for CEIG approval processes, including all required electrical and layout documentation.',
                'icon': 'file-check',
                'features': json.dumps([
                    'CEIG approval drawing support',
                    'Required electrical/layout documentation',
                    'Grounding-related drawings',
                    'Lightning protection layouts',
                    'Substation/equipment layouts where applicable',
                    'Professional documentation for approval processes'
                ]),
                'benefits': json.dumps(['Streamlined approval process', 'Compliant documentation', 'Professional engineering drawings']),
                'deliverables': json.dumps(['CEIG drawing package', 'Electrical documentation', 'Grounding/lightning layouts']),
                'display_order': 4
            },
            # Structure Design children
            {
                'category_id': cat_ids['structure-design'],
                'name': 'Standard Solar Structure',
                'slug': 'standard-solar-structure',
                'short_description': 'Standard rooftop solar mounting structures for common installation configurations.',
                'full_description': 'Our standard structure designs cover common rooftop solar mounting configurations optimized for practical installation and cost-effectiveness.',
                'icon': 'grid-3x3',
                'features': json.dumps([
                    'Standard rooftop solar mounting structures',
                    'Common installation configurations',
                    'Optimized module support',
                    'Proper module positioning',
                    'Practical installation approach',
                    'Suitable for standard rooftop applications',
                    'Design based on project requirements'
                ]),
                'benefits': json.dumps(['Cost-effective solutions', 'Proven designs', 'Quick turnaround']),
                'deliverables': json.dumps(['Structure design drawings', 'Material specifications', 'Installation guidelines']),
                'display_order': 1
            },
            {
                'category_id': cat_ids['structure-design'],
                'name': 'Custom Solar Structure',
                'slug': 'custom-solar-structure',
                'short_description': 'Custom mounting structure solutions for complex sites and unique project requirements.',
                'full_description': 'Custom structure designs for projects with unique site constraints, unusual roof geometry, or specialized requirements.',
                'icon': 'settings',
                'features': json.dumps([
                    'Custom mounting structure solutions',
                    'Site-specific structure concepts',
                    'Complex rooftop condition handling',
                    'Customized heights and orientations',
                    'Special roof geometry solutions',
                    'Customized module arrangement',
                    'Solutions for unusual site constraints',
                    'Design optimized for the specific project'
                ]),
                'benefits': json.dumps(['Tailored to project needs', 'Handles complex sites', 'Optimized for constraints']),
                'deliverables': json.dumps(['Custom structure drawings', 'Engineering calculations', 'Material specifications']),
                'display_order': 2
            }
        ]
        
        for svc in child_services:
            cursor.execute("""
                INSERT INTO services (category_id, name, slug, short_description, full_description, icon, features, benefits, deliverables, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (svc['category_id'], svc['name'], svc['slug'], svc['short_description'], svc['full_description'], svc['icon'], svc['features'], svc['benefits'], svc['deliverables'], svc['display_order']))
        
        print("Services seeded.")
        
        conn.commit()
    conn.close()

if __name__ == '__main__':
    init_db()
