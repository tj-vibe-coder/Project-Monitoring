import sqlite3
import os
import sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import init_db, get_db

print("Starting database initialization...")

if os.path.exists('projects.db'):
    os.remove('projects.db')
    print("Removed existing database file")

init_db()
print("Database initialized")

# Add test data
conn = sqlite3.connect('projects.db')
cursor = conn.cursor()

try:
    # Add test project
    cursor.execute("""
        INSERT INTO projects (
            ds, year, project_no, client, project_name, amount, status, pic
        ) VALUES (
            'DS1', 2025, 'P2025-001', 'Test Client', 'Test Project 1', 1000000.00, 0.0, 'JNL'
        )
    """)
    project_id = cursor.lastrowid
    
    # Add forecast items for the project
    current_date = '2025-06-06'  # Current date
    next_month = '2025-07-06'    # Next month
    
    cursor.execute("""
        INSERT INTO forecast_items (
            project_id, forecast_date, forecast_input_type, forecast_input_value, is_forecast_completed, is_deduction
        ) VALUES 
        (?, ?, 'amount', 250000.00, 0, 0),
        (?, ?, 'percent', 25.0, 0, 0)
    """, (project_id, current_date, project_id, next_month))
    
    conn.commit()
    print("Test data added successfully")

except sqlite3.Error as e:
    print(f"Error adding test data: {e}")
    conn.rollback()

finally:
    conn.close()
