#!/usr/bin/env python
"""
Database connection test script for the DS Monitoring App.
Tests connection to the Neon PostgreSQL database.
"""

import os
import sys
import psycopg2
from dotenv import load_dotenv

def test_db_connection():
    """Test the database connection using environment variables."""
    load_dotenv()  # Load environment variables from .env file
    
    # Get database connection params from environment
    db_params = {
        "dbname": os.environ.get("PGDATABASE", "ds_monitoring"),
        "user": os.environ.get("PGUSER", "TJ"),
        "password": os.environ.get("PGPASSWORD", "npg_fgM8vu5TCYoy"),
        "host": os.environ.get("PGHOST", "ep-blue-recipe-13945216.us-east-2.aws.neon.tech"),
        "port": os.environ.get("PGPORT", "5432"),
        "sslmode": os.environ.get("PGSSLMODE", "require"),
    }
    
    print("Attempting to connect to PostgreSQL database...")
    print(f"Host: {db_params['host']}")
    print(f"Database: {db_params['dbname']}")
    print(f"User: {db_params['user']}")
    
    try:
        # Establish connection
        conn = psycopg2.connect(**db_params)
        cursor = conn.cursor()
        
        # Test query
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        print("Connection successful!")
        print(f"PostgreSQL server version: {version[0]}")
        
        # Close connection
        cursor.close()
        conn.close()
        return True
    
    except psycopg2.Error as e:
        print(f"Error connecting to the database: {e}")
        return False
    
if __name__ == "__main__":
    print("\nDatabase connection test for DS Monitoring App")
    print("=" * 50)
    try:
        import psycopg2
    except ImportError:
        print("ERROR: psycopg2 module is not installed.")
        print("Install it using: pip install psycopg2-binary")
        sys.exit(1)
        
    try:
        from dotenv import load_dotenv
    except ImportError:
        print("ERROR: python-dotenv module is not installed.")
        print("Install it using: pip install python-dotenv")
        sys.exit(1)
        
    print("All required modules are installed.")
    print("Testing database connection...")
    success = test_db_connection()
    
    if success:
        print("\nSUCCESS: Database connection established!")
    else:
        print("\nFAILED: Could not connect to the database.")
        print("Please check your .env file and internet connection.")
    
    sys.exit(0 if success else 1)
