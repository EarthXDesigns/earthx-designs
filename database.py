import sqlite3
import os
import json
import shutil
import glob
import urllib.request
import urllib.error
from werkzeug.security import generate_password_hash

SCHEMA_PATH = os.path.join(os.path.dirname(__file__), 'schema.sql')

# We'll use a global variable to hold the configured DATA_DIR
CONFIGURED_DATA_DIR = os.path.join(os.path.dirname(__file__), 'data')

def is_using_cloudflare_d1():
    """Returns True if Cloudflare D1 credentials are set in the environment."""
    return bool(
        os.environ.get('CLOUDFLARE_D1_DATABASE_ID') and
        os.environ.get('CLOUDFLARE_ACCOUNT_ID') and
        os.environ.get('CLOUDFLARE_API_TOKEN')
    )

class D1Row:
    """Wraps Cloudflare D1 row dictionaries to behave like sqlite3.Row."""
    def __init__(self, data_dict):
        self._dict = data_dict or {}
        self._keys = list(self._dict.keys())
        self._values = list(self._dict.values())
        
    def __getitem__(self, key):
        if isinstance(key, int):
            return self._values[key]
        return self._dict[key]
        
    def get(self, key, default=None):
        return self._dict.get(key, default)
        
    def keys(self):
        return self._dict.keys()
        
    def values(self):
        return self._dict.values()
        
    def items(self):
        return self._dict.items()
        
    def __iter__(self):
        return iter(self._dict)
        
    def __contains__(self, key):
        return key in self._dict
        
    def __repr__(self):
        return repr(self._dict)

class D1Cursor:
    """Cursor that executes SQL queries against Cloudflare D1 REST API."""
    def __init__(self, connection):
        self.connection = connection
        self.description = None
        self.lastrowid = None
        self.rowcount = 0
        self._results = []
        self._idx = 0

    def execute(self, sql, params=None):
        self._results = []
        self._idx = 0
        self.lastrowid = None
        self.rowcount = 0
        
        result_data = self.connection._query(sql, params)
        if result_data:
            results_list = result_data.get('results', [])
            self._results = [D1Row(r) for r in results_list]
            meta = result_data.get('meta', {})
            self.lastrowid = meta.get('last_row_id')
            self.rowcount = meta.get('changes', len(self._results))
            if results_list and len(results_list) > 0:
                self.description = [(k, None, None, None, None, None, None) for k in results_list[0].keys()]
            else:
                self.description = None
        return self

    def executemany(self, sql, seq_of_parameters):
        for params in seq_of_parameters:
            self.execute(sql, params)
        return self

    def fetchone(self):
        if self._idx < len(self._results):
            row = self._results[self._idx]
            self._idx += 1
            return row
        return None

    def fetchall(self):
        res = self._results[self._idx:]
        self._idx = len(self._results)
        return res

    def close(self):
        pass

class D1Connection:
    """Connection that wraps Cloudflare D1 REST API to provide a SQLite-compatible interface."""
    def __init__(self, account_id, database_id, api_token):
        self.account_id = account_id.strip().strip('\'"')
        self.database_id = database_id.strip().strip('\'"')
        self.api_token = api_token.strip().strip('\'"')
        self.url = f"https://api.cloudflare.com/client/v4/accounts/{self.account_id}/d1/database/{self.database_id}/query"
        self.row_factory = None

    def cursor(self):
        return D1Cursor(self)

    def execute(self, sql, params=None):
        cur = self.cursor()
        return cur.execute(sql, params)

    def executemany(self, sql, seq_of_parameters):
        cur = self.cursor()
        return cur.executemany(sql, seq_of_parameters)

    def executescript(self, script):
        cleaned_lines = []
        for line in script.splitlines():
            stripped = line.strip()
            if stripped.startswith('--'):
                continue
            cleaned_lines.append(line)
        cleaned_sql = '\n'.join(cleaned_lines)
        statements = [s.strip() for s in cleaned_sql.split(';') if s.strip()]
        for stmt in statements:
            self.execute(stmt)

    def commit(self):
        pass  # Cloudflare D1 auto-commits

    def close(self):
        pass

    def _query(self, sql, params=None):
        body = {"sql": sql}
        if params is not None:
            clean_params = []
            for p in params:
                if isinstance(p, (bytes, bytearray)):
                    clean_params.append(p.decode('utf-8', errors='ignore'))
                else:
                    clean_params.append(p)
            body["params"] = clean_params

        req = urllib.request.Request(
            self.url,
            data=json.dumps(body).encode('utf-8'),
            headers={
                "Authorization": f"Bearer {self.api_token}",
                "Content-Type": "application/json",
                "User-Agent": "EarthXDesigns-D1Client/1.0"
            },
            method="POST"
        )
        
        try:
            with urllib.request.urlopen(req, timeout=20) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                if not data.get('success'):
                    err_msg = json.dumps(data.get('errors', []))
                    if 'UNIQUE constraint' in err_msg or '19' in err_msg:
                        raise sqlite3.IntegrityError(err_msg)
                    raise Exception(f"D1 Query failed: {err_msg}")
                result_list = data.get('result', [])
                if result_list:
                    return result_list[0]
                return None
        except urllib.error.HTTPError as e:
            err_body = e.read().decode('utf-8', errors='ignore')
            if 'UNIQUE constraint' in err_body:
                raise sqlite3.IntegrityError(err_body)
            raise Exception(f"D1 HTTP Error {e.code}: {err_body}")

