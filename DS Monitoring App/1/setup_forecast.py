import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'projects.db')
print(f"Using database at: {DB_PATH}")

# Create or connect to database
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Create projects table
cursor.execute('''
CREATE TABLE IF NOT EXISTS projects (
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
    po_date DATE,
    po_no TEXT,
    date_completed DATE,
    pic TEXT,
    address TEXT
)
''')

# Create forecast_items table
cursor.execute('''
CREATE TABLE IF NOT EXISTS forecast_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id INTEGER NOT NULL,
    forecast_date DATE,
    forecast_input_type TEXT NOT NULL CHECK(forecast_input_type IN ('percent', 'amount')),
    forecast_input_value REAL NOT NULL,
    is_forecast_completed INTEGER NOT NULL DEFAULT 0 CHECK(is_forecast_completed IN (0, 1)),
    is_deduction INTEGER NOT NULL DEFAULT 0 CHECK(is_deduction IN (0, 1)),
    FOREIGN KEY(project_id) REFERENCES projects(id) ON DELETE CASCADE
)
''')

# Add test data
cursor.execute('''
INSERT INTO projects (ds, year, project_no, client, project_name, amount, status, pic)
VALUES ('DS1', 2025, 'P2025-001', 'Test Client', 'Test Project 1', 1000000.00, 0.0, 'JNL')
''')

project_id = cursor.lastrowid

# Add forecast items for current month and next month
current_date = '2025-06-06'
next_month = '2025-07-06'

cursor.execute('''
INSERT INTO forecast_items (project_id, forecast_date, forecast_input_type, forecast_input_value, is_forecast_completed)
VALUES 
    (?, ?, 'amount', 250000.00, 0),
    (?, ?, 'percent', 25.0, 0)
''', (project_id, current_date, project_id, next_month))

conn.commit()
conn.close()

print("Database initialized with test data")
