# app.py - Backend with Task Data Storage & API
# v8.9: Removed duplicate /login route definition.
# v8.8: Added MRF item status tracking (status, actual_delivery_date) and project-specific MRF monitoring page/API.
# v8.7: Added /api/test route for diagnostics.
# v8.6: Added MRF (Material Request Form) functionality - new tables and API endpoints.
# v8.5: Modified api_dashboard to calculate monthly forecast/invoiced totals.
# v8.4: Corrected syntax errors (removed trailing text).
# v8.3: Added /api/register endpoint for user creation.
# v8.2: Second attempt at correcting syntax errors.
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

# --- Configuration ---
DATABASE = 'projects.db'
MAX_UPDATES_PER_PROJECT = 30 
FORECAST_LIMIT = 100 
STATIC_FOLDER_PATH = 'static' 
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
if not os.path.exists(STATIC_FOLDER_PATH):
    print(f"Warning: Static folder '{STATIC_FOLDER_PATH}' not found. Creating it.")
    try:
        os.makedirs(STATIC_FOLDER_PATH)
        for filename in ['index.html', 'updates_log.html', 'project_gantt.html',
                         'forecast.html', 'login.html', 'mrf_form.html', 
                         'project_mrf_status.html', 
                         'mrf_items_log.html', 
                         'style.css', 'script.js', 'forecast.js',
                         'project_gantt.js']:
            filepath = os.path.join(STATIC_FOLDER_PATH, filename)
            if not os.path.exists(filepath):
                with open(filepath, 'w') as f:
                    if filename.endswith('.html'):
                        f.write(f"<html><head><title>{filename}</title></head><body>Placeholder for {filename}</body></html>")
                    elif filename.endswith('.js'):
                         f.write(f"// Placeholder for {filename}\nconsole.log('{filename} loaded.');")
                    else: 
                         f.write(f"/* Placeholder for {filename} */")
                print(f" -> Created placeholder '{filename}'")
    except OSError as e:
        print(f"Error: Could not create static folder '{STATIC_FOLDER_PATH}': {e}")

app = Flask(__name__, static_folder=STATIC_FOLDER_PATH, static_url_path='')

app.secret_key = os.environ.get('FLASK_SECRET_KEY', b'_5#y2L"F4Q8z\n\xec]/') 
if app.secret_key == b'_5#y2L"F4Q8z\n\xec]/':
    print("WARNING: Using default Flask secret key. Set FLASK_SECRET_KEY environment variable for production!")


# --- Database Management ---
def get_db():
    try:
        conn = sqlite3.connect(DATABASE)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn
    except sqlite3.Error as e:
        print(f"Database connection error: {e}")
        raise

