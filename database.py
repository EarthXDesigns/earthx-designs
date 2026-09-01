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
    """Copies default seed images from the repository to the persistent uploads folder."""
    if not os.path.exists(uploads_dir):
        os.makedirs(uploads_dir)

    default_images_dir = os.path.join(os.path.dirname(__file__), 'static', 'default_images')
    
    if not os.path.exists(default_images_dir):
        print("Default images directory not found, skipping image seed.")
        return

    # Copy all files from default_images to uploads_dir
    for filename in os.listdir(default_images_dir):
        source_path = os.path.join(default_images_dir, filename)
        target_path = os.path.join(uploads_dir, filename)
        
        # Only copy if it's a file and doesn't exist in the target
        if os.path.isfile(source_path):
            if not os.path.exists(target_path) or os.path.getsize(target_path) == 0:
                try:
                    shutil.copy(source_path, target_path)
                    print(f"Seeded {filename} to {target_path}")
                except Exception as e:
                    print(f"Error copying {filename}: {e}")

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
                'name': 'Ground Mount Detailed Design',
                'slug': 'ground-mount-detailed-design',
                'short_description': 'Comprehensive engineering for commercial & utility-scale ground mount solar projects.',
                'full_description': 'EarthX delivers end-to-end ground-mount solar design and engineering packages tailored for utility-scale solar farms and commercial installations. From terrain modeling and shading optimization to full substation and grid evacuation design.',
                'icon': 'mountain',
                'hero_heading': 'Ground Mount Detailed Design',
                'hero_subtitle': 'End-to-end civil, structural, and electrical engineering for utility-scale solar farms and commercial ground-mount installations.',
                'display_order': 3
            },
            {
                'name': 'Structure Design',
                'slug': 'structure-design',
                'short_description': 'Solar mounting structure design solutions based on project requirements and site conditions.',
                'full_description': 'EarthX provides solar mounting structure design solutions tailored to specific project requirements, site conditions, and installation needs. From standard rooftop mounting to custom solutions for complex sites.',
                'icon': 'warehouse',
                'hero_heading': 'Structure Design',
                'hero_subtitle': 'Solar mounting structure design solutions based on project requirements, site conditions, and installation requirements.',
                'display_order': 4
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
                    'Detailed Electrical layouts',
                    'Detailed civil and structural design',
                    'Cable routing and earthing design',
                    'BoQ, specifications and construction documentation',
                    'Staad report for structuure stability',
                    'CEIG drawing for govt approvals',
                    'Design coordination and interface management'
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
                    'Detailed project report',
                    'Precise inter-row spacing calculations for maximum energy yield and minimal shading losses',
                    'Ground-mount racking and foundation structural engineering for all soil conditions',
                    'Site grading, drainage design, and foundation engineering for solar farm installations',
                    'DC and AC electrical layout, string sizing, and single-line diagrams for ground-mount systems',
                    'MV/HV equipment interfaces',
                    'Electrical calculations and schedules',
                    'Roads, drainage, foundations and trenches',
                    'Substation and evacuation design'
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
            # Ground Mount Detailed Design Category Children (10 Distinct Engineering Services)
            {
                'category_id': cat_ids['ground-mount-detailed-design'],
                'name': 'Ground Mount Detailed Design',
                'slug': 'gm-detailed-design-package',
                'short_description': 'Complete engineering and design package for commercial and utility-scale ground mount projects.',
                'full_description': 'End-to-end engineering documentation for ground-mounted solar power plants, taking projects from initial site contours to execution-ready construction blueprints.',
                'icon': 'mountain',
                'features': json.dumps([
                    'End-to-end solar farm layout and engineering',
                    'Site topography and contour 3D modeling',
                    'Optimized module placement and MWp capacity density',
                    'Comprehensive civil, structural, and electrical integration',
                    'Execution-ready construction drawing package'
                ]),
                'benefits': json.dumps(['Turnkey engineering clarity', 'Maximized MWp capacity', 'Reduced installation timelines']),
                'deliverables': json.dumps(['Complete GM Drawing Set', 'Master Layout Plan', 'Design Basis Report']),
                'display_order': 1
            },
            {
                'category_id': cat_ids['ground-mount-detailed-design'],
                'name': 'Detailed Project Report (DPR)',
                'slug': 'detailed-project-report',
                'short_description': 'Bankable Detailed Project Reports covering techno-commercial feasibility and generation modeling.',
                'full_description': 'Comprehensive Detailed Project Reports (DPR) prepared for investors, lenders, and EPC developers covering plant sizing, energy yield simulations (P50/P90), CAPEX/OPEX modeling, and statutory roadmaps.',
                'icon': 'file-text',
                'features': json.dumps([
                    'Techno-commercial feasibility study & site assessment',
                    'PVsyst simulation with P50, P75, and P90 generation estimates',
                    'Financial modeling, CAPEX, OPEX, and LCOE breakdown',
                    'Equipment selection matrix (Modules, Inverters, Trackers)',
                    'Statutory regulatory roadmaps and environmental compliance checklist'
                ]),
                'benefits': json.dumps(['Bankable documentation for financing', 'Accurate ROI & generation forecasts', 'De-risked project execution']),
                'deliverables': json.dumps(['Bankable DPR PDF Report', 'PVsyst Yield Report', 'Financial Model Sheet']),
                'display_order': 2
            },
            {
                'category_id': cat_ids['ground-mount-detailed-design'],
                'name': 'Precise Inter-Row Spacing Calculations',
                'slug': 'precise-inter-row-spacing-calculations',
                'short_description': 'Calculations for maximum energy yield and minimal shading losses across all seasons.',
                'full_description': 'Advanced 3D mathematical shadow modeling to calculate optimal pitch, tilt angles, and Ground Coverage Ratio (GCR), completely eliminating winter shadow losses and boosting specific yield (kWh/kWp).',
                'icon': 'sun',
                'features': json.dumps([
                    'Precise inter-row spacing calculations for maximum energy yield and minimal shading losses',
                    'Winter solstice (Dec 21) 9 AM to 3 PM unshaded window optimization',
                    'Ground Coverage Ratio (GCR) optimization for terrain slopes',
                    'Fixed tilt pitch vs. single-axis tracker backtracking simulation',
                    'Near-shading 3D loss diagrams and string grouping analysis'
                ]),
                'benefits': json.dumps(['Eliminates inter-row shade losses', 'Maximizes specific annual yield', 'Optimizes land utilization']),
                'deliverables': json.dumps(['Pitch & Spacing Calculation Report', 'Shade Profile Diagrams', '3D Shadow Simulation']),
                'display_order': 3
            },
            {
                'category_id': cat_ids['ground-mount-detailed-design'],
                'name': 'Ground-Mount Racking & Foundation Structural Engineering',
                'slug': 'ground-mount-racking-foundation-engineering',
                'short_description': 'Structural engineering and foundation design for all soil conditions and high wind zones.',
                'full_description': 'Structural design and STAAD Pro verification for fixed-tilt and seasonal tilt structures. Tailored foundation solutions including driven piles, concrete ballast, helical screws, and rock anchors suited for any geotechnical profile.',
                'icon': 'warehouse',
                'features': json.dumps([
                    'Ground-mount racking and foundation structural engineering for all soil conditions',
                    'Driven pile, concrete pedestal, and ground screw foundation designs',
                    'STAAD Pro 3D structural analysis under IS 875 / ASCE 7-16 wind codes',
                    'Geotechnical report interpretation and pile pullout/lateral load verification',
                    'Hot-dip galvanized steel / PosMAC member specification and fabrication drawings'
                ]),
                'benefits': json.dumps(['25+ year structural stability', 'Material weight optimization', 'Resilience in high-wind zones']),
                'deliverables': json.dumps(['STAAD Pro Report', 'Structural Fabrication Drawings', 'Foundation Details & Pile Schedule']),
                'display_order': 4
            },
            {
                'category_id': cat_ids['ground-mount-detailed-design'],
                'name': 'Site Grading, Drainage Design & Foundation Engineering',
                'slug': 'site-grading-drainage-design',
                'short_description': 'Site grading, hydrology analysis, storm-water drainage design, and earthwork planning.',
                'full_description': 'Comprehensive civil engineering including Digital Elevation Modeling (DEM), cut-and-fill volume minimization, surface storm-water runoff drainage design, and foundation leveling for solar farm installations.',
                'icon': 'compass',
                'features': json.dumps([
                    'Site grading, drainage design, and foundation engineering for solar farm installations',
                    'Cut-and-fill optimization to minimize earth-moving and grading costs',
                    'Hydrological watershed analysis and peak storm-water discharge calculations',
                    'Peripheral and inter-block trapezoidal drainage ditch design',
                    'Culvert sizing and soil erosion prevention retaining structures'
                ]),
                'benefits': json.dumps(['Prevents plant flooding & soil erosion', 'Minimizes costly earth moving', 'Safe civil foundation grading']),
                'deliverables': json.dumps(['Grading & Earthwork Plan', 'Hydrology & Storm Drainage Layout', 'Civil Cross-Section Drawings']),
                'display_order': 5
            },
            {
                'category_id': cat_ids['ground-mount-detailed-design'],
                'name': 'DC & AC Electrical Layout, String Sizing & Single-Line Diagrams',
                'slug': 'dc-ac-electrical-layout-string-sizing-sld',
                'short_description': 'DC and AC electrical layout, string sizing, and single-line diagrams for ground-mount systems.',
                'full_description': 'Detailed electrical architecture design covering VOC/VMP string configuration, Inverter Loading Ratio (ILR), string combiner box mapping, inverter station layouts, and multi-page single-line schematics.',
                'icon': 'git-commit',
                'features': json.dumps([
                    'DC and AC electrical layout, string sizing, and single-line diagrams for ground-mount systems',
                    'String length optimization based on extreme temperature ranges (1500V/1000V DC)',
                    'DC cable routing, combiner box (SCB) grouping, and busbar design',
                    'Comprehensive Single Line Diagrams (SLD) covering PV strings to grid point',
                    'Protection coordination, DC/AC switchgear, and surge suppression design'
                ]),
                'benefits': json.dumps(['Optimized DC/AC electrical efficiency', 'Code compliant SLD for approvals', 'Minimized electrical losses']),
                'deliverables': json.dumps(['Full Plant SLD Schematic', 'DC & AC String Layout Plans', 'Inverter Station Electrical GA']),
                'display_order': 6
            },
            {
                'category_id': cat_ids['ground-mount-detailed-design'],
                'name': 'MV/HV Equipment Interfaces',
                'slug': 'mvhv-equipment-interfaces',
                'short_description': 'Medium & High Voltage equipment interfaces, step-up transformers, and RMU configurations.',
                'full_description': 'Engineering design for Medium Voltage and High Voltage equipment interfaces including Inverter Duty Transformers (IDT), Compact Substations (CSS), Ring Main Units (RMU), HT switchgear panels, and grid synchronization bays.',
                'icon': 'zap',
                'features': json.dumps([
                    'MV/HV equipment interfaces',
                    'Inverter Duty Transformer (IDT) sizing and impedance optimization',
                    '11kV / 33kV / 66kV HT switchgear and vacuum circuit breaker (VCB) interface',
                    'Ring Main Unit (RMU) loop configuration and protection relays',
                    'CT/PT selection, tariff metering cubicle, and utility interface engineering'
                ]),
                'benefits': json.dumps(['Seamless grid synchronization', 'Robust HV protection', 'Compliant with utility interconnect codes']),
                'deliverables': json.dumps(['MV/HV Interface Drawings', 'Transformer & Switchgear Layouts', 'Protection Logic Schemes']),
                'display_order': 7
            },
            {
                'category_id': cat_ids['ground-mount-detailed-design'],
                'name': 'Electrical Calculations and Schedules',
                'slug': 'electrical-calculations-and-schedules',
                'short_description': 'Cable sizing, voltage drop, short circuit analysis, and comprehensive engineering schedules.',
                'full_description': 'Rigorous engineering calculations according to IEC, IEEE, and IS standards, ensuring system safety, optimal cable sizing (<1.5% DC drop, <1% AC drop), grounding grid resistance, and complete installation schedules.',
                'icon': 'calculator',
                'features': json.dumps([
                    'Electrical calculations and schedules',
                    'DC string, main DC, and HT/LT AC cable sizing & voltage drop calculations',
                    'Short circuit fault level analysis and symmetrical/asymmetrical breaking capacity',
                    'Earthing grid design & mesh resistance calculations (IEEE 80 / IS 3043)',
                    'Complete Cable Schedule, Drum Schedule, and Bill of Quantities (BOQ)'
                ]),
                'benefits': json.dumps(['Zero cable undersizing risks', 'Guaranteed minimum power losses', 'Exact procurement quantities']),
                'deliverables': json.dumps(['Electrical Design Calculation Book', 'Cable Pull Schedule', 'Earthing Calculation Sheet']),
                'display_order': 8
            },
            {
                'category_id': cat_ids['ground-mount-detailed-design'],
                'name': 'Roads, Drainage, Foundations and Trenches',
                'slug': 'roads-drainage-foundations-trenches',
                'short_description': 'Civil design for internal plant roads, drainage networks, equipment pads, and cable trenches.',
                'full_description': 'Complete plant civil infrastructure engineering including main access roads, perimeter pathways with turning radius for heavy cranes, reinforced concrete equipment pads, and buried/precast cable trench networks.',
                'icon': 'map',
                'features': json.dumps([
                    'Roads, drainage, foundations and trenches',
                    'Internal WBM/paved road design with heavy vehicle turning radiuses',
                    'Reinforced concrete pad foundations for IDTs, inverters, and control rooms',
                    'Direct-buried and precast concrete cable trench routing and cross-sections',
                    'Perimeter fencing, security gate, and water supply network design'
                ]),
                'benefits': json.dumps(['Safe logistics and crane mobility', 'Durable civil equipment foundations', 'Clean cable management']),
                'deliverables': json.dumps(['Plant Road & Access Plan', 'Trench Cross-Section Blueprints', 'Civil Foundation Structural Details']),
                'display_order': 9
            },
            {
                'category_id': cat_ids['ground-mount-detailed-design'],
                'name': 'Substation and Evacuation Design',
                'slug': 'substation-and-evacuation-design',
                'short_description': 'Pooling substation, switchyard engineering, transmission lines, and grid evacuation design.',
                'full_description': 'Complete engineering for solar plant pooling substations (33kV / 66kV / 132kV / 220kV), switchyard layouts, transmission line towers, gantry structures, SCADA/telemetry systems, and statutory grid evacuation clearance documentation.',
                'icon': 'radio',
                'features': json.dumps([
                    'Substation and evacuation design',
                    'Pooling Substation (PSS) electrical layout, elevations, and clearance diagrams',
                    'Switchyard gantry structures, busbar arrangements, and isolators',
                    'Overhead transmission line routing, tower spotting, and sag-tension engineering',
                    'SCADA architecture, telemetry, RTU, and Power Plant Controller (PPC) interfaces'
                ]),
                'benefits': json.dumps(['Complete grid evacuation clearance', 'Utility-compliant substation design', 'Full telemetry & SCADA readiness']),
                'deliverables': json.dumps(['Substation Key SLD & Layout', 'Switchyard GA & Elevation Plans', 'Transmission Line Route Map']),
                'display_order': 10
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
