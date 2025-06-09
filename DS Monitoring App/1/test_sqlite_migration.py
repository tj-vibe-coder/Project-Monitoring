#!/usr/bin/env python3
"""
Test script to verify SQLite migration is working correctly
"""
import sqlite3
import json
from app import get_db, init_db

def test_database_connection():
    """Test basic database connection"""
    print("Testing database connection...")
    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        conn.close()
        print("✓ Database connection successful")
        return True
    except Exception as e:
        print(f"✗ Database connection failed: {e}")
        return False

def test_tables_exist():
    """Test that all required tables exist"""
    print("Testing table existence...")
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check all required tables
        expected_tables = ['users', 'projects', 'project_updates', 'forecast_items', 'project_tasks', 'mrf_headers', 'mrf_items']
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
        existing_tables = [row[0] for row in cursor.fetchall()]
        
        missing_tables = []
        for table in expected_tables:
            if table not in existing_tables:
                missing_tables.append(table)
        
        if missing_tables:
            print(f"✗ Missing tables: {missing_tables}")
            conn.close()
            return False
        
        print(f"✓ All required tables exist: {existing_tables}")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Table check failed: {e}")
        return False

def test_basic_queries():
    """Test basic CRUD operations"""
    print("Testing basic database queries...")
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Test a simple SELECT query on projects table
        cursor.execute("SELECT COUNT(*) FROM projects")
        project_count = cursor.fetchone()[0]
        print(f"✓ Projects table query successful, found {project_count} projects")
        
        # Test a simple SELECT query on users table
        cursor.execute("SELECT COUNT(*) FROM users")
        user_count = cursor.fetchone()[0]
        print(f"✓ Users table query successful, found {user_count} users")
        
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Basic queries failed: {e}")
        return False

def test_schema_integrity():
    """Test that the schema is properly set up"""
    print("Testing schema integrity...")
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Test projects table structure
        cursor.execute("PRAGMA table_info(projects)")
        projects_columns = [row[1] for row in cursor.fetchall()]
        expected_columns = ['id', 'ds', 'year', 'project_no', 'client', 'project_name', 'amount', 'status', 'remaining_amount', 'total_running_weeks', 'po_date', 'po_no', 'date_completed', 'pic', 'address']
        
        missing_columns = []
        for col in expected_columns:
            if col not in projects_columns:
                missing_columns.append(col)
        
        if missing_columns:
            print(f"✗ Projects table missing columns: {missing_columns}")
            conn.close()
            return False
        
        print(f"✓ Projects table schema looks good")
        conn.close()
        return True
    except Exception as e:
        print(f"✗ Schema integrity check failed: {e}")
        return False

def main():
    print("=" * 50)
    print("SQLite Migration Test")
    print("=" * 50)
    
    # Initialize database first
    print("Initializing database...")
    try:
        init_db()
        print("✓ Database initialization successful")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
        return
    
    # Run all tests
    tests = [
        test_database_connection,
        test_tables_exist,
        test_basic_queries,
        test_schema_integrity
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            if test():
                passed += 1
            else:
                failed += 1
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            failed += 1
        print()
    
    print("=" * 50)
    print(f"Test Results: {passed} passed, {failed} failed")
    print("=" * 50)
    
    if failed == 0:
        print("🎉 All tests passed! SQLite migration is successful.")
    else:
        print("❌ Some tests failed. Please check the errors above.")

if __name__ == "__main__":
    main()
