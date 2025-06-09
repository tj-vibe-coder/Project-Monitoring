# app.py - Backend with Task Data Storage & API
# v10.0: Migrated back to SQLite from PostgreSQL for local development
# v9.4: Modified to serve ALL HTML files from the static folder.
# v9.3: Modified to serve index.html from the static folder.
# v9.2: Modified to serve login.html from the static folder.
# v9.1: Ensured /api/mrf/items/log endpoint and serving of mrf_items_log.html & mrf_items_log.js
# v9.0: Added /api/mrf/items/log endpoint and refined MRF item update/delete for mrf_items_log.html functionality.
# v8.9: Removed duplicate /login route definition.
# v8.8: Added MRF item status tracking (status, actual_delivery_date) and project-specific MRF monitoring page/API.
# v8.7: Added /api/test route for diagnostics.
# v8.6: Added MRF (Material Request Form) functionality - new tables and API endpoints.
# v8.5: Modified api_dashboard to calculate monthly forecast/invoiced totals.
# v8.4: Corrected syntax errors (removed trailing text).
# v8.3: Added /api/register endpoint for user creation.
# v8.2: Second attempt at corrected syntax errors.
# v8.1: Corrected syntax errors (indentation, missing elements)
# v8: Implemented Role-Based Access Control (RBAC)
# v7: Hardcoded specific LAN IP for host binding
# v6: Subtract percentage equivalent from project status when non-deduction forecast marked incomplete.
# v5: Fix NameError: name 'NaN' is not defined in calculation helpers.
# v4: Update project status based on forecast item's percentage equivalent when completed (if not deduction)
# Includes detailed logging in api_dashboard

import sqlite3
import json
from flask import (Flask, request, jsonify, send_from_directory, session,
                   redirect, url_for, flash)
import datetime
import os
import re
import csv
import io
import traceback
from math import isnan
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
# --- MRF Email PDF Endpoint ---
import smtplib
from email.message import EmailMessage

# --- Configuration ---
# SQLite Database Configuration
DATABASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'projects.db')

MAX_UPDATES_PER_PROJECT = 30
FORECAST_LIMIT = 100
STATIC_FOLDER_PATH = 'static' # Assumes static files are in a 'static' subdirectory
MIN_PASSWORD_LENGTH = 8

# Define User Roles
ADMIN = 'Administrator'
DS_ENGINEER = 'DS Engineer'
PROCUREMENT = 'Procurement'
FINANCE = 'Finance'
GUEST = 'Guest'
VALID_ROLES = [ADMIN, DS_ENGINEER, PROCUREMENT, FINANCE, GUEST]
MRF_MANAGEMENT_ROLES = [ADMIN, DS_ENGINEER, PROCUREMENT]
MRF_VIEW_ROLES = [ADMIN, DS_ENGINEER, PROCUREMENT, FINANCE, GUEST] # Roles that can view MRF status


# --- Flask App Initialization ---

# Define root-served HTML files (to be placed in the application root directory)
# This list is now empty as all HTML files will be in the static folder.
ROOT_SERVED_HTML_FILES = []

# Define static assets (CSS, JS, images, and ALL HTML files - to be placed in STATIC_FOLDER_PATH)
STATIC_ASSETS = [
    'style.css', 'script.js', 'login.js',
    'forecast.js', 'mrf_items_log.js',
    'project_gantt.js', 'favicon.ico',
    'CMRP Logo Light.svg', 'CMRP Logo Dark.svg',
    'login.html', 'index.html', # Moved from ROOT_SERVED_HTML_FILES
    'updates_log.html', 'project_gantt.html', # Moved from ROOT_SERVED_HTML_FILES
    'forecast.html', 'mrf_form.html', # Moved from ROOT_SERVED_HTML_FILES
    'project_mrf_status.html', 'mrf_items_log.html',
    'liquidation.html'  # Add the new liquidation page to static assets
]

# Determine the application root path (directory of this script)
application_root_dir = os.path.abspath(os.path.dirname(__file__))

# Create static folder if it doesn't exist
static_dir_full_path = os.path.join(application_root_dir, STATIC_FOLDER_PATH)
if not os.path.exists(static_dir_full_path):
    print(f"Warning: Static folder '{static_dir_full_path}' not found. Creating it.")
    try:
        os.makedirs(static_dir_full_path)
        print(f" -> Successfully created static folder: '{static_dir_full_path}'")
    except OSError as e:
        print(f"Error: Could not create static folder '{static_dir_full_path}': {e}")
else:
    print(f"Static folder '{static_dir_full_path}' already exists.")

# Check and create root-served HTML files (this loop will do nothing now as ROOT_SERVED_HTML_FILES is empty)
print("Checking/creating root-served HTML files...")
for filename in ROOT_SERVED_HTML_FILES:
    filepath = os.path.join(application_root_dir, filename)
    if not os.path.exists(filepath):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"<html><head><title>{filename}</title><!-- Ensure CSS/JS are linked with /static/ prefix if needed --></head><body>Placeholder for {filename}. If you see this, the real file is missing or not yet created.</body></html>")
            print(f" -> Created placeholder '{filename}' in '{application_root_dir}'.")
        except IOError as e:
            print(f"Error: Could not create root file '{filepath}': {e}")
    else:
        print(f" -> Root file '{filename}' already exists in '{application_root_dir}'.")


# Check and create static assets in the static folder
print(f"Checking/creating static assets in '{static_dir_full_path}'...")
for filename in STATIC_ASSETS:
    filepath = os.path.join(static_dir_full_path, filename)
    if not os.path.exists(filepath):
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                if filename.endswith('.js'):
                    f.write(f"// Placeholder for {filename}\nconsole.log('{filename} loaded.');")
                elif filename.endswith('.html'): # Handle HTML files in static assets
                    f.write(f"<html><head><title>{filename}</title></head><body>Placeholder for static HTML file: {filename}</body></html>")
                elif filename.endswith('.svg'):
                    f.write(f'<!-- Placeholder for {filename} -->\n<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#ccc"/><text x="10" y="50">Placeholder</text></svg>')
                elif filename.endswith('.ico'):
                    pass # Empty file for placeholder
                elif filename.endswith('.css'):
                    f.write(f"/* Placeholder for {filename} */\nbody {{ font-family: sans-serif; margin: 0; padding: 0; background-color: #f4f4f4; color: #333; }}")
                else:
                    f.write(f"/* Placeholder for {filename} */")
            print(f" -> Created placeholder '{filename}' in '{static_dir_full_path}'.")
        except IOError as e:
            print(f"Error: Could not create static file '{filepath}': {e}")
    else:
        print(f" -> Static asset '{filename}' already exists in '{static_dir_full_path}'.")

