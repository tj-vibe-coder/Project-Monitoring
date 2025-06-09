import psycopg2
import psycopg2.extras
import os
import sys
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

print("=== PostgreSQL Connection Test ===")
sys.stdout.flush()

# Get connection parameters from environment variables
DATABASE_URL = os.environ.get("DATABASE_URL")
PGDATABASE = os.environ.get("PGDATABASE")
PGUSER = os.environ.get("PGUSER")
PGPASSWORD = os.environ.get("PGPASSWORD")
PGHOST = os.environ.get("PGHOST")
PGPORT = os.environ.get("PGPORT")

print(f"Connection Parameters:")
print(f"PGHOST: {PGHOST}")
print(f"PGUSER: {PGUSER}")
print(f"PGDATABASE: {PGDATABASE}")
print(f"PGPORT: {PGPORT}")
print(f"DATABASE_URL is {'set' if DATABASE_URL else 'not set'}")
sys.stdout.flush()

try:
    print("\nAttempting to connect using DATABASE_URL...")
    sys.stdout.flush()
    
    if DATABASE_URL:
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.DictCursor
        )
    else:
        print("\nFalling back to individual parameters...")
        sys.stdout.flush()
        
        conn = psycopg2.connect(
            dbname=PGDATABASE,
            user=PGUSER,
            password=PGPASSWORD,
            host=PGHOST,
            port=PGPORT,
            cursor_factory=psycopg2.extras.DictCursor
        )
    
    print("Connection successful!")
    sys.stdout.flush()
    
    # Create a cursor
    cursor = conn.cursor()
    
    # Test query
    print("\nTesting database query...")
    sys.stdout.flush()
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL version: {version[0]}")
    
    # List all tables to verify connection
    try:
        print("\nListing tables in database:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = cursor.fetchall()
        if tables:
            for table in tables:
                print(f"- {table[0]}")
        else:
            print("No tables found in the database.")
    except Exception as e:
        print(f"Error listing tables: {e}")
        
    # Close the connection
    cursor.close()
    conn.close()
    print("\nConnection closed.")
    
except Exception as e:
    print(f"\nError: {e}")
    import traceback
    traceback.print_exc()
    sys.stdout.flush()
    
print("\n=== Test Complete ===")
sys.stdout.flush()