def init_db():
    conn = None
    print("Attempting to initialize database schema...")
    try:
        conn = get_db()
        cursor = conn.cursor()
        print(f"Database connection established to '{DATABASE}'.")

        # --- Users Table ---
        print(" -> Checking 'users' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> Creating 'users' table...")
            roles_str = "', '".join(VALID_ROLES)
            cursor.execute(f'''
                CREATE TABLE users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password_hash TEXT NOT NULL,
                    role TEXT NOT NULL CHECK(role IN ('{roles_str}'))
                )
            ''')
            cursor.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_username ON users (username)")
            print(" -> 'users' table created.")
        else:
             print(" -> 'users' table already exists.")

        # --- Projects Table ---
        print(" -> Checking 'projects' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> Creating 'projects' table...")
            cursor.execute('''
                CREATE TABLE projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ds TEXT, year INTEGER, project_no TEXT UNIQUE, client TEXT,
                    project_name TEXT NOT NULL, amount REAL,
                    status REAL NOT NULL DEFAULT 0.0 CHECK(status >= 0.0 AND status <= 100.0),
                    remaining_amount REAL, total_running_weeks INTEGER,
                    po_date TEXT, po_no TEXT, date_completed TEXT, pic TEXT, address TEXT
                )
            ''')
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_project_no ON projects (project_no)")
            print(" -> 'projects' table created.")
        else:
            print(" -> 'projects' table already exists. Checking columns...")
            cursor.execute("PRAGMA table_info(projects)")
            project_columns = {column['name'] for column in cursor.fetchall()}
            if 'address' not in project_columns:
                try:
                    cursor.execute("ALTER TABLE projects ADD COLUMN address TEXT")
                    print(" -> Added 'address' column to 'projects'.")
                except sqlite3.OperationalError as e:
                    print(f" -> Could not add 'address': {e}")
        
        # --- Project Updates Table ---
        print(" -> Checking 'project_updates' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_updates';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> Creating 'project_updates' table...")
            cursor.execute('''
                CREATE TABLE project_updates (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL,
                    update_text TEXT NOT NULL,
                    is_completed INTEGER NOT NULL DEFAULT 0 CHECK(is_completed IN (0, 1)),
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                    completion_timestamp DATETIME, due_date TEXT,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_update_project_id ON project_updates (project_id)")
            print(" -> 'project_updates' table created.")
        else:
            print(" -> 'project_updates' table exists. Checking columns...")
            cursor.execute("PRAGMA table_info(project_updates)")
            update_columns = {column['name'] for column in cursor.fetchall()}
            if 'completion_timestamp' not in update_columns:
                try:
                    cursor.execute("ALTER TABLE project_updates ADD COLUMN completion_timestamp DATETIME")
                    print(" -> Added 'completion_timestamp'.")
                except sqlite3.OperationalError as e:
                    print(f" -> Could not add 'completion_timestamp': {e}")
            if 'due_date' not in update_columns:
                try:
                    cursor.execute("ALTER TABLE project_updates ADD COLUMN due_date TEXT")
                    print(" -> Added 'due_date'.")
                except sqlite3.OperationalError as e:
                    print(f" -> Could not add 'due_date': {e}")

        # --- Forecast Items Table ---
        print(" -> Checking 'forecast_items' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='forecast_items';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> Creating 'forecast_items' table...")
            cursor.execute('''
                CREATE TABLE forecast_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL,
                    forecast_date TEXT,
                    forecast_input_type TEXT NOT NULL CHECK(forecast_input_type IN ('percent', 'amount')),
                    forecast_input_value REAL NOT NULL,
                    is_forecast_completed INTEGER NOT NULL DEFAULT 0 CHECK(is_forecast_completed IN (0, 1)),
                    is_deduction INTEGER NOT NULL DEFAULT 0 CHECK(is_deduction IN (0, 1)),
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_forecast_project_id ON forecast_items (project_id)")
            print(" -> 'forecast_items' table created.")
        else:
            print(" -> 'forecast_items' table exists. Checking columns...")
            cursor.execute("PRAGMA table_info(forecast_items)")
            forecast_columns = {column['name'] for column in cursor.fetchall()}
            if 'forecast_date' not in forecast_columns:
                try:
                    cursor.execute("ALTER TABLE forecast_items ADD COLUMN forecast_date TEXT")
                    print(" -> Added 'forecast_date' column to 'forecast_items'.")
                except sqlite3.OperationalError as e:
                    print(f" -> Could not add 'forecast_date' column: {e}")
            if 'is_deduction' not in forecast_columns:
                try:
                    cursor.execute("ALTER TABLE forecast_items ADD COLUMN is_deduction INTEGER NOT NULL DEFAULT 0 CHECK(is_deduction IN (0, 1))")
                    print(" -> Added 'is_deduction' column to 'forecast_items'.")
                except sqlite3.OperationalError as e:
                    print(f" -> Could not add 'is_deduction' column: {e}")

        # --- Project Tasks Table ---
        print(" -> Checking 'project_tasks' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='project_tasks';")
        table_exists = cursor.fetchone()
        if not table_exists:
            print(" -> Creating 'project_tasks' table...")
            cursor.execute('''
                CREATE TABLE project_tasks (
                    task_id INTEGER PRIMARY KEY AUTOINCREMENT, project_id INTEGER NOT NULL,
                    task_name TEXT NOT NULL, start_date TEXT, end_date TEXT,
                    planned_weight REAL, actual_start TEXT, actual_end TEXT,
                    assigned_to TEXT, parent_task_id INTEGER,
                    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE,
                    FOREIGN KEY(parent_task_id) REFERENCES project_tasks(task_id) ON DELETE SET NULL
                )
            ''')
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_project_id ON project_tasks (project_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_parent_id ON project_tasks (parent_task_id)")
            print(" -> 'project_tasks' table created.")
        else:
            print(" -> 'project_tasks' table exists. Checking columns...")
            cursor.execute("PRAGMA table_info(project_tasks)")
            task_columns = {column['name'] for column in cursor.fetchall()}
            if 'assigned_to' not in task_columns:
                try:
                    cursor.execute("ALTER TABLE project_tasks ADD COLUMN assigned_to TEXT")
                    print(" -> Added 'assigned_to'.")
                except sqlite3.OperationalError as e:
                    print(f" -> Could not add 'assigned_to': {e}")
            if 'parent_task_id' not in task_columns:
                try:
                    cursor.execute("ALTER TABLE project_tasks ADD COLUMN parent_task_id INTEGER REFERENCES project_tasks(task_id) ON DELETE SET NULL")
                    cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_parent_id ON project_tasks (parent_task_id)")
                    print(" -> Added 'parent_task_id' and index.")
                except sqlite3.OperationalError as e:
                    print(f" -> Could not add 'parent_task_id': {e}")

        # --- MRF Headers Table ---
        print(" -> Checking 'mrf_headers' table...")
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mrf_headers';")
        if not cursor.fetchone():
            print(" -> Creating 'mrf_headers' table...")
            cursor.execute('''
                CREATE TABLE mrf_headers (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    form_no TEXT UNIQUE NOT NULL,
                    mrf_date TEXT,
                    project_name TEXT,
                    project_number TEXT,
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
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_number) REFERENCES projects(project_no) ON DELETE SET NULL 
                )
            ''') 
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrf_form_no ON mrf_headers (form_no)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrf_project_number ON mrf_headers (project_number)")
            print(" -> 'mrf_headers' table created.")
        else:
            print(" -> 'mrf_headers' table already exists.")

        # --- MRF Items Table ---
        print(" -> Checking 'mrf_items' table for status and delivery date columns...")
        cursor.execute("PRAGMA table_info(mrf_items)")
        mrf_items_columns = {column['name'] for column in cursor.fetchall()}
        
        default_mrf_item_status = "Processing" # Updated default status

        if 'status' not in mrf_items_columns:
            try:
                cursor.execute(f"ALTER TABLE mrf_items ADD COLUMN status TEXT DEFAULT '{default_mrf_item_status}'")
                print(f" -> Added 'status' column to 'mrf_items' with default '{default_mrf_item_status}'.")
            except sqlite3.OperationalError as e:
                print(f" -> Could not add 'status' column to 'mrf_items': {e}")
        
        if 'actual_delivery_date' not in mrf_items_columns:
            try:
                cursor.execute("ALTER TABLE mrf_items ADD COLUMN actual_delivery_date TEXT")
                print(" -> Added 'actual_delivery_date' column to 'mrf_items'.")
            except sqlite3.OperationalError as e:
                print(f" -> Could not add 'actual_delivery_date' column to 'mrf_items': {e}")

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='mrf_items';")
        if not cursor.fetchone(): 
            print(" -> 'mrf_items' table not found, creating it with new columns...")
            cursor.execute(f'''
                CREATE TABLE mrf_items (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mrf_header_id INTEGER NOT NULL,
                    item_no TEXT, 
                    part_no TEXT,
                    brand_name TEXT,
                    description TEXT,
                    qty REAL,
                    uom TEXT,
                    install_date TEXT,
                    remarks TEXT,
                    status TEXT DEFAULT '{default_mrf_item_status}', 
                    actual_delivery_date TEXT,
                    FOREIGN KEY(mrf_header_id) REFERENCES mrf_headers(id) ON DELETE CASCADE
                )
            ''')
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_mrf_item_header_id ON mrf_items (mrf_header_id)")
            print(f" -> 'mrf_items' table created with status (default '{default_mrf_item_status}') and delivery date.")
        else:
            print(" -> 'mrf_items' table already exists or columns added.")


        conn.commit()
        print("Database schema initialization/verification complete.")

    except sqlite3.Error as e:
        print("!!!!!!!! ERROR DURING DATABASE INITIALIZATION !!!!!!!!")
        print(f"Error initializing database: {e}")
        print(traceback.format_exc())
        if conn: conn.rollback()
    except Exception as e:
        print("!!!!!!!! UNEXPECTED ERROR DURING DATABASE INITIALIZATION !!!!!!!!")
        print(f"An unexpected error occurred during DB init: {e}")
        print(traceback.format_exc())
        if conn: conn.rollback()
    finally:
        if conn:
            conn.close()
            print("Database connection closed after init.")

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
                    return redirect(url_for('index'))
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
        if abs(float_val - round(float_val)) < 1e-9:
            return int(round(float_val))
        else:
            return int(float_val) 
    except (ValueError, TypeError):
        return default

def calculate_remaining(amount_val, status_percent_val):
    amount = safe_float(amount_val)
    status_percent = safe_float(status_percent_val)
    if amount is None or status_percent is None: return None
    status_percent = max(0.0, min(100.0, status_percent)) 
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
        placeholders = ','.join('?' * len(project_ids))
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
def login_page_route(): # This is the primary definition
    if 'user_id' in session:
        return redirect(url_for('index')) 
    login_path = os.path.join(app.static_folder, 'login.html')
    if not os.path.exists(login_path):
        return "Error: Login page file not found.", 404
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
            next_url = session.pop('next_url', None) or url_for('index')
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
        cursor.execute("""
            SELECT id, ds, year, project_no, client, project_name, amount, status,
                   remaining_amount, po_date, po_no, date_completed, pic, address
            FROM projects 
            WHERE (date_completed IS NULL OR date_completed = '') OR status < 100.0
            ORDER BY CASE WHEN remaining_amount IS NULL THEN 1 ELSE 0 END, remaining_amount DESC
        """)
        project_rows = cursor.fetchall()
        forecasted_project_ids = set()
        project_ids = [row['id'] for row in project_rows]
        if project_ids:
            placeholders = ','.join('?' * len(project_ids))
            cursor.execute(f"SELECT DISTINCT project_id FROM forecast_items WHERE project_id IN ({placeholders})", tuple(project_ids))
            forecasted_project_ids = {row['project_id'] for row in cursor.fetchall()}
        projects = _process_project_rows(project_rows, cursor, forecasted_project_ids)
        return jsonify(projects), 200
    except Exception as e:
        print(f"Error fetching active projects: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error fetching active projects"}), 500
    finally:
        if conn: conn.close()

@app.route('/api/projects/completed', methods=['GET'])
@role_required(VALID_ROLES) 
def api_completed_projects():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, ds, year, project_no, client, project_name, amount, status,
                   remaining_amount, po_date, po_no, date_completed, pic, address
            FROM projects WHERE (date_completed IS NOT NULL AND date_completed != '') OR status >= 100.0
            ORDER BY date_completed DESC, id DESC
        """)
        project_rows = cursor.fetchall()
        forecasted_project_ids = set()
        project_ids = [row['id'] for row in project_rows]
        if project_ids:
            placeholders = ','.join('?' * len(project_ids))
            cursor.execute(f"SELECT DISTINCT project_id FROM forecast_items WHERE project_id IN ({placeholders})", tuple(project_ids))
            forecasted_project_ids = {row['project_id'] for row in cursor.fetchall()}
        projects = _process_project_rows(project_rows, cursor, forecasted_project_ids)
        return jsonify(projects), 200
    except Exception as e:
        print(f"Error fetching completed projects: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error fetching completed projects"}), 500
    finally:
        if conn: conn.close()

# --- Helper Function for Processing Project Data (Used by Bulk/CSV Upload) ---
def _process_and_save_project(project_data, row_num, cursor, existing_projects_map):
    if not isinstance(project_data, dict):
        return "skipped", f"Row {row_num}: Invalid format (expected dictionary)."
    normalized_data = {}
    for k, v in project_data.items():
        if k and isinstance(k, str): 
            key_str = str(k).strip()
            if not key_str: continue
            normalized_key = key_str.lower()
            header_map = {
                "project #": "project_no", "project#": "project_no", "project_#": "project_no", "project no": "project_no", "project_no.": "project_no",
                "project name": "project_name", "client": "client", "amount": "amount",
                "status (%)": "status", "status(%)": "status", "status_%": "status", "status": "status",
                "po date": "po_date", "po no.": "po_no", "po no": "po_no", "po_no.": "po_no",
                "date completed": "date_completed", "pic": "pic", "address": "address", "ds": "ds", "year": "year"
            }
            db_key = header_map.get(normalized_key)
            if not db_key:
                normalized_key = re.sub(r'[\s\(\)#%\.]+', '_', normalized_key) 
                normalized_key = re.sub(r'_+', '_', normalized_key) 
                db_key = normalized_key.strip('_') 
            if db_key:
                normalized_data[db_key] = v
    project_name = normalized_data.get('project_name')
    if not project_name or str(project_name).strip() == '':
        return "skipped", f"Row {row_num}: Missing or empty 'Project Name'."
    project_no = normalized_data.get('project_no')
    if isinstance(project_no, (int, float)): 
        project_no = str(int(project_no)) 
    if isinstance(project_no, str):
        project_no = project_no.strip()
    if project_no == '' or project_no is None or project_no.upper() in ['#N/A', 'N/A', 'NULL', 'NONE']:
        project_no = None
    raw_status = normalized_data.get('status')
    status_percent = safe_float(raw_status, default=None)
    error_status_msg = None
    if status_percent is None:
        if raw_status is not None and str(raw_status).strip() != '':
            error_status_msg = f"Row {row_num} ('{project_name}'): Invalid 'Status' value '{raw_status}'. Using DB default 0.0."
        status_percent = 0.0 
    clamped_status = max(0.0, min(100.0, status_percent)) 
    amount_val = safe_float(normalized_data.get('amount')) 
    calculated_remaining = calculate_remaining(amount_val, clamped_status)
    ds = str(normalized_data.get('ds', '')).strip() or None
    year = safe_int(normalized_data.get('year')) 
    client = str(normalized_data.get('client', '')).strip() or None
    po_date_raw = normalized_data.get('po_date')
    po_no_raw = normalized_data.get('po_no')
    po_no = str(po_no_raw).strip() if po_no_raw is not None else None
    if po_no == '': po_no = None 
    date_completed_raw = normalized_data.get('date_completed')
    pic = str(normalized_data.get('pic', '')).strip() or None
    address = str(normalized_data.get('address', '')).strip() or None
    po_date = None
    date_completed = None
    error_date_msg = None
    if po_date_raw and str(po_date_raw).strip():
        parsed_po = parse_flexible_date(str(po_date_raw))
        if parsed_po: po_date = parsed_po.isoformat()
        else: error_date_msg = f"Invalid PO Date format '{po_date_raw}'."
    if date_completed_raw and str(date_completed_raw).strip():
        parsed_completed = parse_flexible_date(str(date_completed_raw))
        if parsed_completed: date_completed = parsed_completed.isoformat()
        else: error_date_msg = (error_date_msg + " " if error_date_msg else "") + f"Invalid Date Completed format '{date_completed_raw}'."
    final_warning_msg = error_status_msg
    if error_date_msg:
        final_warning_msg = (final_warning_msg + " " if final_warning_msg else "") + error_date_msg
    existing_id = existing_projects_map.get(project_no) if project_no else None
    try:
        if existing_id is not None: 
            cursor.execute("""
                UPDATE projects SET ds=?, year=?, client=?, project_name=?, amount=?, status=?,
                                     remaining_amount=?, po_date=?, po_no=?, date_completed=?, pic=?, address=?
                WHERE id = ?
            """, (ds, year, client, project_name, amount_val, clamped_status, calculated_remaining,
                  po_date, po_no, date_completed, pic, address, existing_id))
            return "updated", final_warning_msg 
        else: 
            cursor.execute("""
                INSERT INTO projects (ds, year, project_no, client, project_name, amount, status,
                                      remaining_amount, po_date, po_no, date_completed, pic, address)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (ds, year, project_no, client, project_name, amount_val, clamped_status, calculated_remaining,
                  po_date, po_no, date_completed, pic, address))
            new_id = cursor.lastrowid
            if project_no and new_id:
                existing_projects_map[project_no] = new_id
            return "inserted", final_warning_msg
    except sqlite3.IntegrityError as db_err:
        error_detail = str(db_err)
        error_msg = f"Row {row_num} ('{project_name}'): Skipped. DB Integrity Error: {error_detail}"
        if "UNIQUE constraint failed: projects.project_no" in error_detail and project_no:
            error_msg = f"Row {row_num} ('{project_name}'): Skipped. Project Number '{project_no}' already exists."
        print(error_msg)
        if final_warning_msg: error_msg += f" (Additional Warning: {final_warning_msg})"
        return "skipped", error_msg
    except sqlite3.Error as db_err:
        error_msg = f"Row {row_num} ('{project_name}'): Skipped. DB Error: {db_err}"
        print(error_msg)
        if final_warning_msg: error_msg += f" (Additional Warning: {final_warning_msg})"
        return "skipped", error_msg