def get_db_connection():
    if is_using_cloudflare_d1():
        return D1Connection(
            os.environ.get('CLOUDFLARE_ACCOUNT_ID'),
            os.environ.get('CLOUDFLARE_D1_DATABASE_ID'),
            os.environ.get('CLOUDFLARE_API_TOKEN')
        )
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
def seed_service_categories_and_services(conn, force=False):
    """Ensures service categories and child options exist in the database."""
    cursor = conn.cursor()
    if not force:
        try:
            cursor.execute("SELECT COUNT(*) FROM service_categories")
            row = cursor.fetchone()
            if row and row[0] > 0:
                print(f"[SEED] Service categories already exist ({row[0]} found).")
                return False
        except Exception as e:
            print(f"[SEED] Checking service categories: {e}")

    print("[SEED] Seeding service categories and child services...")
    service_cats = [
        {
            'name': 'Pre Sales Design',
            'slug': 'pre-sales-design',
            'short_description': 'Professional solar design support for EPC companies during the pre-sales stage.',
            'full_description': 'EarthX provides comprehensive pre-sales design services that help EPC companies present compelling solar proposals to clients. Our pre-sales designs include realistic 3D visualizations and precise 2D layouts that improve sales conversion rates.',
            'icon': 'presentation',
            'hero_heading': 'Pre Sales Design',
            'hero_subtitle': 'Professional solar design support for EPC companies during the pre-sales stage. Win more projects with compelling visualizations and precise layouts.',
            'hero_image': '/uploads/residential_3d_featured.png',
            'hero_bg_image': '/uploads/residential_3d_featured.png',
            'display_order': 1
        },
        {
            'name': '3D Post Sales Design',
            'slug': '3d-post-sales-design',
            'short_description': 'Detailed 3D solar installation models for execution-ready project documentation.',
            'full_description': 'Our 3D post-sales design creates highly detailed, accurate models of the solar installation for construction and execution planning, providing exact visual references for installers and developers.',
            'icon': 'box',
            'hero_heading': '3D Post Sales Design',
            'hero_subtitle': 'Convert approved solar concepts into detailed, execution-ready 3D designs with comprehensive engineering documentation.',
            'hero_image': '/uploads/commercial_solar_featured.png',
            'hero_bg_image': '/uploads/commercial_solar_featured.png',
            'display_order': 2
        },
        {
            'name': 'Detailed Plan Design , Engineering & Consultancy',
            'slug': 'detailed-plan-design-engineering-consultancy',
            'short_description': 'Comprehensive solar engineering consultancy, detailed project planning, and technical advisory.',
            'full_description': 'Complete engineering consultancy and detailed design planning for commercial, industrial, and utility-scale solar installations, ensuring compliance with international engineering standards and site optimization.',
            'icon': 'compass',
            'hero_heading': 'Detailed Plan Design , Engineering & Consultancy',
            'hero_subtitle': 'Comprehensive solar design planning, detailed engineering specifications, and technical consultancy.',
            'hero_image': '/uploads/commercial_solar_featured.png',
            'hero_bg_image': '/uploads/commercial_solar_featured.png',
            'display_order': 3
        },
        {
            'name': 'CEIG Drawing Services',
            'slug': 'ceig-drawing-services',
            'short_description': 'CEIG approval drawing support and professional documentation for regulatory processes.',
            'full_description': 'EarthX provides design and documentation support for Chief Electrical Inspector to Government (CEIG) approval processes, including single-line diagrams, earthing layouts, and lightning protection.',
            'icon': 'file-check',
            'hero_heading': 'CEIG Drawing Services',
            'hero_subtitle': 'Government and electrical inspector approval drawings, compliance documentation, and grounding schematics.',
            'hero_image': '/uploads/sld_blueprint.png',
            'hero_bg_image': '/uploads/sld_blueprint.png',
            'display_order': 4
        },
        {
            'name': 'Ground Mounted Detailed Design',
            'slug': 'ground-mounted-detailed-design',
            'short_description': 'Comprehensive civil, structural, and electrical engineering for ground mount solar projects.',
            'full_description': 'EarthX delivers end-to-end ground-mounted solar design and engineering packages for commercial and utility-scale installations, covering site grading, inter-row spacing, racking, and evacuation.',
            'icon': 'mountain',
            'hero_heading': 'Ground Mounted Detailed Design',
            'hero_subtitle': 'End-to-end civil, structural, and electrical engineering for utility-scale and commercial ground mount installations.',
            'hero_image': '/uploads/ground_mount_featured.png',
            'hero_bg_image': '/uploads/ground_mount_featured.png',
            'display_order': 5
        },
        {
            'name': 'Electrical Calculation and Schedules',
            'slug': 'electrical-calculation-and-schedules',
            'short_description': 'Cable sizing, voltage drop, short circuit analysis, and comprehensive engineering schedules.',
            'full_description': 'Rigorous electrical calculations adhering to IEC, IEEE, and IS standards, ensuring safety, optimal cable sizing, earthing grid design, and complete BOQ schedules.',
            'icon': 'calculator',
            'hero_heading': 'Electrical Calculation and Schedules',
            'hero_subtitle': 'DC and AC cable sizing, voltage drop calculations, fault analysis, and procurement schedules.',
            'hero_image': '/uploads/sld_blueprint.png',
            'hero_bg_image': '/uploads/sld_blueprint.png',
            'display_order': 6
        },
        {
            'name': 'Substation and Evacuation Design',
            'slug': 'substation-and-evacuation-design',
            'short_description': 'Plant pooling substations, switchyard engineering, transmission lines, and grid evacuation design.',
            'full_description': 'Complete engineering for solar plant pooling substations (33kV to 220kV), switchyard layouts, transmission line routing, SCADA/telemetry architecture, and statutory evacuation clearance.',
            'icon': 'radio',
            'hero_heading': 'Substation and Evacuation Design',
            'hero_subtitle': 'Pooling substations, switchyards, transmission lines, and grid power evacuation documentation.',
            'hero_image': '/uploads/ground_mount_featured.png',
            'hero_bg_image': '/uploads/ground_mount_featured.png',
            'display_order': 7
        },
        {
            'name': 'Shadow Analysis Report & Structure Stability Report',
            'slug': 'shadow-analysis-structure-stability-report',
            'short_description': 'Advanced 3D shadow analysis, solar path modeling, and STAAD Pro structural stability reports.',
            'full_description': 'Precise 3D solar shade simulations across seasonal sun trajectories combined with STAAD Pro structural stability calculations and wind load verification under extreme weather conditions.',
            'icon': 'sun',
            'hero_heading': 'Shadow Analysis Report & Structure Stability Report',
            'hero_subtitle': '3D yearly shadow profile simulations and STAAD Pro structural stability reports for maximum yield and safety.',
            'hero_image': '/uploads/residential_3d_featured.png',
            'hero_bg_image': '/uploads/residential_3d_featured.png',
            'display_order': 8
        }
    ]

    for cat in service_cats:
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO service_categories (name, slug, short_description, full_description, icon, hero_heading, hero_subtitle, display_order, hero_image, hero_bg_image)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cat['name'], cat['slug'], cat['short_description'], cat['full_description'], cat['icon'], cat['hero_heading'], cat['hero_subtitle'], cat['display_order'], cat.get('hero_image', ''), cat.get('hero_bg_image', '')))
        except Exception as e:
            print(f"[SEED ERROR] Category {cat.get('name')}: {e}")

    try:
        cat_rows = cursor.execute("SELECT id, slug FROM service_categories").fetchall()
        cat_ids = {row['slug']: row['id'] for row in cat_rows}
    except Exception as e:
        cat_ids = {}

    child_services = [
        {
            'cat_slug': 'pre-sales-design',
            'name': '3D Pre Sales Visualization',
            'slug': '3d-pre-sales-visualization',
            'short_description': 'Realistic 3D solar visualizations for client presentations and sales proposals.',
            'full_description': 'Our 3D pre-sales design service creates photorealistic visualizations of proposed solar installations, helping EPC companies communicate their vision clearly and close deals faster.',
            'icon': 'box',
            'features': json.dumps([
                'Detailed 3D modeling of the project site',
                'Building and rooftop modeling with realistic textures',
                'Solar panel placement visualization',
                'Mounting structure rendering',
                'Client presentation-ready views & renderings'
            ]),
            'benefits': json.dumps(['Higher client conversion rates', 'Professional proposal presentations', 'Clear project visualization']),
            'deliverables': json.dumps(['3D rendered views', 'Site model', 'Presentation-ready images']),
            'display_order': 1
        },
        {
            'cat_slug': 'pre-sales-design',
            'name': '2D GA Layout Design',
            'slug': '2d-ga-layout-design',
            'short_description': 'Professional 2D General Arrangement layouts for project planning and client proposals.',
            'full_description': 'Our 2D GA layout service provides precise, professional solar layouts that are perfect for client presentations and initial project planning.',
            'icon': 'layout-grid',
            'features': json.dumps([
                'Professional 2D General Arrangement layouts',
                'Solar module placement optimization',
                'Row spacing and panel orientation',
                'Roof boundaries, setbacks, and walkway allocations',
                'Clear drawings for client presentations and project planning'
            ]),
            'benefits': json.dumps(['Optimized panel layouts', 'Professional documentation', 'Clear project planning']),
            'deliverables': json.dumps(['2D GA layout drawings', 'Module arrangement plans', 'Dimensioned layouts']),
            'display_order': 2
        },
        {
            'cat_slug': '3d-post-sales-design',
            'name': 'Execution-Ready 3D Solar Model',
            'slug': 'execution-ready-3d-model',
            'short_description': 'Detailed 3D solar installation models for execution-ready project documentation.',
            'full_description': 'Our 3D post-sales design creates highly detailed, accurate models of the solar installation for construction and execution planning.',
            'icon': 'box',
            'features': json.dumps([
                'Detailed 3D solar installation model',
                'Accurate rooftop/site geometry representation',
                'Module placement and string grouping visualization',
                'Inverter and DC combiner equipment positioning',
                'Construction reference renders'
            ]),
            'benefits': json.dumps(['Execution-ready visualization', 'Accurate site representation', 'Construction planning support']),
            'deliverables': json.dumps(['3D installation model', 'Equipment layout views', 'Construction reference renders']),
            'display_order': 1
        },
        {
            'cat_slug': '3d-post-sales-design',
            'name': 'Rooftop Detailed Design',
            'slug': 'rooftop-detailed-design',
            'short_description': 'Comprehensive rooftop solar layouts with detailed engineering specifications.',
            'full_description': 'Complete detailed rooftop solar design covering every aspect of the installation from module arrangement to equipment placement.',
            'icon': 'home',
            'features': json.dumps([
                'Detailed Electrical layouts and cable routing',
                'Detailed civil and structural design',
                'BoQ, specifications and construction documentation',
                'Design coordination and interface management'
            ]),
            'benefits': json.dumps(['Maximum roof utilization', 'Code-compliant designs', 'Installation-ready documentation']),
            'deliverables': json.dumps(['Detailed rooftop layout', 'Module arrangement plan', 'Equipment placement drawings']),
            'display_order': 2
        },
        {
            'cat_slug': 'detailed-plan-design-engineering-consultancy',
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
            'display_order': 1
        },
        {
            'cat_slug': 'detailed-plan-design-engineering-consultancy',
            'name': 'Site Grading, Drainage & Civil Engineering',
            'slug': 'site-grading-drainage-civil',
            'short_description': 'Site grading, hydrology analysis, storm-water drainage design, and earthwork planning.',
            'full_description': 'Comprehensive civil engineering including Digital Elevation Modeling (DEM), cut-and-fill volume minimization, surface storm-water runoff drainage design, and foundation leveling.',
            'icon': 'compass',
            'features': json.dumps([
                'Site grading, drainage design, and foundation leveling',
                'Cut-and-fill optimization to minimize earth-moving costs',
                'Hydrological watershed analysis and peak discharge calculations',
                'Peripheral and inter-block drainage channels and culverts'
            ]),
            'benefits': json.dumps(['Prevents plant flooding & soil erosion', 'Minimizes costly earth moving', 'Safe civil foundation grading']),
            'deliverables': json.dumps(['Grading & Earthwork Plan', 'Hydrology & Storm Drainage Layout', 'Civil Cross-Section Drawings']),
            'display_order': 2
        },
        {
            'cat_slug': 'ceig-drawing-services',
            'name': 'CEIG Approval Drawing Package',
            'slug': 'ceig-drawing-package',
            'short_description': 'CEIG approval drawing support and professional documentation for regulatory processes.',
            'full_description': 'EarthX provides design and documentation support for CEIG approval processes, including all required electrical and layout documentation.',
            'icon': 'file-check',
            'features': json.dumps([
                'Chief Electrical Inspector to Government (CEIG) compliant SLDs',
                'Earthing layouts and lightning protection calculations',
                'Transformer and switchyard layout drawings',
                'Cable sizing, voltage drop, and protection coordination'
            ]),
            'benefits': json.dumps(['Streamlined approval process', 'Compliant documentation', 'First-time approval success']),
            'deliverables': json.dumps(['CEIG drawing package', 'Electrical documentation', 'Grounding/lightning layouts']),
            'display_order': 1
        },
        {
            'cat_slug': 'ground-mounted-detailed-design',
            'name': 'Ground Mount Layout & Spacing Design',
            'slug': 'gm-layout-spacing-design',
            'short_description': 'Detailed ground-mounted solar layouts with complete site engineering.',
            'full_description': 'Comprehensive ground mount solar design covering site layout, structure arrangement, precise row pitch, and detailed engineering documentation.',
            'icon': 'mountain',
            'features': json.dumps([
                'End-to-end solar farm layout and topography modeling',
                'Precise inter-row spacing calculations for maximum energy yield',
                'Ground-mount racking and foundation structural engineering for all soil conditions',
                'Plant access roads, internal drainage, and trench cross-sections'
            ]),
            'benefits': json.dumps(['Optimized site utilization', 'Cost-effective layouts', 'Construction-ready plans']),
            'deliverables': json.dumps(['Ground mount master layout', 'Structure arrangement drawings', 'Site civil plans']),
            'display_order': 1
        },
        {
            'cat_slug': 'electrical-calculation-and-schedules',
            'name': 'Electrical Calculations & Sizing Book',
            'slug': 'electrical-calculations-sizing-book',
            'short_description': 'Cable sizing, voltage drop, short circuit analysis, and comprehensive engineering schedules.',
            'full_description': 'Rigorous engineering calculations according to IEC, IEEE, and IS standards, ensuring system safety, optimal cable sizing (<1.5% DC drop, <1% AC drop), grounding grid resistance, and complete installation schedules.',
            'icon': 'calculator',
            'features': json.dumps([
                'DC string, main DC, and HT/LT AC cable sizing & schedule',
                'Short circuit fault level analysis and breaking capacity',
                'Earthing grid design & mesh resistance calculations (IEEE 80 / IS 3043)',
                'Comprehensive Cable Pull Schedule, Drum Schedule, and BOQ'
            ]),
            'benefits': json.dumps(['Zero cable undersizing risks', 'Guaranteed minimum power losses', 'Exact procurement quantities']),
            'deliverables': json.dumps(['Electrical Design Calculation Book', 'Cable Pull Schedule', 'Earthing Calculation Sheet']),
            'display_order': 1
        },
        {
            'cat_slug': 'substation-and-evacuation-design',
            'name': 'Substation & Power Evacuation Scheme',
            'slug': 'substation-evacuation-scheme',
            'short_description': 'Pooling substation, switchyard engineering, transmission lines, and grid evacuation design.',
            'full_description': 'Complete engineering for solar plant pooling substations (33kV to 220kV), switchyard layouts, transmission line towers, gantry structures, SCADA/telemetry systems, and statutory grid evacuation clearance documentation.',
            'icon': 'radio',
            'features': json.dumps([
                'Pooling Substation (PSS) electrical layout, elevations, and clearance diagrams',
                'Switchyard gantry structures, busbar arrangements, and isolators',
                'Overhead transmission line routing, tower spotting, and sag-tension engineering',
                'SCADA architecture, telemetry, RTU, and Power Plant Controller (PPC) interfaces'
            ]),
            'benefits': json.dumps(['Complete grid evacuation clearance', 'Utility-compliant substation design', 'Full telemetry & SCADA readiness']),
            'deliverables': json.dumps(['Substation Key SLD & Layout', 'Switchyard GA & Elevation Plans', 'Transmission Line Route Map']),
            'display_order': 1
        },
        {
            'cat_slug': 'shadow-analysis-structure-stability-report',
            'name': 'Shadow Analysis & Structural Stability Package',
            'slug': 'shadow-analysis-structural-stability-package',
            'short_description': 'Advanced 3D shadow analysis, solar path modeling, and STAAD Pro structural stability reports.',
            'full_description': 'Precise 3D solar shade simulations across seasonal sun trajectories combined with STAAD Pro structural stability calculations and wind load verification under extreme weather conditions.',
            'icon': 'sun',
            'features': json.dumps([
                '3D yearly solar path & shadow profile analysis',
                'STAAD Pro 3D structural analysis under IS 875 / ASCE 7-16 wind codes',
                'Geotechnical load verification and pile depth optimization',
                'Near-shading 3D loss diagrams and string grouping analysis'
            ]),
            'benefits': json.dumps(['Eliminates inter-row shade losses', '25+ year structural stability', 'Optimized steel material weight']),
            'deliverables': json.dumps(['Shadow Analysis Report', 'STAAD Pro Stability Report', 'Structural Fabrication Drawings']),
            'display_order': 1
        }
    ]

    for svc in child_services:
        cat_id = cat_ids.get(svc.get('cat_slug'))
        if not cat_id:
            continue
        try:
            cursor.execute("""
                INSERT OR IGNORE INTO services (category_id, name, slug, short_description, full_description, icon, features, benefits, deliverables, display_order)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (cat_id, svc['name'], svc['slug'], svc['short_description'], svc['full_description'], svc['icon'], svc['features'], svc['benefits'], svc['deliverables'], svc['display_order']))
        except Exception as e:
            print(f"[SEED ERROR] Service {svc.get('name')}: {e}")

    try:
        conn.commit()
    except Exception:
        pass
    print("[SEED] Service categories and services successfully seeded.")
    return True

def init_db(data_dir=None):
    global CONFIGURED_DATA_DIR
    if data_dir:
        CONFIGURED_DATA_DIR = data_dir
        
    db_path = os.path.join(CONFIGURED_DATA_DIR, 'database.db')
    uploads_dir = os.path.join(CONFIGURED_DATA_DIR, 'uploads')
    
    copy_generated_images(uploads_dir)
    
    conn = get_db_connection()
    
    # Check if database already initialized
    user_count = 0
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM users")
        row = cursor.fetchone()
        if row:
            user_count = row[0]
    except Exception as e:
        # Tables do not exist yet, execute schema
        try:
            with open(SCHEMA_PATH, 'r') as f:
                conn.executescript(f.read())
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM users")
            row = cursor.fetchone()
            if row:
                user_count = row[0]
        except Exception as schema_err:
            print(f"[DATABASE INIT ERROR] Could not initialize schema: {schema_err}")
            return

    if user_count == 0:
        cursor = conn.cursor()
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
        
        # 5. Seed Client Logos
        client_logos = [
            ('Apex Solar EPC', '/uploads/client_apex_solar.svg', '', 1, 1),
            ('SunPeak Energy', '/uploads/client_sunpeak.svg', '', 2, 1),
            ('Nexus Power EPC', '/uploads/client_nexus_power.svg', '', 3, 1),
            ('Solaria Global', '/uploads/client_solaria.svg', '', 4, 1),
            ('Voltix Renewables', '/uploads/client_voltix.svg', '', 5, 1),
            ('TerraWatt Engineering', '/uploads/client_terrawatt.svg', '', 6, 1)
        ]
        cursor.executemany("""
            INSERT INTO client_logos (name, image, website_url, display_order, is_published)
            VALUES (?, ?, ?, ?, ?)
        """, client_logos)
        print("Client logos seeded.")
        
        conn.commit()

    # Always ensure service categories and options are seeded even if admin already exists
    seed_service_categories_and_services(conn)
    conn.close()

if __name__ == '__main__':
    init_db()