app = Flask(__name__, static_folder=STATIC_FOLDER_PATH, static_url_path='/static')

app.secret_key = os.environ.get('FLASK_SECRET_KEY', b'_5#y2L"F4Q8z\n\xec]/')
if app.secret_key == b'_5#y2L"F4Q8z\n\xec]/':
    print("WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production!")


# --- Database Management ---
def get_db():
    try:
        # Connect to the SQLite database
        conn = sqlite3.connect(
            DATABASE,
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        conn.row_factory = sqlite3.Row  # Enable named parameters
        return conn
    except sqlite3.Error as e:
        print(f"SQLite connection error: {e}")
        raise

def init_db():
    conn = None
    print("Attempting to initialize SQLite database schema...")
    try:
        conn = get_db()
        cursor = conn.cursor()
        # print(f"Database connection established to \'{DATABASE}\'.") # DATABASE var is removed
        
        # --- Users Table (SQLite syntax) ---
        print(" -> Checking \'users\' table...")
        # SQLite way to check if table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> Creating \'users\' table...")
            roles_str = "', '".join(VALID_ROLES)  # Keep this as is
            # Use INTEGER PRIMARY KEY AUTOINCREMENT for auto-incrementing primary key in SQLite
            # Use TEXT for strings
            cursor.execute(f"""
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN (\'{roles_str}\'))
                )
            """)
            # Index creation is similar
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_username ON users (username)")
            print(" -> \'users\' table created.")
        else:
             print(" -> \'users\' table already exists.")

        # --- Projects Table (SQLite syntax) ---
        print(" -> Checking \'projects\' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> Creating \'projects\' table...")
            cursor.execute("""
                CREATE TABLE projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ds TEXT,
                    year INTEGER,
                    project_no TEXT UNIQUE,
                    client TEXT,
                    project_name TEXT NOT NULL,
                    amount REAL,
                    status REAL NOT NULL DEFAULT 0.0 CHECK(status >= 0.0 AND status <= 100.0),
                    remaining_amount REAL,
                    total_running_weeks INTEGER,
                    po_date DATE, -- Use DATE type for dates
                    po_no TEXT,
                    date_completed DATE, -- Use DATE type for dates
                    pic TEXT,
                    address TEXT
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_no ON projects (project_no)")
            print(" -> \'projects\' table created.")
        else:
            print(" -> \'projects\' table already exists. Checking columns...")
            # SQLite doesn't have a straightforward way to check columns, so we try to ALTER and catch error if column exists
            try:
                cursor.execute("ALTER TABLE projects ADD COLUMN address TEXT")
                print(" -> Added \'address\' column to \'projects\'.")
            except sqlite3.Error as e:
                print(f" -> Could not add \'address\': {e}")

        # --- Project Updates Table (SQLite syntax) ---
        print(" -> Checking \'project_updates\' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_updates';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> Creating \'project_updates\' table...")
            cursor.execute("""
                CREATE TABLE project_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    update_text TEXT NOT NULL,
                    is_completed INTEGER NOT NULL DEFAULT 0 CHECK(is_completed IN (0, 1)), -- Or BOOLEAN type
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,                    completion_timestamp TIMESTAMP,
                    due_date DATE, -- Use DATE type
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_update_project_id ON project_updates (project_id)");
            print(" -> \'project_updates\' table created.")
        else:
            print(" -> \'project_updates\' table exists. Checking columns...")
            # Check for 'completion_timestamp'
            cursor.execute("PRAGMA table_info(project_updates);")
            columns = [column[1] for column in cursor.fetchall()]
            if 'completion_timestamp' not in columns:
                try:
                    cursor.execute("ALTER TABLE project_updates ADD COLUMN completion_timestamp TIMESTAMP")
                    print(" -> Added \'completion_timestamp\'.")
                except sqlite3.Error as e:
                    print(f" -> Could not add \'completion_timestamp\': {e}")
            # Check for 'due_date'
            if 'due_date' not in columns:
                try:
                    cursor.execute("ALTER TABLE project_updates ADD COLUMN due_date DATE")
                    print(" -> Added \'due_date\'.")
                except sqlite3.Error as e:
                    print(f" -> Could not add \'due_date\': {e}")

        # --- Forecast Items Table (SQLite syntax) ---
        print(" -> Checking \'forecast_items\' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forecast_items';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> Creating \'forecast_items\' table...")
            cursor.execute("""
                CREATE TABLE forecast_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    forecast_date DATE, -- Use DATE type
                    forecast_input_type TEXT NOT NULL CHECK(forecast_input_type IN (\'percent\', \'amount\')),
                    forecast_input_value REAL NOT NULL,
                    is_forecast_completed INTEGER NOT NULL DEFAULT 0 CHECK(is_forecast_completed IN (0, 1)), -- Or BOOLEAN
                    is_deduction INTEGER NOT NULL DEFAULT 0 CHECK(is_deduction IN (0, 1)), -- Or BOOLEAN
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_forecast_project_id ON forecast_items (project_id)")
            print(" -> \'forecast_items\' table created.")
        else:
            print(" -> \'forecast_items\' table exists. Checking columns...")
            # Check for 'forecast_date'
            cursor.execute("PRAGMA table_info(forecast_items);")
            columns = [column[1] for column in cursor.fetchall()]
            if 'forecast_date' not in columns:
                try:
                    cursor.execute("ALTER TABLE forecast_items ADD COLUMN forecast_date DATE")
                    print(" -> Added \'forecast_date\' column to \'forecast_items\'.")
                except sqlite3.Error as e:
                    print(f" -> Could not add \'forecast_date\' column: {e}")
            # Check for 'is_deduction'
            if 'is_deduction' not in columns:
                try:
                    cursor.execute("ALTER TABLE forecast_items ADD COLUMN is_deduction INTEGER NOT NULL DEFAULT 0 CHECK(is_deduction IN (0, 1))")
                    print(" -> Added \'is_deduction\' column to \'forecast_items\'.")
                except sqlite3.Error as e:
                    print(f" -> Could not add \'is_deduction\' column: {e}")

        # --- Project Tasks Table (SQLite syntax) ---
        print(" -> Checking \'project_tasks\' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_tasks';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> Creating \'project_tasks\' table...")
            cursor.execute("""
                CREATE TABLE project_tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER NOT NULL,
                    task_name TEXT NOT NULL,
                    start_date DATE,
                    end_date DATE,
                    planned_weight REAL,
                    actual_start DATE,
                    actual_end DATE,
                    assigned_to TEXT,
                    parent_task_id INTEGER,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(parent_task_id) REFERENCES project_tasks(task_id) ON DELETE SET NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_project_id ON project_tasks (project_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_parent_id ON project_tasks (parent_task_id)")
            print(" -> \'project_tasks\' table created.")
        else:
            print(" -> \'project_tasks\' table exists. Checking columns...")
            # Check for 'assigned_to'
            cursor.execute("PRAGMA table_info(project_tasks);")
            columns = [column[1] for column in cursor.fetchall()]
            if 'assigned_to' not in columns:
                try:
                    cursor.execute("ALTER TABLE project_tasks ADD COLUMN assigned_to TEXT")
                    print(" -> Added \'assigned_to\'.")
                except sqlite3.Error as e:
                    print(f" -> Could not add \'assigned_to\': {e}")
            # Check for 'parent_task_id'
            if 'parent_task_id' not in columns:
                try:
                    cursor.execute("ALTER TABLE project_tasks ADD COLUMN parent_task_id INTEGER REFERENCES project_tasks(task_id) ON DELETE SET NULL")
                    # Index might already exist or be created with the FK, handle potential error or check first
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_parent_id ON project_tasks (parent_task_id)")
                    print(" -> Added \'parent_task_id\' and index.")
                except sqlite3.Error as e:
                    print(f" -> Could not add \'parent_task_id\': {e}")        # --- MRF Headers Table (SQLite syntax) ---
        print(" -> Checking \'mrf_headers\' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mrf_headers';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> Creating \'mrf_headers\' table...")
            cursor.execute("""
                CREATE TABLE mrf_headers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    form_no TEXT UNIQUE NOT NULL,
                    mrf_date DATE,
                    project_name TEXT,
                    project_number TEXT, -- Consider if this should reference projects.project_no directly
                    client TEXT,
                    site_location TEXT,
                    project_phase TEXT,
                    header_prepared_by_name TEXT,
                    header_prepared_by_designation TEXT,
                    header_approved_by_name TEXT,
                    header_approved_by_designation TEXT,
                    footer_prepared_by_name TEXT,
                    footer_prepared_by_designation TEXT,
                    footer_approved_by_name TEXT,
                    footer_approved_by_designation TEXT,
                    footer_noted_by_name TEXT,
                    footer_noted_by_designation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_number) REFERENCES projects(project_no) ON DELETE SET NULL
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrf_form_no ON mrf_headers (form_no)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrf_project_number ON mrf_headers (project_number)")
            print(" -> \'mrf_headers\' table created.")
        else:
            print(" -> \'mrf_headers\' table already exists.")

        # --- MRF Items Table (SQLite syntax) ---
        print(" -> Checking \'mrf_items\' table...")
        default_mrf_item_status = "Processing"
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mrf_items';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> \'mrf_items\' table not found, creating it...")
            cursor.execute(f"""
                CREATE TABLE mrf_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mrf_header_id INTEGER NOT NULL,
                    item_no TEXT,
                    part_no TEXT,
                    brand_name TEXT,
                    description TEXT,
                    qty REAL,
                    uom TEXT,
                    install_date DATE,
                    remarks TEXT,
                    status TEXT DEFAULT \'{default_mrf_item_status}\',
                    actual_delivery_date DATE,
                    FOREIGN KEY(mrf_header_id) REFERENCES mrf_headers(id) ON DELETE CASCADE
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrf_item_header_id ON mrf_items (mrf_header_id)")
            print(f" -> \'mrf_items\' table created with status (default \'{default_mrf_item_status}\') and delivery date.")
        else:
            print(" -> \'mrf_items\' table already exists. Checking for \'status\' and \'actual_delivery_date\' columns...")
            # Check for 'status'
            cursor.execute("PRAGMA table_info(mrf_items);")
            columns = [column[1] for column in cursor.fetchall()]
            if 'status' not in columns:
                try:
                    cursor.execute(f"ALTER TABLE mrf_items ADD COLUMN status TEXT DEFAULT \'{default_mrf_item_status}\'")
                    print(f" -> Added \'status\' column to \'mrf_items\' with default \'{default_mrf_item_status}\'.")
                except sqlite3.Error as e:
                    print(f" -> Could not add \'status\' column to \'mrf_items\': {e}")
            # Check for 'actual_delivery_date'
            if 'actual_delivery_date' not in columns:
                try:
                    cursor.execute("ALTER TABLE mrf_items ADD COLUMN actual_delivery_date DATE")
                    print(" -> Added \'actual_delivery_date\' column to \'mrf_items\'.")
                except sqlite3.Error as e:
                    print(f" -> Could not add \'actual_delivery_date\' column to \'mrf_items\': {e}")

        conn.commit()
        print("Database schema initialization/verification complete for SQLite.")

    except sqlite3.Error as e: # Catch sqlite3 specific errors
        print("!!!!!!!! ERROR DURING SQLITE DATABASE INITIALIZATION !!!!!!!!")
        print(f"Error initializing SQLite database: {e}")
        print(traceback.format_exc())
        if conn: conn.rollback()
    except Exception as e:
        print("!!!!!!!! UNEXPECTED ERROR DURING SQLITE DATABASE INITIALIZATION !!!!!!!!")
        print(f"An unexpected error occurred during SQLite DB init: {e}")
        print(traceback.format_exc())
        if conn: conn.rollback()
    finally:
        if conn:
            conn.close()
            print("SQLite database connection closed after init.")

# --- Authorization Decorator ---
def role_required(allowed_roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if 'user_id' not in session:
                if request.path.startswith('/api/'):
                     return jsonify({"error": "Authentication required. Please log in."}), 401
                else: 
                    flash("Please log in to access this page.", "warning")
                    session['next_url'] = request.url
                    return redirect(url_for('login_page_route'))

            user_role = session.get('role')
            if user_role not in allowed_roles:
                if request.path.startswith('/api/'):
                    return jsonify({"error": f"Forbidden: Your role ('{user_role}') does not have permission."}), 403
                else: 
                    flash(f"You do not have permission ({user_role}) to access this resource.", "danger")
                    return redirect(url_for('index')) # Redirect to index (which is now /static/index.html)
            return f(*args, **kwargs)
        return decorated_function
    return decorator

# --- Data Validation & Utility Functions ---
def safe_float(value, default=None):
    if value is None: return default
    str_value = str(value).replace(',', '').replace('%', '').strip()
    if str_value == '': return default
    try: return float(str_value)
    except (ValueError, TypeError): return default

def safe_int(value, default=None):
    float_val = safe_float(value, default=None)
    if float_val is None: return default
    try:
        if abs(float_val - round(float_val)) < 1e-9: # Check if it's effectively an integer
            return int(round(float_val))
        else:
            return int(float_val) # Truncate if it has a non-zero fractional part
    except (ValueError, TypeError):
        return default

def calculate_remaining(amount_val, status_percent_val):
    amount = safe_float(amount_val)
    status_percent = safe_float(status_percent_val)
    if amount is None or status_percent is None: return None
    status_percent = max(0.0, min(100.0, status_percent)) # Clamp status between 0 and 100
    return amount * (1 - status_percent / 100.0)

def is_valid_date_format(date_str):
    if not isinstance(date_str, str): return False
    return bool(re.match(r'^\d{4}-\d{2}-\d{2}$', date_str))

def parse_flexible_date(date_str):
    if not date_str or not isinstance(date_str, str):
        return None
    date_str = date_str.strip()
    try:
        return datetime.date.fromisoformat(date_str)
    except ValueError:
        try:
            dt_obj = datetime.datetime.strptime(date_str, '%m/%d/%Y')
            return dt_obj.date()
        except ValueError:
            return None 

# --- Forecast Calculation Helpers ---
def calculate_individual_forecast_amount(forecast_item_dict, project_amount):
    if not forecast_item_dict: return 0.0 
    proj_amt = safe_float(project_amount, float('nan')) 
    input_value = safe_float(forecast_item_dict.get('forecast_input_value'), 0.0)
    input_type = forecast_item_dict.get('forecast_input_type')
    is_deduction = bool(forecast_item_dict.get('is_deduction', False))
    forecast_amount = 0.0
    if input_type == 'percent':
        if isnan(proj_amt): return 0.0 
        forecast_amount = proj_amt * (input_value / 100.0)
    elif input_type == 'amount':
        forecast_amount = input_value
    else:
        print(f"Warning: Unknown forecast input type '{input_type}' in calculation.")
    multiplier = -1.0 if is_deduction else 1.0
    final_amount = forecast_amount * multiplier
    return 0.0 if isnan(final_amount) else final_amount 

def calculate_individual_forecast_percent(forecast_item_dict, project_amount):
    if not forecast_item_dict: return 0.0
    proj_amt = safe_float(project_amount, float('nan'))
    if isnan(proj_amt) or proj_amt == 0:
        return 0.0
    input_value = safe_float(forecast_item_dict.get('forecast_input_value'), 0.0)
    input_type = forecast_item_dict.get('forecast_input_type')
    is_deduction = bool(forecast_item_dict.get('is_deduction', False))
    percent = 0.0
    if input_type == 'percent':
        percent = input_value
    elif input_type == 'amount':
        percent = (input_value / proj_amt) * 100.0
    else:
        print(f"Warning: Unknown forecast input type '{input_type}' in percentage calculation.")
    multiplier = -1.0 if is_deduction else 1.0
    final_percent = percent * multiplier
    return 0.0 if isnan(final_percent) else final_percent 

# --- Helper Function to Process Project Rows ---
def _process_project_rows(project_rows, cursor, forecasted_project_ids):
    projects = []
    project_ids = [row['id'] for row in project_rows]
    updates_map = {pid: [] for pid in project_ids}
    latest_update_map = {}
    if project_ids:
        placeholders = ','.join(['?'] * len(project_ids))
        cursor.execute(f"""
            SELECT project_id, id as update_id, update_text, is_completed,
                   timestamp, completion_timestamp, due_date
            FROM project_updates
            WHERE project_id IN ({placeholders})
            ORDER BY project_id, timestamp DESC, id DESC
        """, tuple(project_ids))
        for update_row in cursor.fetchall():
            update_dict = dict(update_row)
            update_dict['is_completed'] = bool(update_dict['is_completed'])
            project_id = update_dict['project_id']
            if project_id in updates_map:
                updates_map[project_id].append(update_dict)
        cursor.execute(f"""
            SELECT p_id, update_text
            FROM (
                SELECT
                    pu.project_id as p_id,
                    pu.update_text,
                    ROW_NUMBER() OVER(PARTITION BY pu.project_id ORDER BY pu.timestamp DESC, pu.id DESC) as rn
                FROM project_updates pu
                WHERE pu.project_id IN ({placeholders})
            )
            WHERE rn = 1
        """, tuple(project_ids))
        for latest_row in cursor.fetchall():
            latest_update_map[latest_row['p_id']] = latest_row['update_text']
    today = datetime.date.today()
    for row in project_rows:
        project_dict = dict(row)
        project_id = project_dict['id']
        project_dict['updates'] = updates_map.get(project_id, [])
        project_dict['latest_update'] = latest_update_map.get(project_id, '')
        project_dict['has_forecasts'] = project_id in forecasted_project_ids
        calculated_weeks = None
        po_date_str = project_dict.get('po_date')
        completed_date_str = project_dict.get('date_completed')
        start_date = parse_flexible_date(po_date_str) 
        if start_date:
            end_date = today 
            completion_date = parse_flexible_date(completed_date_str)
            if completion_date:
                end_date = min(completion_date, today)
            if start_date <= end_date:
                delta = end_date - start_date
                calculated_weeks = (delta.days // 7) + 1
            else:
                calculated_weeks = 0 
        project_dict['total_running_weeks'] = calculated_weeks
        projects.append(project_dict)
    return projects

# --- API Test Route ---
@app.route('/api/test', methods=['GET'])
def api_test_route():
    print("--- /api/test route hit successfully! ---")
    return jsonify({"message": "API test route is working!"}), 200

# --- Authentication Endpoints ---
@app.route('/login')
def login_page_route(): 
    if 'user_id' in session:
        return redirect(url_for('index')) 
    # Serve login.html from the static folder
    return send_from_directory(app.static_folder, 'login.html')


@app.route('/api/login', methods=['POST'])
def handle_login():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data:
        return jsonify({"error": "Missing username or password"}), 400
    username = data.get('username', '').strip() 
    password = data.get('password') 
    if not username or not password: 
       return jsonify({"error": "Username and password cannot be empty"}), 400
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, username, password_hash, role FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()
        if user and check_password_hash(user['password_hash'], password):
            session.clear() 
            session['user_id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']
            session.permanent = True 
            app.permanent_session_lifetime = datetime.timedelta(days=31) 
            print(f"Login successful for user: {username}, Role: {user['role']}")
            next_url = session.pop('next_url', None) or url_for('static', filename='index.html')
            return jsonify({"message": f"Login successful! Welcome {user['username']}.", "redirect_url": next_url}), 200
        else:
            print(f"Login failed for username: {username}")
            return jsonify({"error": "Invalid username or password"}), 401 
    except sqlite3.Error as db_err:
        print(f"Database error during login: {db_err}")
        traceback.print_exc()
        return jsonify({"error": "Database error during login."}), 500
    except Exception as e:
        print(f"Unexpected error during login: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred during login."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/logout', methods=['POST']) 
@role_required(VALID_ROLES) 
def logout():
    username = session.get('username', 'Unknown')
    session.clear()
    print(f"User {username} logged out.")
    return jsonify({"message": "Logout successful."}), 200

@app.route('/api/user/profile', methods=['GET'])
@role_required(VALID_ROLES) 
def get_user_profile():
    return jsonify({
        "user_id": session['user_id'],
        "username": session['username'],
        "role": session['role']
    }), 200

@app.route('/api/register', methods=['POST'])
def handle_register():
    data = request.get_json()
    if not data or 'username' not in data or 'password' not in data or 'role' not in data:
        return jsonify({"error": "Missing username, password, or role"}), 400
    username = data.get('username', '').strip()
    password = data.get('password') 
    role = data.get('role')
    if not username:
        return jsonify({"error": "Username cannot be empty."}), 400
    if not password or len(password) < MIN_PASSWORD_LENGTH:
        return jsonify({"error": f"Password must be at least {MIN_PASSWORD_LENGTH} characters long."}), 400
    if role not in VALID_ROLES:
        return jsonify({"error": f"Invalid role selected. Must be one of: {', '.join(VALID_ROLES)}"}), 400
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()
        if existing_user:
            return jsonify({"error": "Username already taken. Please choose another."}), 409 
        password_hash = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                       (username, password_hash, role))
        conn.commit()
        print(f"New user registered: Username='{username}', Role='{role}'")
        return jsonify({"message": "Account created successfully. You can now log in."}), 201 
    except sqlite3.IntegrityError: 
       if conn: conn.rollback()
       print(f"Registration failed for '{username}' due to integrity error (likely username taken).")
       return jsonify({"error": "Username already taken. Please choose another."}), 409
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"Database error during registration: {db_err}")
        traceback.print_exc()
        return jsonify({"error": "Database error during registration."}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error during registration: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred during registration."}), 500
    finally:
        if conn: conn.close()


# --- Project Endpoints ---
@app.route('/api/projects', methods=['GET'])
@role_required(VALID_ROLES)
def get_projects():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Fetch projects that are not yet completed
        # Assuming 'date_completed' is NULL or in the future for active projects
        # Or, if you have a specific status column, filter by that.
        # For now, let's fetch all projects and the frontend can filter if needed,
        # or we can add a filter here later.
        cursor.execute("SELECT * FROM projects WHERE date_completed IS NULL ORDER BY id DESC")
        project_rows = cursor.fetchall()

        # Get IDs of projects that have forecast entries
        cursor.execute("SELECT DISTINCT project_id FROM forecast_items")
        forecasted_ids_rows = cursor.fetchall()
        forecasted_project_ids = {row['project_id'] for row in forecasted_ids_rows}

        # Process rows using the helper function
        projects_list = _process_project_rows(project_rows, cursor, forecasted_project_ids)
        
        return jsonify(projects_list), 200

    except sqlite3.Error as db_err:
        print(f"Database error in /api/projects: {db_err}")
        traceback.print_exc()
        return jsonify({"error": "Database error fetching projects."}), 500
    except Exception as e:
        print(f"Unexpected error in /api/projects: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred fetching projects."}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/projects/completed', methods=['GET'])
@role_required(VALID_ROLES)
def get_completed_projects():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()

        # Fetch projects that are completed
        cursor.execute("SELECT * FROM projects WHERE date_completed IS NOT NULL ORDER BY date_completed DESC, id DESC")
        project_rows = cursor.fetchall()

        # Get IDs of projects that have forecast entries (might still be relevant for completed projects)
        cursor.execute("SELECT DISTINCT project_id FROM forecast_items")
        forecasted_ids_rows = cursor.fetchall()
        forecasted_project_ids = {row['project_id'] for row in forecasted_ids_rows}

        projects_list = _process_project_rows(project_rows, cursor, forecasted_project_ids)
        
        return jsonify(projects_list), 200

    except sqlite3.Error as db_err:
        print(f"Database error in /api/projects/completed: {db_err}")
        traceback.print_exc()
        return jsonify({"error": "Database error fetching completed projects."}), 500
    except Exception as e:
        print(f"Unexpected error in /api/projects/completed: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred fetching completed projects."}), 500
    finally:
        if conn:
            conn.close()

# --- Helper Function for Processing Project Data (Used by Bulk/CSV Upload) ---
def _process_and_save_project(project_data, row_num, cursor, existing_projects_map):
    # Placeholder for helper function
    pass

@app.route('/api/projects/upload', methods=['POST'])
@role_required([ADMIN])
def upload_projects():
    return jsonify({"message": "Upload projects endpoint placeholder. Implement logic."}), 200

@app.route('/api/projects/bulk', methods=['POST'])
@role_required([ADMIN])
def add_projects_bulk():
    return jsonify({"message": "Bulk add projects endpoint placeholder. Implement logic."}), 200

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
@role_required([ADMIN, DS_ENGINEER])
def update_project_field(project_id):
    return jsonify({"message": f"Update project {project_id} endpoint placeholder. Implement logic."}), 200

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
@role_required([ADMIN])
def delete_project(project_id):
    return jsonify({"message": f"Delete project {project_id} endpoint placeholder. Implement logic."}), 200

@app.route('/api/projects/<int:project_id>/details', methods=['GET'])
@role_required(VALID_ROLES)
def get_project_details(project_id):
    return jsonify({"message": f"Get project details for {project_id} endpoint placeholder. Implement logic."}), 200

# --- Project Update Endpoints ---
@app.route('/api/projects/<int:project_id>/updates', methods=['GET'])
@role_required(VALID_ROLES)
def get_project_updates(project_id):
    return jsonify({"message": f"Get updates for project {project_id} endpoint placeholder. Implement logic."}), 200

@app.route('/api/projects/<int:project_id>/updates', methods=['POST'])
@role_required([ADMIN, DS_ENGINEER])
def add_project_update(project_id):
    conn = None
    try:
        return jsonify({"message": f"Add update for project {project_id} endpoint placeholder. Implement logic."}), 200
    except sqlite3.Error as db_err:
        return jsonify({"error": str(db_err)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/updates/<int:update_id>/complete', methods=['PUT'])
@role_required([ADMIN, DS_ENGINEER])
def toggle_update_completion(update_id):
    conn = None
    try:
        return jsonify({"message": f"Toggle completion for update {update_id} endpoint placeholder. Implement logic."}), 200
    except sqlite3.Error as db_err:
        return jsonify({"error": str(db_err)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/updates/<int:update_id>', methods=['DELETE'])
@role_required([ADMIN, DS_ENGINEER])
def delete_project_update(update_id):
    conn = None
    try:
        return jsonify({"message": f"Delete update {update_id} endpoint placeholder. Implement logic."}), 200
    except sqlite3.Error as db_err:
        return jsonify({"error": str(db_err)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# --- Updates Log Endpoint ---
@app.route('/api/updates/log', methods=['GET'])
@role_required(VALID_ROLES)
def get_updates_log():
    log_entries = []
    conn = None
    try:
        return jsonify({"message": "Updates log endpoint placeholder. Implement logic.", "log_entries": log_entries}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# --- Forecast Endpoints ---
@app.route('/api/forecast', methods=['GET'])
@role_required(VALID_ROLES)
def get_forecast_items():
    forecast_items_list = []
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Join forecast_items with projects to get complete data
        cursor.execute("""
            SELECT 
                f.*,
                p.project_no,
                p.project_name,
                p.amount as project_amount,
                p.pic as project_pic,
                p.status as project_status
            FROM forecast_items f
            LEFT JOIN projects p ON f.project_id = p.id
            ORDER BY f.forecast_date
        """)
        rows = cursor.fetchall()
        
        for row in rows:
            item = dict(row)
            # Add forecast_entry_id for frontend compatibility
            item['forecast_entry_id'] = item['id']
            forecast_items_list.append(item)
        
        return jsonify(forecast_items_list), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/forecast', methods=['POST'])
@role_required([ADMIN, DS_ENGINEER])
def add_forecast_item():
    conn = None
    data = request.get_json()
    
    required_fields = ['project_id', 'forecast_input_type', 'forecast_input_value', 'forecast_date']
    for field in required_fields:
        if field not in data:
            return jsonify({"error": f"Missing required field: {field}"}), 400
            
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Validate project exists
        cursor.execute("SELECT id FROM projects WHERE id = ?", (data['project_id'],))
        if not cursor.fetchone():
            return jsonify({"error": "Invalid project_id"}), 400
            
        # Validate input type
        if data['forecast_input_type'] not in ['percent', 'amount']:
            return jsonify({"error": "Invalid forecast_input_type. Must be 'percent' or 'amount'"}), 400
            
        # Insert forecast item
        cursor.execute("""
            INSERT INTO forecast_items (
                project_id,
                forecast_date,
                forecast_input_type,
                forecast_input_value,
                is_deduction
            ) VALUES (?, ?, ?, ?, ?)
        """, (
            data['project_id'],
            data['forecast_date'],
            data['forecast_input_type'],
            float(data['forecast_input_value']),
            bool(data.get('is_deduction', False))
        ))
        conn.commit()
        
        return jsonify({
            "message": "Forecast item added successfully",
            "id": cursor.lastrowid
        }), 201
        
    except sqlite3.Error as db_err:
        return jsonify({"error": str(db_err)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/forecast/entry/<int:entry_id>', methods=['DELETE'])
@role_required([ADMIN, DS_ENGINEER])
def remove_single_forecast_entry(entry_id):
    conn = None
    try:
        return jsonify({"message": f"Remove forecast entry {entry_id} endpoint placeholder. Implement logic."}), 200
    except sqlite3.Error as db_err:
        return jsonify({"error": str(db_err)}), 500
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        if conn:
            conn.close()

# --- MRF (Material Request Form) Endpoints ---
# (Placeholder for MRF Endpoints - to be added or verified)

# --- Gantt Chart Endpoints ---
# (Placeholder for Gantt Chart Endpoints - to be added or verified)

# --- Favicon and Static Files ---
@app.route('/favicon.ico')
def favicon():
    return send_from_directory(os.path.join(app.root_path, 'static'),
                               'favicon.ico', mimetype='image/vnd.microsoft.icon')

# --- Serve any HTML file from static folder if it exists ---
@app.route('/<path:filename>')
def serve_static_html(filename):
    if filename.endswith('.html'):
        static_path = os.path.join(app.static_folder, filename)
        if os.path.isfile(static_path):
            return send_from_directory(app.static_folder, filename)
    # If not found or not .html, fall through to other routes/404
    return not_found(404)

# --- Catch-all for SPA (Single Page Application) routing and 404s ---
# This should be one of the LAST routes defined.
@app.errorhandler(404)
def not_found(e):
    # If the request path looks like an API call, return JSON 404
    if request.path.startswith('/api/'):
        return jsonify(error='Not found'), 404
    # Otherwise, assume it's a frontend route and serve index.html
    # This helps with SPAs that handle their own routing client-side.
    return send_from_directory(app.static_folder, 'index.html')

# --- Dashboard Endpoint ---
@app.route('/api/dashboard', methods=['GET'])
@role_required(VALID_ROLES)
def api_dashboard():
    print("\n--- Calculating Dashboard Metrics (with Monthly Breakdown) ---")
    metrics = {
        "total_remaining": 0.0, 
        "monthly_actual_invoiced": {month: 0.0 for month in range(1, 13)}, 
        "monthly_total_forecast": {month: 0.0 for month in range(1, 13)},  
        "completed_this_year_count": 0,
        "total_active_projects_count": 0,
        "new_projects_count": 0
    }
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        active_count, completed_this_year_count, new_projects_count = 0, 0, 0
        total_remaining_active = 0.0
        today = datetime.date.today()
        current_year = today.year
        current_year_str = str(current_year) 
        date_15_days_ago = today - datetime.timedelta(days=15)
        cursor.execute("SELECT id, status, po_date, date_completed, remaining_amount FROM projects")
        all_projects = cursor.fetchall()
        print(f"[Dashboard] Processing {len(all_projects)} projects for counts/remaining...")
        for project in all_projects:
            status_val = safe_float(project['status'], default=0.0)
            completed_date = parse_flexible_date(project['date_completed'])
            po_date = parse_flexible_date(project['po_date'])
            is_active = status_val < 100.0 and completed_date is None
            if is_active:
                active_count += 1
                remaining = safe_float(project['remaining_amount'])
                if remaining is not None: total_remaining_active += remaining
            if completed_date and completed_date.year == current_year:
                completed_this_year_count += 1
            if po_date and po_date >= date_15_days_ago:
                new_projects_count += 1
        metrics["total_active_projects_count"] = active_count
        metrics["completed_this_year_count"] = completed_this_year_count
        metrics["new_projects_count"] = new_projects_count
        metrics["total_remaining"] = total_remaining_active
        print(f"[Dashboard] Counts: Active={active_count}, Completed={completed_this_year_count}, New={new_projects_count}")
        print(f"[Dashboard] Total Remaining: {total_remaining_active:.2f}")
        print(f"[Dashboard] Calculating monthly totals for year: {current_year_str}...")
        cursor.execute("""
            SELECT
                fi.forecast_date,
                fi.forecast_input_type,
                fi.forecast_input_value,
                fi.is_forecast_completed,
                fi.is_deduction,
                p.amount as project_amount
            FROM forecast_items fi
            JOIN projects p ON fi.project_id = p.id
            WHERE strftime('%Y', fi.forecast_date) = ?
        """, (current_year_str,))
        forecast_items_this_year = cursor.fetchall()
        print(f"[Dashboard] Fetched {len(forecast_items_this_year)} forecast items for {current_year_str}.")
        for item_row in forecast_items_this_year:
            try:
                forecast_date_str = item_row['forecast_date']
                forecast_date_obj = parse_flexible_date(forecast_date_str)
                if forecast_date_obj:
                    month = forecast_date_obj.month
                    project_amount = safe_float(item_row['project_amount'], float('nan')) 
                    item_dict = dict(item_row) 
                    calculated_amount = calculate_individual_forecast_amount(item_dict, project_amount)
                    metrics["monthly_total_forecast"][month] += calculated_amount
                    if item_row['is_forecast_completed']:
                        metrics["monthly_actual_invoiced"][month] += calculated_amount
                else:
                     print(f"[Dashboard] Warning: Could not parse forecast_date '{forecast_date_str}' for calculation.")
            except Exception as e:
                print(f"[Dashboard] Error processing forecast item {item_row}: {e}")
        print(f"[Dashboard] Monthly Forecast Totals: {json.dumps(metrics['monthly_total_forecast'], indent=2)}")
        print(f"[Dashboard] Monthly Invoiced Totals: {json.dumps(metrics['monthly_actual_invoiced'], indent=2)}")
        # --- Backlogs per Client ---
        try:
            cursor.execute("""
                SELECT client, SUM(remaining_amount) as total_backlog
                FROM projects
                WHERE (status < 100.0 OR status IS NULL) AND (date_completed IS NULL)
                GROUP BY client
            """)
            backlog_rows = cursor.fetchall()
            metrics["backlogs_per_client"] = {row["client"]: row["total_backlog"] for row in backlog_rows if row["client"]}
            print(f"[Dashboard] Backlogs per client: {json.dumps(metrics['backlogs_per_client'], indent=2)}")
        except Exception as e:
            print(f"[Dashboard] Error calculating backlogs per client: {e}")
            metrics["backlogs_per_client"] = {}
    except sqlite3.Error as db_err:
        print(f"[Dashboard] DB error: {db_err}")
        traceback.print_exc()
        return jsonify({"error": f"DB error calculating metrics: {db_err}", "metrics": metrics}), 500
    except Exception as e:
        print(f"[Dashboard] Unexpected error: {e}")
        traceback.print_exc()
        return jsonify({"error": f"Error calculating metrics: {e}", "metrics": metrics}), 500
    finally:
        if conn: conn.close()
    print(f"[Dashboard] Returning Final Metrics: {json.dumps(metrics, indent=2)}")
    print("--- End Dashboard ---")
    return jsonify(metrics)

# --- MRF Email PDF Endpoint ---
@app.route('/api/mrf/email', methods=['POST'])
@role_required(VALID_ROLES)
def email_mrf_pdf():
    data = request.get_json()
    mrf_id = data.get('mrf_id')
    recipient = data.get('email')
    if not mrf_id or not recipient:
        return jsonify({'error': 'Missing MRF ID or email address'}), 400

    # Example: PDF path (adjust as needed)
    pdf_path = f'CSV/mrf_{mrf_id}.pdf'
    if not os.path.exists(pdf_path):
        return jsonify({'error': f'PDF for MRF {mrf_id} not found on server.'}), 404

    try:
        msg = EmailMessage()
        msg['Subject'] = f'MRF Form #{mrf_id}'
        msg['From'] = 'your_email@example.com'
        msg['To'] = recipient
        msg.set_content('Please find the attached MRF PDF.')
        with open(pdf_path, 'rb') as f:
            msg.add_attachment(f.read(), maintype='application', subtype='pdf', filename=os.path.basename(pdf_path))
        with smtplib.SMTP('smtp.yourprovider.com', 587) as smtp:
            smtp.starttls()
            smtp.login('your_email@example.com', 'your_password')
            smtp.send_message(msg)
        return jsonify({'message': 'Email sent successfully!'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# --- MRF Load Endpoint ---
@app.route('/api/mrf/<int:mrf_id>', methods=['GET'])
@role_required(VALID_ROLES)
def get_mrf_header(mrf_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mrf_headers WHERE id = ?", (mrf_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': f'MRF with id {mrf_id} not found.'}), 404
        header = dict_keys_to_camel_case(dict(row))
        # Fetch items for this MRF
        cursor.execute("SELECT * FROM mrf_items WHERE mrf_header_id = ? ORDER BY item_no ASC", (mrf_id,))
        items = [dict_keys_to_camel_case(dict(item)) for item in cursor.fetchall()]
        return jsonify({'header': header, 'items': items}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

# --- MRF Create Endpoint ---
@app.route('/api/mrf', methods=['POST'])
@role_required(VALID_ROLES)
def create_mrf():
    data = request.get_json()
    print('--- /api/mrf POST received ---')
    print('Incoming data:', json.dumps(data, indent=2, default=str))
    if not data:
        print('No data provided to /api/mrf')
        return jsonify({'error': 'No data provided'}), 400
    header = data.get('header')
    items = data.get('items', [])
    if not header:
        print('Missing MRF header data in /api/mrf')
        return jsonify({'error': 'Missing MRF header data'}), 400
    # Auto-generate form_no if missing or empty
    form_no = header.get('form_no')
    if not form_no or str(form_no).strip() == '':
        # Generate a unique form_no: MRF-YYYYMMDD-<next_id>
        today_str = datetime.date.today().strftime('%Y%m%d')
        try:
            conn = get_db()
            cursor = conn.cursor()
            cursor.execute("SELECT MAX(id) FROM mrf_headers")
            max_id = cursor.fetchone()[0] or 0
            form_no = f"MRF-{today_str}-{max_id+1}"
            print(f"Auto-generated form_no: {form_no}")
            if conn:
                conn.close()
        except Exception as e:
            print('Error auto-generating form_no:', str(e))
            form_no = f"MRF-{today_str}-X"
        header['form_no'] = form_no
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        # Insert header
        cursor.execute("""
            INSERT INTO mrf_headers (
                form_no, mrf_date, project_name, project_number, client, site_location, project_phase,
                header_prepared_by_name, header_prepared_by_designation,
                header_approved_by_name, header_approved_by_designation,
                footer_prepared_by_name, footer_prepared_by_designation,
                footer_approved_by_name, footer_approved_by_designation,
                footer_noted_by_name, footer_noted_by_designation
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            header.get('form_no'),
            header.get('mrf_date'),
            header.get('project_name'),
            header.get('project_number'),
            header.get('client'),
            header.get('site_location'),
            header.get('project_phase'),
            header.get('header_prepared_by_name'),
            header.get('header_prepared_by_designation'),
            header.get('header_approved_by_name'),
            header.get('header_approved_by_designation'),
            header.get('footer_prepared_by_name'),
            header.get('footer_prepared_by_designation'),
            header.get('footer_approved_by_name'),
            header.get('footer_approved_by_designation'),
            header.get('footer_noted_by_name'),
            header.get('footer_noted_by_designation')
        ))
        mrf_id = cursor.lastrowid
        # Insert items if provided
        for item in items:
            cursor.execute("""
                INSERT INTO mrf_items (
                    mrf_header_id, item_no, part_no, brand_name, description, qty, uom, install_date, remarks, status, actual_delivery_date
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                mrf_id,
                item.get('item_no'),
                item.get('part_no'),
                item.get('brand_name'),
                item.get('description'),
                item.get('qty'),
                item.get('uom'),
                item.get('install_date'),
                item.get('remarks'),
                item.get('status'),
                item.get('actual_delivery_date')
            ))
        conn.commit()
        print(f'MRF saved successfully with id {mrf_id}')
        return jsonify({'message': 'MRF saved successfully', 'mrf_id': mrf_id, 'form_no': header.get('form_no')}), 201
    except Exception as e:
        if conn:
            conn.rollback()
        print('Exception in /api/mrf:', str(e))
        import traceback; traceback.print_exc()
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/mrfs', methods=['GET'])
@role_required(VALID_ROLES)
def list_mrfs():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mrf_headers ORDER BY id DESC")
        rows = cursor.fetchall()
        mrf_list = [dict(row) for row in rows]
        return jsonify(mrf_list), 200  # Return direct array
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@app.route('/api/mrf/by_form_no/<form_no>', methods=['GET'])
@role_required(VALID_ROLES)
def get_mrf_by_form_no(form_no):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mrf_headers WHERE form_no = ?", (form_no,))
        row = cursor.fetchone()
        if not row:
            return jsonify({'error': f'MRF with form_no {form_no} not found.'}), 404
        header = dict_keys_to_camel_case(dict(row))
        mrf_id = header.get('id')
        # Fetch items for this MRF
        cursor.execute("SELECT * FROM mrf_items WHERE mrf_header_id = ? ORDER BY item_no ASC", (mrf_id,))
        items = [dict_keys_to_camel_case(dict(item)) for item in cursor.fetchall()]
        return jsonify({'header': header, 'items': items}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

# --- Helper: Convert dict keys from snake_case to camelCase ---
def to_camel_case(s):
    parts = s.split('_')
    return parts[0] + ''.join(word.capitalize() for word in parts[1:]) if len(parts) > 1 else s

def dict_keys_to_camel_case(d):
    return {to_camel_case(k): v for k, v in d.items()}

if __name__ == '__main__':
    print("Starting Flask application...")
    init_db()  # Ensure DB tables exist
    # Run on all interfaces for intranet access
    app.run(host='0.0.0.0', debug=True, port=5000)