@app.route('/api/projects/upload', methods=['POST'])
@role_required([ADMIN]) 
def upload_projects_csv():
    if 'csv-file' not in request.files:
        return jsonify({"error": "No 'csv-file' part"}), 400
    file = request.files['csv-file']
    if file.filename == '':
        return jsonify({"error": "No selected file"}), 400
    if not file or not file.filename.lower().endswith('.csv'):
        return jsonify({"error": "Invalid file type, please upload a .csv file"}), 400
    inserted_count, updated_count, skipped_count = 0, 0, 0
    results_log = [] 
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects';")
        if not cursor.fetchone():
            print("ERROR: 'projects' table does not exist during CSV upload.")
            return jsonify({"error": "Database not initialized correctly. 'projects' table missing."}), 500
        cursor.execute("SELECT id, project_no FROM projects WHERE project_no IS NOT NULL AND project_no != ''")
        existing_projects_map = {row['project_no']: row['id'] for row in cursor.fetchall()}
        try:
            first_bytes = file.stream.read(3)
            file.stream.seek(0) 
            encoding = 'utf-8-sig' if first_bytes == b'\xef\xbb\xbf' else 'utf-8'
            file_content = file.stream.read().decode(encoding)
            stream = io.StringIO(file_content, newline=None)
        except UnicodeDecodeError:
            file.stream.seek(0)
            try:
                file_content = file.stream.read().decode('latin-1')
                stream = io.StringIO(file_content, newline=None)
                encoding = 'latin-1'
                print("Warning: CSV file might not be UTF-8, decoded as latin-1.")
            except Exception as decode_err:
                print(f"Error decoding CSV file: {decode_err}")
                return jsonify({"error": "Could not decode CSV file. Please ensure it's UTF-8 or compatible."}), 400
        csv_reader = csv.DictReader(stream)
        if not csv_reader.fieldnames:
            return jsonify({"error": "CSV file appears to be empty or has no header row."}), 400
        conn.execute("BEGIN TRANSACTION")
        for row_num, row_data in enumerate(csv_reader, start=2): 
            status, msg = _process_and_save_project(row_data, row_num, cursor, existing_projects_map)
            if status == "inserted": inserted_count += 1
            elif status == "updated": updated_count += 1
            else: skipped_count += 1
            if msg: results_log.append(msg) 
        conn.commit() 
        response_status = 200 if not results_log else 207 
        response_message = f"CSV process finished. Inserted: {inserted_count}, Updated: {updated_count}, Skipped/Warnings: {skipped_count}."
        print(f"[CSV Upload] Result: {response_message}")
        if results_log: print(f"[CSV Upload] Errors/Warnings encountered:\n" + "\n".join(results_log))
    except csv.Error as csv_err:
        if conn: conn.rollback()
        print(f"CSV parsing error: {csv_err}")
        return jsonify({"error": f"Error parsing CSV file: {csv_err}"}), 400
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"Critical DB error during CSV upload: {db_err}")
        if "no such table" in str(db_err):
            return jsonify({"error": "DB error during upload: 'projects' table not found."}), 500
        else:
            return jsonify({"error": f"DB error during upload: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Critical unexpected error during CSV upload: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected server error during CSV processing."}), 500
    finally:
        if conn: conn.close()
    response_body = {
        "message": response_message,
        "inserted_count": inserted_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "errors": results_log[:100] 
    }
    if len(results_log) > 100:
        response_body["errors"].append(f"...and {len(results_log)-100} more errors/warnings.")
    return jsonify(response_body), response_status

@app.route('/api/projects/bulk', methods=['POST'])
@role_required([ADMIN]) 
def add_projects_bulk():
    projects_data = request.get_json()
    if not isinstance(projects_data, list):
        return jsonify({"error": "Expected a list of projects"}), 400
    inserted_count, updated_count, skipped_count = 0, 0, 0
    results_log = []
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='projects';")
        if not cursor.fetchone():
            print("ERROR: 'projects' table does not exist during bulk add.")
            return jsonify({"error": "Database not initialized correctly. 'projects' table missing."}), 500
        cursor.execute("SELECT id, project_no FROM projects WHERE project_no IS NOT NULL AND project_no != ''")
        existing_projects_map = {row['project_no']: row['id'] for row in cursor.fetchall()}
        conn.execute("BEGIN TRANSACTION")
        for index, project_dict in enumerate(projects_data):
            row_num = index + 1 
            status, msg = _process_and_save_project(project_dict, row_num, cursor, existing_projects_map)
            if status == "inserted": inserted_count += 1
            elif status == "updated": updated_count += 1
            else: skipped_count += 1
            if msg: results_log.append(msg)
        conn.commit()
        response_status = 200 if not results_log else 207
        response_message = f"JSON Bulk process finished. Inserted: {inserted_count}, Updated: {updated_count}, Skipped/Warnings: {skipped_count}."
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error during JSON bulk: {db_err}")
        return jsonify({"error": f"DB error: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error during JSON bulk: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected server error during bulk processing."}), 500
    finally:
        if conn: conn.close()
    response_body = {
        "message": response_message,
        "inserted_count": inserted_count,
        "updated_count": updated_count,
        "skipped_count": skipped_count,
        "errors": results_log[:50] 
    }
    if len(results_log) > 50:
        response_body["errors"].append(f"...and {len(results_log)-50} more errors/warnings.")
    return jsonify(response_body), response_status

@app.route('/api/projects/<int:project_id>', methods=['PUT'])
@role_required([ADMIN, DS_ENGINEER]) 
def update_project_field(project_id):
    data = request.get_json()
    allowed_fields = {
        'client': str, 'status': 'status_float', 'po_date': 'date_str_optional',
        'po_no': 'po_no_str_optional', 'date_completed': 'date_str_optional', 'pic': str,
        'address': str, 'amount': 'amount_float', 'project_name': str,
        'year': int, 'ds': str
    }
    if not data:
        return jsonify({"error": "Request body must contain JSON data."}), 400
    fields_to_update = {}
    update_amount = None
    update_status = None
    validation_errors = []
    for field, field_type in allowed_fields.items():
        if field in data:
            value = data[field]
            sanitized_value = None
            error_msg = None
            try:
                if field_type == 'status_float':
                    status_percent = safe_float(value, default=None) if value is not None and str(value).strip() != '' else 0.0
                    if status_percent is None or not (0 <= status_percent <= 100):
                        error_msg = f"Invalid 'status': '{value}'. Must be 0-100 or empty."
                    else:
                        sanitized_value = status_percent
                        update_status = sanitized_value
                elif field_type == 'amount_float':
                    amount_val = safe_float(value, default=None) if value is not None and str(value).strip() != '' else None
                    if amount_val is None and value is not None and str(value).strip() != '':
                        error_msg = f"Invalid 'amount': '{value}'. Must be number or empty."
                    else:
                        sanitized_value = amount_val
                        update_amount = sanitized_value
                elif field_type == int:
                    int_val = safe_int(value, default=None) if value is not None and str(value).strip() != '' else None
                    if int_val is None and value is not None and str(value).strip() != '':
                         error_msg = f"Invalid value for '{field}': '{value}'. Expected integer or empty."
                    else:
                         sanitized_value = int_val
                elif field_type == 'date_str_optional':
                    str_val = str(value).strip() if value is not None else None
                    if str_val == '':
                        sanitized_value = None
                    elif str_val:
                        parsed_dt = parse_flexible_date(str_val)
                        if not parsed_dt:
                            error_msg = f"Invalid date format for '{field}': '{value}'. Use yyyy-MM-dd or MM/dd/yyyy or empty."
                        else:
                            sanitized_value = parsed_dt.isoformat()
                elif field_type == 'po_no_str_optional':
                    sanitized_value = str(value).strip() if value is not None else None
                    if sanitized_value == '': sanitized_value = None
                elif field_type == str:
                    sanitized_value = str(value).strip() if value is not None else None
                    if field == 'project_name' and not sanitized_value: 
                         error_msg = "Project Name cannot be empty."
                else:
                    error_msg = f"Internal error: Unknown validation type for field '{field}'."
            except Exception as val_err:
                error_msg = f"Error processing field '{field}': {val_err}"
            if error_msg:
                validation_errors.append(error_msg)
            else:
                fields_to_update[field] = sanitized_value
    if validation_errors:
        return jsonify({"error": "Validation failed", "details": validation_errors}), 400
    if not fields_to_update:
        return jsonify({"message": "No valid fields provided for update."}), 200
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, amount, status FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            return jsonify({"error": "Project not found."}), 404
        if 'amount' in fields_to_update or 'status' in fields_to_update:
            amount_for_calc = update_amount if 'amount' in fields_to_update else project['amount']
            status_for_calc = update_status if 'status' in fields_to_update else project['status']
            fields_to_update['remaining_amount'] = calculate_remaining(amount_for_calc, status_for_calc)
        set_clause = ", ".join([f"`{field}` = ?" for field in fields_to_update])
        update_values = list(fields_to_update.values()) + [project_id]
        sql = f"UPDATE projects SET {set_clause} WHERE id = ?"
        cursor.execute(sql, tuple(update_values))
        conn.commit()
        cursor.execute("SELECT * FROM projects WHERE id = ?", (project_id,))
        updated_project_row = cursor.fetchone()
        if not updated_project_row:
            return jsonify({"message": "Project updated, but failed to retrieve updated record."}), 207
        cursor.execute("SELECT 1 FROM forecast_items WHERE project_id = ? LIMIT 1", (project_id,))
        has_forecasts = cursor.fetchone() is not None
        forecasted_ids_set = {project_id} if has_forecasts else set()
        updated_project_list = _process_project_rows([updated_project_row], cursor, forecasted_ids_set)
        if not updated_project_list:
             return jsonify({"message": "Project updated, but failed to process updated record."}), 207
        response_data = {
            "message": "Project updated successfully.",
            "updatedFields": list(fields_to_update.keys()),
            "updatedProject": updated_project_list[0]
        }
        return jsonify(response_data), 200
    except sqlite3.IntegrityError as ie:
        if conn: conn.rollback()
        error_detail = str(ie)
        if "UNIQUE constraint failed: projects.project_no" in error_detail:
            updated_proj_no = fields_to_update.get('project_no', 'N/A')
            return jsonify({"error": f"Update failed. Project Number '{updated_proj_no}' already exists."}), 409
        else:
            print(f"DB integrity error during project update: {ie}")
            return jsonify({"error": f"Database integrity error: {error_detail}"}), 500
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error during project update: {db_err}")
        return jsonify({"error": f"Database error: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error during project update: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected server error during project update."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/projects/<int:project_id>', methods=['DELETE'])
@role_required([ADMIN]) 
def delete_project(project_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if not project:
            return jsonify({"error": "Project not found."}), 404
        cursor.execute("DELETE FROM projects WHERE id = ?", (project_id,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Project {project_id} deleted by user {session.get('username', 'Unknown')}.")
            return jsonify({"message": "Project deleted successfully."}), 200
        else:
            print(f"Delete failed unexpectedly after finding project {project_id}.")
            return jsonify({"error": "Delete operation failed unexpectedly."}), 500
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error deleting project {project_id}: {db_err}")
        return jsonify({"error": f"Error deleting project: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error deleting project {project_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected error during project deletion."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/projects/<int:project_id>/details', methods=['GET'])
@role_required(VALID_ROLES) 
def get_project_details(project_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, project_no, project_name, po_no FROM projects WHERE id = ?", (project_id,))
        project = cursor.fetchone()
        if project:
            return jsonify(dict(project)), 200
        else:
            return jsonify({"error": "Project not found"}), 404
    except Exception as e:
        print(f"Error fetching details for project {project_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error fetching project details"}), 500
    finally:
        if conn: conn.close()

# --- Project Update Endpoints ---
@app.route('/api/projects/<int:project_id>/updates', methods=['GET'])
@role_required(VALID_ROLES) 
def get_project_updates(project_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Project not found."}), 404
        cursor.execute("""
            SELECT id as update_id, update_text, is_completed, timestamp, completion_timestamp, due_date
            FROM project_updates
            WHERE project_id = ?
            ORDER BY timestamp DESC, id DESC
        """, (project_id,))
        updates = [dict(row) for row in cursor.fetchall()]
        for u in updates:
            u['is_completed'] = bool(u['is_completed'])
        return jsonify(updates), 200
    except Exception as e:
        print(f"Error fetching updates for project {project_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error fetching project updates."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/projects/<int:project_id>/updates', methods=['POST'])
@role_required([ADMIN, DS_ENGINEER]) 
def add_project_update(project_id):
    data = request.get_json()
    if not data or 'update_text' not in data or not str(data['update_text']).strip():
        return jsonify({"error": "Missing or empty 'update_text'."}), 400
    update_text = str(data['update_text']).strip()
    due_date_str = data.get('due_date')
    validated_due_date = None
    if due_date_str is not None and str(due_date_str).strip() != '':
        due_date_str = str(due_date_str).strip()
        parsed_due = parse_flexible_date(due_date_str)
        if parsed_due:
            validated_due_date = parsed_due.isoformat()
        else:
            return jsonify({"error": f"Invalid 'due_date' format: '{due_date_str}'. Use yyyy-MM-dd or MM/dd/yyyy or empty."}), 400
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Project not found."}), 404
        cursor.execute("SELECT COUNT(*) as count FROM project_updates WHERE project_id = ?", (project_id,))
        count_row = cursor.fetchone()
        if count_row and count_row['count'] >= MAX_UPDATES_PER_PROJECT:
            return jsonify({"error": f"Maximum updates limit ({MAX_UPDATES_PER_PROJECT}) reached."}), 400
        cursor.execute("INSERT INTO project_updates (project_id, update_text, due_date) VALUES (?, ?, ?)",
                       (project_id, update_text, validated_due_date))
        new_update_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT id as update_id, update_text, is_completed, timestamp, completion_timestamp, due_date FROM project_updates WHERE id = ?", (new_update_id,))
        new_update_row = cursor.fetchone()
        if new_update_row:
            new_update_dict = dict(new_update_row)
            new_update_dict['is_completed'] = bool(new_update_dict['is_completed'])
            return jsonify({"message": "Update added successfully.", "new_update": new_update_dict}), 201
        else:
            print(f"Error retrieving newly added update {new_update_id}.")
            return jsonify({"message": "Update added, but failed to retrieve."}), 207
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error adding update: {db_err}")
        return jsonify({"error": f"Database error adding update: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error adding update: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected server error adding update."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/updates/<int:update_id>/complete', methods=['PUT'])
@role_required([ADMIN, DS_ENGINEER]) 
def toggle_update_completion(update_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, project_id, is_completed FROM project_updates WHERE id = ?", (update_id,))
        update_item = cursor.fetchone()
        if not update_item:
            return jsonify({"error": "Update not found."}), 404
        new_status_int = 1 - update_item['is_completed']
        completion_time_sql_part = "completion_timestamp = CURRENT_TIMESTAMP" if new_status_int == 1 else "completion_timestamp = NULL"
        sql = f"UPDATE project_updates SET is_completed = ?, {completion_time_sql_part} WHERE id = ?"
        cursor.execute(sql, (new_status_int, update_id))
        conn.commit()
        if cursor.rowcount > 0:
            new_status_bool = bool(new_status_int)
            message = f"Update marked as {'Complete' if new_status_bool else 'Incomplete'}."
            cursor.execute("SELECT completion_timestamp FROM project_updates WHERE id = ?", (update_id,))
            completion_ts = cursor.fetchone()['completion_timestamp']
            return jsonify({"message": message, "update_id": update_id, "is_completed": new_status_bool, "completion_timestamp": completion_ts }), 200
        else:
            print(f"Toggle completion failed unexpectedly for update {update_id}.")
            return jsonify({"error": "Toggle completion failed."}), 500
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error toggling update {update_id}: {db_err}")
        return jsonify({"error": f"Database error toggling update: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error toggling update {update_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected error toggling update."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/updates/<int:update_id>', methods=['DELETE'])
@role_required([ADMIN, DS_ENGINEER]) 
def delete_project_update(update_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM project_updates WHERE id = ?", (update_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Update not found."}), 404
        cursor.execute("DELETE FROM project_updates WHERE id = ?", (update_id,))
        conn.commit()
        if cursor.rowcount > 0:
             return jsonify({"message": "Update deleted successfully.", "deleted_update_id": update_id}), 200
        else:
             print(f"Delete failed unexpectedly for update {update_id}.")
             return jsonify({"error": "Delete failed."}), 500
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error deleting update {update_id}: {db_err}")
        return jsonify({"error": f"Database error deleting update: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error deleting update {update_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected error deleting update."}), 500
    finally:
        if conn: conn.close()

# --- Updates Log Endpoint ---
@app.route('/api/updates/log', methods=['GET'])
@role_required(VALID_ROLES) 
def get_updates_log():
    log_entries = []
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT pu.id as update_id, pu.project_id, pu.update_text, pu.is_completed,
                   pu.timestamp as creation_timestamp, pu.completion_timestamp, pu.due_date,
                   p.project_no, p.project_name
            FROM project_updates pu
            JOIN projects p ON pu.project_id = p.id
            ORDER BY pu.timestamp DESC, pu.id DESC
        """)
        rows = cursor.fetchall()
        for row in rows:
            entry_dict = dict(row)
            entry_dict['is_completed'] = bool(entry_dict['is_completed'])
            log_entries.append(entry_dict)
        return jsonify(log_entries), 200
    except Exception as e:
        print(f"Error fetching updates log: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error fetching updates log."}), 500
    finally:
        if conn: conn.close()

# --- Forecast Endpoints ---
@app.route('/api/forecast', methods=['GET'])
@role_required(VALID_ROLES) 
def get_forecast_items():
    forecast_items_list = []
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fi.id as forecast_entry_id, fi.project_id, fi.forecast_input_type,
                   fi.forecast_input_value, fi.is_forecast_completed, fi.forecast_date,
                   fi.is_deduction,
                   p.project_no, p.project_name, p.amount as project_amount,
                   p.status as project_status, p.pic as project_pic
            FROM forecast_items fi
            JOIN projects p ON fi.project_id = p.id
            ORDER BY fi.forecast_date, p.project_no, fi.id
        """)
        rows = cursor.fetchall()
        for row in rows:
            item_dict = dict(row)
            item_dict['is_forecast_completed'] = bool(item_dict['is_forecast_completed'])
            item_dict['is_deduction'] = bool(item_dict['is_deduction'])
            forecast_items_list.append(item_dict)
        return jsonify(forecast_items_list), 200
    except Exception as e:
        print(f"Error fetching forecast items: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error fetching forecast items."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/forecast', methods=['POST'])
@role_required([ADMIN, DS_ENGINEER]) 
def add_forecast_item():
    conn = None
    data = request.get_json()
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) as count FROM forecast_items")
        count_row = cursor.fetchone()
        if count_row and count_row['count'] >= FORECAST_LIMIT:
            return jsonify({"error": f"Maximum forecast limit ({FORECAST_LIMIT}) reached."}), 400
        required_fields = ['project_id', 'forecast_input_type', 'forecast_input_value', 'forecast_date']
        if not data or not all(field in data for field in required_fields):
            missing = [field for field in required_fields if field not in (data or {})]
            return jsonify({"error": f"Missing required fields: {', '.join(missing)}"}), 400
        project_id = data['project_id']
        input_type = data['forecast_input_type']
        input_value = safe_float(data['forecast_input_value'], default=None)
        forecast_date_str = data.get('forecast_date')
        is_deduction = bool(data.get('is_deduction', False))
        is_deduction_int = 1 if is_deduction else 0
        if not isinstance(project_id, int):
             return jsonify({"error": "Invalid 'project_id'."}), 400
        if input_type not in ['percent', 'amount', 'deduction_percent']:
            return jsonify({"error": "Invalid 'forecast_input_type'."}), 400
        if input_type == 'deduction_percent':
            input_type = 'percent'
        if input_value is None:
            return jsonify({"error": "Invalid 'forecast_input_value'."}), 400
        if is_deduction and input_value < 0:
            input_value = abs(input_value)
            print(f"Info: Storing deduction as positive: {input_value}")
        elif not is_deduction and input_value < 0:
            print(f"Warn: Negative value {input_value} for non-deduction.")
        parsed_date = parse_flexible_date(forecast_date_str)
        if not parsed_date:
            return jsonify({"error": f"Invalid 'forecast_date' format: '{forecast_date_str}'."}), 400
        validated_date_iso = parsed_date.isoformat()
        cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            return jsonify({"error": f"Project ID {project_id} not found."}), 404
        cursor.execute("""
            INSERT INTO forecast_items
                (project_id, forecast_input_type, forecast_input_value, forecast_date, is_deduction)
            VALUES (?, ?, ?, ?, ?)
        """, (project_id, input_type, input_value, validated_date_iso, is_deduction_int))
        new_forecast_id = cursor.lastrowid
        conn.commit()
        cursor.execute("""
            SELECT fi.id as forecast_entry_id, fi.project_id, fi.forecast_input_type,
                   fi.forecast_input_value, fi.is_forecast_completed, fi.forecast_date,
                   fi.is_deduction,
                   p.project_no, p.project_name, p.amount as project_amount,
                   p.status as project_status, p.pic as project_pic
            FROM forecast_items fi JOIN projects p ON fi.project_id = p.id
            WHERE fi.id = ?
        """, (new_forecast_id,))
        new_item_row = cursor.fetchone()
        if new_item_row:
            new_item_dict = dict(new_item_row)
            new_item_dict['is_forecast_completed'] = bool(new_item_dict['is_forecast_completed'])
            new_item_dict['is_deduction'] = bool(new_item_dict['is_deduction'])
            return jsonify({"message": "Forecast entry added.", "new_forecast_entry": new_item_dict}), 201
        else:
            print(f"Error retrieving new forecast {new_forecast_id}.")
            return jsonify({"message": "Forecast added, but failed to retrieve."}), 207
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error adding forecast: {db_err}")
        return jsonify({"error": f"DB error adding forecast: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error adding forecast: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected server error adding forecast."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/forecast/entry/<int:entry_id>', methods=['DELETE'])
@role_required([ADMIN, DS_ENGINEER]) 
def remove_single_forecast_entry(entry_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM forecast_items WHERE id = ?", (entry_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Forecast entry not found."}), 404
        cursor.execute("DELETE FROM forecast_items WHERE id = ?", (entry_id,))
        conn.commit()
        if cursor.rowcount > 0:
            return jsonify({"message": "Forecast entry removed.", "deleted_entry_id": entry_id}), 200
        else:
            print(f"Delete failed for forecast {entry_id}.")
            return jsonify({"error": "Delete failed."}), 500
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error removing forecast {entry_id}: {db_err}")
        return jsonify({"error": f"DB error removing forecast: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error removing forecast {entry_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected error removing forecast."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/forecast/entry/<int:entry_id>/complete', methods=['PUT'])
@role_required([ADMIN, DS_ENGINEER]) 
def toggle_single_forecast_entry_completion(entry_id):
    print(f"\n--- Toggling Forecast Entry {entry_id} ---")
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT fi.id, fi.project_id, fi.forecast_input_type, fi.forecast_input_value,
                   fi.is_forecast_completed, fi.is_deduction,
                   p.status as project_status, p.amount as project_amount
            FROM forecast_items fi
            JOIN projects p ON fi.project_id = p.id
            WHERE fi.id = ?
        """, (entry_id,))
        item_row = cursor.fetchone()
        if not item_row:
            print(f"[Toggle Forecast {entry_id}] Error: Not found.")
            return jsonify({"error": "Forecast entry not found."}), 404
        item = dict(item_row)
        print(f"[Toggle Forecast {entry_id}] Fetched: {item}")
        current_forecast_status_int = item['is_forecast_completed']
        new_forecast_status_int = 1 - current_forecast_status_int
        is_deduction_item = bool(item['is_deduction'])
        project_id = item['project_id']
        project_current_status = safe_float(item['project_status'], 0.0)
        project_amount = safe_float(item['project_amount'])
        print(f"[Toggle Forecast {entry_id}] New Status: {new_forecast_status_int}")
        forecast_percentage_equivalent = 0.0
        if project_amount is None or isnan(project_amount) or project_amount == 0:
             print(f"[Toggle Forecast {entry_id}] Invalid project amount: {project_amount}")
        else:
            forecast_percentage_equivalent = calculate_individual_forecast_percent(item, project_amount)
        print(f"  - Pct Equiv: {forecast_percentage_equivalent:.4f}%")
        conn.execute("BEGIN TRANSACTION")
        print(f"[Toggle Forecast {entry_id}] BEGIN TX")
        cursor.execute("UPDATE forecast_items SET is_forecast_completed = ? WHERE id = ?", (new_forecast_status_int, entry_id))
        print(f"[Toggle Forecast {entry_id}] Updated forecast item status.")
        project_status_updated = False
        clamped_new_project_status = project_current_status
        cond_not_deduction = not is_deduction_item
        cond_meaningful_percent = abs(forecast_percentage_equivalent) > 1e-9
        print(f"[Toggle Forecast {entry_id}] Check conditions: NotDeduct={cond_not_deduction}, MeaningfulPct={cond_meaningful_percent}")
        if cond_not_deduction and cond_meaningful_percent:
            if new_forecast_status_int == 1:
                print(f"[Toggle Forecast {entry_id}] ADDING status")
                new_project_status = project_current_status + forecast_percentage_equivalent
                clamped_new_project_status = max(0.0, min(100.0, new_project_status))
                print(f"  - Calc New Status: {new_project_status:.4f} -> Clamped: {clamped_new_project_status:.4f}")
                if abs(clamped_new_project_status - project_current_status) > 1e-9:
                    print("  - Status Changed: True")
                    project_status_updated = True
                else:
                    print("  - Status Changed: False")
                    clamped_new_project_status = project_current_status
            elif new_forecast_status_int == 0:
                print(f"[Toggle Forecast {entry_id}] SUBTRACTING status")
                new_project_status = project_current_status - forecast_percentage_equivalent
                clamped_new_project_status = max(0.0, min(100.0, new_project_status))
                print(f"  - Calc New Status: {new_project_status:.4f} -> Clamped: {clamped_new_project_status:.4f}")
                if abs(clamped_new_project_status - project_current_status) > 1e-9:
                    print("  - Status Changed: True")
                    project_status_updated = True
                else:
                    print("  - Status Changed: False")
                    clamped_new_project_status = project_current_status
        else:
             print(f"[Toggle Forecast {entry_id}] Conditions NOT MET for project status update.")
        if project_status_updated:
            new_remaining_amount = calculate_remaining(project_amount, clamped_new_project_status)
            print(f"  - New Remaining: {new_remaining_amount}")
            print(f"  - UPDATING project {project_id}: status={clamped_new_project_status:.4f}, remaining={new_remaining_amount}")
            cursor.execute(
                "UPDATE projects SET status = ?, remaining_amount = ? WHERE id = ?",
                (clamped_new_project_status, new_remaining_amount, project_id)
            )
        conn.commit()
        print(f"[Toggle Forecast {entry_id}] COMMIT TX")
        cursor.execute("""
            SELECT fi.id as forecast_entry_id, fi.project_id, fi.forecast_input_type,
                   fi.forecast_input_value, fi.is_forecast_completed, fi.forecast_date,
                   fi.is_deduction,
                   p.project_no, p.project_name, p.amount as project_amount,
                   p.status as project_status, p.pic as project_pic
            FROM forecast_items fi JOIN projects p ON fi.project_id = p.id
            WHERE fi.id = ?
        """, (entry_id,))
        updated_item_row = cursor.fetchone()
        updated_entry_data = dict(updated_item_row) if updated_item_row else {}
        if updated_entry_data:
            updated_entry_data['is_forecast_completed'] = bool(updated_entry_data['is_forecast_completed'])
            updated_entry_data['is_deduction'] = bool(updated_entry_data['is_deduction'])
        message = f"Forecast entry marked {'Complete' if new_forecast_status_int == 1 else 'Incomplete'}."
        if project_status_updated:
            message += f" Project {project_id} status updated."
        print(f"[Toggle Forecast {entry_id}] Response: {message}")
        print(f"--- End Toggle {entry_id} ---")
        return jsonify({"message": message, "updated_entry": updated_entry_data}), 200
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"[Toggle Forecast {entry_id}] DB Error: {db_err}")
        traceback.print_exc()
        return jsonify({"error": f"DB error toggling completion: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"[Toggle Forecast {entry_id}] Unexpected Error: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected error toggling completion."}), 500
    finally:
        if conn: conn.close()

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

# --- Project Task API Endpoints ---
@app.route('/api/projects/<int:project_id>/tasks', methods=['GET'])
@role_required(VALID_ROLES) 
def get_project_tasks(project_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Project not found"}), 404
        cursor.execute("""
            SELECT task_id, project_id, task_name, start_date, end_date,
                   planned_weight, actual_start, actual_end, assigned_to, parent_task_id
            FROM project_tasks WHERE project_id = ?
            ORDER BY parent_task_id NULLS FIRST, start_date, task_id
        """, (project_id,))
        tasks = [dict(row) for row in cursor.fetchall()]
        return jsonify(tasks), 200
    except Exception as e:
        print(f"Error fetching tasks for project {project_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error fetching project tasks."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/projects/<int:project_id>/tasks', methods=['POST'])
@role_required([ADMIN, DS_ENGINEER]) 
def add_project_task(project_id):
    data = request.get_json()
    if not data or not data.get('task_name') or str(data['task_name']).strip() == '':
        return jsonify({"error": "Missing or empty 'task_name'"}), 400
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM projects WHERE id = ?", (project_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Project not found"}), 404
        task_name = str(data['task_name']).strip()
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        planned_weight = safe_float(data.get('planned_weight'), default=0.0)
        actual_start = data.get('actual_start')
        actual_end = data.get('actual_end')
        assigned_to = data.get('assigned_to')
        parent_task_id = data.get('parent_task_id')
        validated_parent_id = None
        date_fields = {'start_date': start_date, 'end_date': end_date,
                       'actual_start': actual_start, 'actual_end': actual_end}
        for field_name, date_val in date_fields.items():
            if date_val and str(date_val).strip():
                if not is_valid_date_format(str(date_val).strip()):
                     return jsonify({"error": f"Invalid {field_name} format: '{date_val}'. Use yyyy-MM-dd."}), 400
                date_fields[field_name] = str(date_val).strip()
            else:
                date_fields[field_name] = None
        if parent_task_id is not None:
            parent_id_int = safe_int(parent_task_id)
            if parent_id_int is None:
                return jsonify({"error": f"Invalid 'parent_task_id': '{parent_task_id}'."}), 400
            cursor.execute("SELECT task_id FROM project_tasks WHERE task_id = ? AND project_id = ?", (parent_id_int, project_id))
            if not cursor.fetchone():
                return jsonify({"error": f"Parent task ID {parent_id_int} not found in project {project_id}."}), 400
            validated_parent_id = parent_id_int
        cursor.execute("""
            INSERT INTO project_tasks (project_id, task_name, start_date, end_date, planned_weight,
                                       actual_start, actual_end, assigned_to, parent_task_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (project_id, task_name, date_fields['start_date'], date_fields['end_date'], planned_weight,
              date_fields['actual_start'], date_fields['actual_end'], assigned_to, validated_parent_id))
        new_task_id = cursor.lastrowid
        conn.commit()
        cursor.execute("SELECT * FROM project_tasks WHERE task_id = ?", (new_task_id,))
        new_task_row = cursor.fetchone()
        if new_task_row:
            return jsonify(dict(new_task_row)), 201
        else:
            print(f"Error retrieving new task {new_task_id}.")
            return jsonify({"message": "Task added, but failed to retrieve."}), 207
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error adding task: {db_err}")
        return jsonify({"error": f"DB error adding task: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error adding task: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected server error adding task"}), 500
    finally:
        if conn: conn.close()

@app.route('/api/tasks/<int:task_id>', methods=['PUT'])
@role_required([ADMIN, DS_ENGINEER]) 
def update_project_task(task_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Missing JSON data"}), 400
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT task_id, project_id FROM project_tasks WHERE task_id = ?", (task_id,))
        task = cursor.fetchone()
        if not task:
            return jsonify({"error": "Task not found"}), 404
        current_project_id = task['project_id']
        allowed_fields = ['task_name', 'start_date', 'end_date', 'planned_weight',
                          'actual_start', 'actual_end', 'assigned_to', 'parent_task_id']
        fields_to_update = {}
        validation_errors = []
        for field in allowed_fields:
            if field in data:
                value = data[field]
                sanitized_value = None
                error_msg = None
                if field == 'task_name':
                    sanitized_value = str(value).strip()
                    if not sanitized_value: error_msg = "Task name cannot be empty."
                elif field == 'planned_weight':
                    sanitized_value = safe_float(value, default=None)
                    if sanitized_value is None: error_msg = f"Invalid planned_weight: '{value}'."
                    else: sanitized_value = max(0.0, sanitized_value)
                elif field == 'parent_task_id':
                    if value is None or str(value).strip() == '':
                        sanitized_value = None
                    else:
                        parent_id = safe_int(value)
                        if parent_id is None: error_msg = f"Invalid parent_task_id: '{value}'."
                        elif parent_id == task_id: error_msg = "Task cannot be its own parent."
                        else:
                            cursor.execute("SELECT task_id FROM project_tasks WHERE task_id = ? AND project_id = ?", (parent_id, current_project_id))
                            if not cursor.fetchone(): error_msg = f"Parent task ID {parent_id} not found in project {current_project_id}."
                            else: sanitized_value = parent_id
                elif field in ['start_date', 'end_date', 'actual_start', 'actual_end']:
                    str_val = str(value).strip() if value is not None else None
                    if str_val == '': sanitized_value = None
                    elif str_val and not is_valid_date_format(str_val):
                        error_msg = f"Invalid date format for '{field}': '{value}'. Use yyyy-MM-dd or empty."
                    else: sanitized_value = str_val
                else: 
                    sanitized_value = str(value).strip() if value is not None else None
                    if field == 'assigned_to' and sanitized_value == '':
                        sanitized_value = None
                if error_msg:
                    validation_errors.append(error_msg)
                else:
                    fields_to_update[field] = sanitized_value
        if validation_errors:
            return jsonify({"error": "Validation failed.", "details": validation_errors}), 400
        if not fields_to_update:
            return jsonify({"message": "No valid fields provided for update."}), 200
        set_clause = ", ".join([f"`{field}` = ?" for field in fields_to_update])
        update_values = list(fields_to_update.values()) + [task_id]
        sql = f"UPDATE project_tasks SET {set_clause} WHERE task_id = ?"
        cursor.execute(sql, tuple(update_values))
        conn.commit()
        cursor.execute("SELECT * FROM project_tasks WHERE task_id = ?", (task_id,))
        updated_task_row = cursor.fetchone()
        if updated_task_row:
            return jsonify(dict(updated_task_row)), 200
        else:
            print(f"Error retrieving updated task {task_id}.")
            return jsonify({"message": "Task updated, but failed to retrieve."}), 207
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error updating task {task_id}: {db_err}")
        return jsonify({"error": f"Database error updating task: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error updating task {task_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected server error updating task"}), 500
    finally:
        if conn: conn.close()

@app.route('/api/tasks/<int:task_id>', methods=['DELETE'])
@role_required([ADMIN, DS_ENGINEER]) 
def delete_project_task(task_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT task_id FROM project_tasks WHERE task_id = ?", (task_id,))
        if not cursor.fetchone():
            return jsonify({"error": "Task not found"}), 404
        cursor.execute("DELETE FROM project_tasks WHERE task_id = ?", (task_id,))
        conn.commit()
        if cursor.rowcount > 0:
            print(f"Task {task_id} deleted.")
            return jsonify({"message": "Task deleted successfully."}), 200
        else:
            print(f"Delete failed unexpectedly for task {task_id}.")
            return jsonify({"error": "Delete failed."}), 500
    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error deleting task {task_id}: {db_err}")
        return jsonify({"error": f"Database error deleting task: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error deleting task {task_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Unexpected error deleting task."}), 500
    finally:
        if conn: conn.close()

# --- MRF API Endpoints ---
@app.route('/api/mrf', methods=['POST'])
@role_required(MRF_MANAGEMENT_ROLES)
def save_mrf():
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    header_data = data.get('header', {})
    table_rows_data = data.get('tableRows', [])
    footer_data = data.get('footerSignatories', {})
    form_no = header_data.get('formNo')
    if not form_no or not str(form_no).strip():
        return jsonify({"error": "Form No. is required."}), 400
    form_no = str(form_no).strip()
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM mrf_headers WHERE form_no = ?", (form_no,))
        if cursor.fetchone():
            return jsonify({"error": f"MRF with Form No. '{form_no}' already exists."}), 409 
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
            form_no, header_data.get('mrfDate'), header_data.get('projectName'), header_data.get('projectNumber'),
            header_data.get('client'), header_data.get('siteLocation'), header_data.get('projectPhase', 'Execution'),
            header_data.get('headerPreparedByName'), header_data.get('headerPreparedByDesignation'),
            header_data.get('headerApprovedByName'), header_data.get('headerApprovedByDesignation'),
            footer_data.get('footerPreparedByName'), footer_data.get('footerPreparedByDesignation'),
            footer_data.get('footerApprovedByName'), footer_data.get('footerApprovedByDesignation'),
            footer_data.get('footerNotedByName'), footer_data.get('footerNotedByDesignation')
        ))
        mrf_header_id = cursor.lastrowid
        for item_row_container in table_rows_data:
            item_values = item_row_container.get('values', {})
            if not item_values.get('description') and not item_values.get('partNo'): 
                continue
            cursor.execute("""
                INSERT INTO mrf_items (
                    mrf_header_id, item_no, part_no, brand_name, description, qty, uom, install_date, remarks,
                    status, actual_delivery_date 
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, ( 
                mrf_header_id, item_values.get('itemNo'), item_values.get('partNo'), item_values.get('brandName'),
                item_values.get('description'), safe_float(item_values.get('qty'), 0), item_values.get('uom'),
                item_values.get('installDate'), item_values.get('remarks'),
                item_values.get('status', 'Processing'), # Updated default status
                item_values.get('actual_delivery_date') 
            ))
        conn.commit()
        return jsonify({"message": "MRF saved successfully!", "form_no": form_no, "mrf_id": mrf_header_id}), 201
    except sqlite3.IntegrityError as e:
        if conn: conn.rollback()
        if "UNIQUE constraint failed: mrf_headers.form_no" in str(e):
             return jsonify({"error": f"MRF with Form No. '{form_no}' already exists (Integrity Error)."}), 409
        print(f"DB Integrity Error saving MRF: {e}")
        return jsonify({"error": "Database integrity error saving MRF."}), 500
    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"DB Error saving MRF: {e}")
        traceback.print_exc()
        return jsonify({"error": "Database error saving MRF."}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error saving MRF: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred while saving the MRF."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/mrfs', methods=['GET'])
@role_required(MRF_VIEW_ROLES) 
def get_mrf_list():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, form_no, project_name, project_number, mrf_date FROM mrf_headers ORDER BY mrf_date DESC, form_no DESC")
        mrfs = [dict(row) for row in cursor.fetchall()]
        return jsonify(mrfs), 200
    except Exception as e:
        print(f"Error fetching MRF list: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error fetching MRF list."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/mrf/<string:form_no>', methods=['GET'])
@role_required(MRF_VIEW_ROLES) 
def get_mrf_by_form_no(form_no):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM mrf_headers WHERE form_no = ?", (form_no,))
        header_row_db = cursor.fetchone()

        if not header_row_db:
            print(f"MRF not found for form_no: {form_no}")
            return jsonify({"error": "MRF not found."}), 404

        mrf_header_id = header_row_db['id'] if 'id' in header_row_db.keys() else None
        if mrf_header_id is None:
            print(f"Critical error: MRF header for form_no {form_no} is missing 'id' column or value.")
            return jsonify({"error": "MRF header data is incomplete (missing ID)."}), 500

        header_data_for_json = {}
        header_key_map = {
            "form_no": "formNo", 
            "mrf_date": "mrfDate",
            "project_name": "projectName",
            "project_number": "projectNumber",
            "client": "client",
            "site_location": "siteLocation",
            "project_phase": "projectPhase",
        }
        for db_key, json_key in header_key_map.items():
            header_data_for_json[json_key] = header_row_db[db_key] if db_key in header_row_db.keys() else None
        
        if header_data_for_json.get('formNo') is None and ('form_no' in header_row_db.keys() and header_row_db['form_no'] is not None):
             header_data_for_json['formNo'] = header_row_db['form_no']

        footer_signatories_for_json = {}
        footer_key_map = {
            "footer_prepared_by_name": "footerPreparedByName",
            "footer_prepared_by_designation": "footerPreparedByDesignation",
            "footer_approved_by_name": "footerApprovedByName",
            "footer_approved_by_designation": "footerApprovedByDesignation",
            "footer_noted_by_name": "footerNotedByName",
            "footer_noted_by_designation": "footerNotedByDesignation",
        }
        for db_key, json_key in footer_key_map.items():
            footer_signatories_for_json[json_key] = header_row_db[db_key] if db_key in header_row_db.keys() else None

        mrf_data_response = {
            "header": header_data_for_json,
            "tableRows": [],
            "footerSignatories": footer_signatories_for_json
        }
        
        cursor.execute("""
            SELECT id, item_no, part_no, brand_name, description, qty, uom, 
                   install_date, remarks, status, actual_delivery_date 
            FROM mrf_items 
            WHERE mrf_header_id = ? ORDER BY id
        """, (mrf_header_id,))
        items_rows_db = cursor.fetchall()

        for item_row_db in items_rows_db:
            item_values_camel_case = {
                "id": item_row_db['id'] if 'id' in item_row_db.keys() else None, 
                "itemNo": item_row_db['item_no'] if 'item_no' in item_row_db.keys() else None,
                "partNo": item_row_db['part_no'] if 'part_no' in item_row_db.keys() else None,
                "brandName": item_row_db['brand_name'] if 'brand_name' in item_row_db.keys() else None,
                "description": item_row_db['description'] if 'description' in item_row_db.keys() else None,
                "qty": item_row_db['qty'] if 'qty' in item_row_db.keys() else None,
                "uom": item_row_db['uom'] if 'uom' in item_row_db.keys() else None,
                "installDate": item_row_db['install_date'] if 'install_date' in item_row_db.keys() else None,
                "remarks": item_row_db['remarks'] if 'remarks' in item_row_db.keys() else None,
                "status": item_row_db['status'] if 'status' in item_row_db.keys() else "Processing", # Default if status is missing
                "actualDeliveryDate": item_row_db['actual_delivery_date'] if 'actual_delivery_date' in item_row_db.keys() else None
            }
            mrf_data_response["tableRows"].append({"values": item_values_camel_case})
            
        return jsonify(mrf_data_response), 200

    except sqlite3.Error as db_err: 
        print(f"Database error fetching MRF {form_no}: {db_err}")
        traceback.print_exc()
        return jsonify({"error": f"Database error while fetching MRF data: {db_err}"}), 500
    except KeyError as ke: 
        print(f"Key error fetching MRF {form_no}: Missing key {ke}")
        traceback.print_exc()
        return jsonify({"error": f"Data inconsistency error: Missing expected field '{ke}'."}), 500
    except Exception as e: 
        print(f"Unexpected error fetching MRF {form_no}: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected server error occurred while fetching MRF data."}), 500
    finally:
        if conn:
            conn.close()

# New endpoint for MRF Items Log
@app.route('/api/mrf/items/log', methods=['GET'])
@role_required(MRF_VIEW_ROLES)
def get_mrf_items_log():
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 
                mi.id, mi.item_no, mi.part_no, mi.brand_name, mi.description,
                mi.qty, mi.uom, mi.install_date, mi.remarks, mi.status, mi.actual_delivery_date,
                mh.form_no, mh.project_name, mh.mrf_date
            FROM mrf_items mi
            JOIN mrf_headers mh ON mi.mrf_header_id = mh.id
            ORDER BY mh.mrf_date DESC, mh.form_no DESC, mi.id ASC
        """)
        items = [dict(row) for row in cursor.fetchall()]
        return jsonify(items), 200
    except sqlite3.Error as db_err:
        print(f"Database error fetching MRF items log: {db_err}")
        traceback.print_exc()
        return jsonify({"error": f"Database error fetching MRF items log: {db_err}"}), 500
    except Exception as e:
        print(f"Unexpected error fetching MRF items log: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected server error occurred while fetching MRF items log."}), 500
    finally:
        if conn:
            conn.close()


@app.route('/api/project/<string:project_no>/mrfs_with_items', methods=['GET'])
@role_required(MRF_VIEW_ROLES)
def get_project_mrfs_with_items(project_no):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id, project_name FROM projects WHERE project_no = ?", (project_no,))
        project_context = cursor.fetchone()
        if not project_context:
             return jsonify({"error": f"Project with number '{project_no}' not found."}), 404
        cursor.execute("SELECT * FROM mrf_headers WHERE project_number = ? ORDER BY mrf_date DESC, id DESC", (project_no,))
        mrf_headers = cursor.fetchall()
        result_mrfs = []
        for header_row in mrf_headers:
            mrf_detail = {"header": dict(header_row), "items": []}
            header_id = header_row['id'] if 'id' in header_row.keys() else None
            if header_id is None:
                print(f"Warning: MRF Header {header_row['form_no'] if 'form_no' in header_row.keys() else 'N/A'} is missing an ID.")
                continue 

            cursor.execute("SELECT id, item_no, part_no, brand_name, description, qty, uom, install_date, remarks, status, actual_delivery_date FROM mrf_items WHERE mrf_header_id = ? ORDER BY id", (header_id,))
            items_rows = cursor.fetchall()
            for item_row in items_rows:
                mrf_detail["items"].append(dict(item_row))
            result_mrfs.append(mrf_detail)
        return jsonify({
            "project_name": project_context["project_name"], 
            "project_number": project_no,
            "mrfs": result_mrfs
            }), 200
    except Exception as e:
        print(f"Error fetching MRFs for project {project_no}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Error fetching MRFs for project."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/mrf/item/<int:item_id>', methods=['PUT'])
@role_required(MRF_MANAGEMENT_ROLES) 
def update_mrf_item_status(item_id):
    data = request.get_json()
    if not data:
        return jsonify({"error": "Invalid data"}), 400
    new_status = data.get('status')
    new_delivery_date = data.get('actual_delivery_date') 

    if new_status is None and ('actual_delivery_date' not in data) : 
        return jsonify({"error": "No status or delivery date provided for update."}), 400
        
    valid_statuses = ["Processing", "Pending Approval", "For Purchase Order", "Awaiting Delivery", "Delivered to CMR", "Delivered to Site", "Cancelled", "On Hold"]
    if new_status is not None and new_status not in valid_statuses:
        return jsonify({"error": f"Invalid status value. Must be one of: {', '.join(valid_statuses)}"}), 400
    
    validated_delivery_date = None
    if 'actual_delivery_date' in data: 
        if new_delivery_date is not None and new_delivery_date.strip() != "": 
            parsed_date = parse_flexible_date(new_delivery_date)
            if not parsed_date:
                return jsonify({"error": "Invalid actual_delivery_date format. Use yyyy-MM-dd or MM/dd/yyyy."}), 400
            validated_delivery_date = parsed_date.isoformat()
        else: 
            validated_delivery_date = None


    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM mrf_items WHERE id = ?", (item_id,))
        if not cursor.fetchone():
            return jsonify({"error": "MRF item not found."}), 404
        
        fields_to_update = []
        params = []

        if new_status is not None:
            fields_to_update.append("status = ?")
            params.append(new_status)
        
        if 'actual_delivery_date' in data: 
            fields_to_update.append("actual_delivery_date = ?")
            params.append(validated_delivery_date) 

        if not fields_to_update: 
             return jsonify({"message": "No valid changes to apply."}), 200 

        params.append(item_id)
        sql = f"UPDATE mrf_items SET {', '.join(fields_to_update)} WHERE id = ?"
        
        cursor.execute(sql, tuple(params))
        conn.commit()

        if cursor.rowcount > 0:
            cursor.execute("SELECT * FROM mrf_items WHERE id = ?", (item_id,))
            updated_item_row = cursor.fetchone()
            updated_item = dict(updated_item_row) if updated_item_row else None
            return jsonify({"message": "MRF item updated successfully.", "item": updated_item}), 200
        else:
            cursor.execute("SELECT * FROM mrf_items WHERE id = ?", (item_id,)) 
            current_item = dict(cursor.fetchone()) if cursor.fetchone() else {}
            return jsonify({"message": "No changes applied to MRF item (values might be the same).", "item": current_item }), 200

    except sqlite3.Error as e:
        if conn: conn.rollback()
        print(f"DB Error updating MRF item {item_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "Database error updating MRF item."}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error updating MRF item {item_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred."}), 500
    finally:
        if conn: conn.close()

@app.route('/api/mrf/item/<int:item_id>', methods=['DELETE'])
@role_required(MRF_MANAGEMENT_ROLES)
def delete_mrf_item(item_id):
    conn = None
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT id FROM mrf_items WHERE id = ?", (item_id,))
        item = cursor.fetchone()
        if not item:
            return jsonify({"error": "MRF item not found."}), 404
        
        cursor.execute("DELETE FROM mrf_items WHERE id = ?", (item_id,))
        conn.commit()

        if cursor.rowcount > 0:
            print(f"MRF Item ID {item_id} deleted by user {session.get('username', 'Unknown')}.")
            return jsonify({"message": "MRF item deleted successfully.", "deleted_item_id": item_id}), 200
        else:
            print(f"Delete operation for MRF Item ID {item_id} reported 0 rows affected, though item was found.")
            return jsonify({"error": "Delete operation failed unexpectedly or item was already deleted."}), 500

    except sqlite3.Error as db_err:
        if conn: conn.rollback()
        print(f"DB error deleting MRF item {item_id}: {db_err}")
        traceback.print_exc()
        return jsonify({"error": f"Database error deleting MRF item: {db_err}"}), 500
    except Exception as e:
        if conn: conn.rollback()
        print(f"Unexpected error deleting MRF item {item_id}: {e}")
        traceback.print_exc()
        return jsonify({"error": "An unexpected error occurred during MRF item deletion."}), 500
    finally:
        if conn: conn.close()


# --- Static File Serving & Main Execution ---
@app.route('/')
@role_required(VALID_ROLES) 
def index():
    return send_from_directory(app.static_folder, 'index.html')

@app.route('/forecast')
@role_required(VALID_ROLES)
def forecast_page():
    return send_from_directory(app.static_folder, 'forecast.html')

@app.route('/mrf_form')
@role_required(MRF_MANAGEMENT_ROLES) 
def mrf_form_page():
    return send_from_directory(app.static_folder, 'mrf_form.html')

@app.route('/project_mrf_status/<string:project_no>') 
@role_required(MRF_VIEW_ROLES) 
def project_mrf_status_page(project_no):
    return send_from_directory(app.static_folder, 'project_mrf_status.html')

@app.route('/mrf_items_log') # Route for the new MRF Items Log page
@role_required(MRF_VIEW_ROLES) 
def mrf_items_log_page():
    return send_from_directory(app.static_folder, 'mrf_items_log.html')


@app.route('/updates_log')
@role_required(VALID_ROLES) 
def updates_log_page():
    return send_from_directory(app.static_folder, 'updates_log.html')

@app.route('/project_gantt')
@role_required(VALID_ROLES) 
def project_gantt_page():
    return send_from_directory(app.static_folder, 'project_gantt.html')

# Removed the duplicate /login route that was here. 
# The primary one is defined under "Authentication Endpoints".

# --- Main Execution Block ---
if __name__ == '__main__':
    print("Running database initialization...")
    init_db() 
    # --- Add Initial Admin User (Example - Run once or manage users separately) ---
    # conn = None
    # try:
    #     conn = get_db()
    #     cursor = conn.cursor()
    #     cursor.execute("SELECT id FROM users WHERE username = ?", ('admin',))
    #     if not cursor.fetchone():
    #         print("Creating initial admin user...")
    #         admin_pass = 'YourSecurePassword123!' # <<<--- CHANGE THIS!
    #         hashed_pass = generate_password_hash(admin_pass)
    #         cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
    #                        ('admin', hashed_pass, ADMIN))
    #         conn.commit()
    #         print(" -> Initial admin user 'admin' created.")
    # except sqlite3.Error as e:
    #     print(f"DB error during admin user check/creation: {e}")
    #     if conn: conn.rollback()
    # finally:
    #     if conn: conn.close()
    # ---------------------------------------------------------------------
    print("-" * 30)
    print("Starting Flask Server...")
    host_ip = '0.0.0.0' 
    port = 5000
    debug_mode = False 
    use_reloader = False 
    print(f" * Environment: Production/LAN")
    print(f" * Debug Mode: {'ON' if debug_mode else 'OFF'}")
    print(f" * Binding to: {host_ip}:{port}")
    print(f" * Accessible via http://<your-server-ip>:{port}/")
    print(f" * Login page: http://<your-server-ip>:{port}/login")
    print(" * Press CTRL+C to quit")
    print("-" * 30)
    try:
        from waitress import serve
        print(f" * Starting Waitress server on {host_ip}:{port}...")
        serve(app, host=host_ip, port=port, threads=8)
    except ImportError:
        print("\n--- WARNING: 'waitress' not installed ---")
        print("     For better performance, install it: pip install waitress")
        print("     Falling back to Flask's development server...\n")
        print(f" * Starting Flask development server on {host_ip}:{port}...")
        app.run(host=host_ip, port=port, debug=debug_mode, use_reloader=use_reloader)