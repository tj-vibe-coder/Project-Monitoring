import psycopg2
import traceback
import os
import sys

print("Starting PostgreSQL connection test...")
sys.stdout.flush()

# Connection string
connection_string = "postgresql://neondb_owner:npg_keiHc0G4bIXP@ep-sweet-firefly-a8fhichc-pooler.eastus2.azure.neon.tech/projectmonitoring?sslmode=require"

print(f"Using connection string with host: {connection_string.split('@')[1].split('/')[0]}")
sys.stdout.flush()

try:
    print("Attempting to connect...")
    sys.stdout.flush()
    
    # Connect to PostgreSQL
    conn = psycopg2.connect(connection_string)
    
    print("Connection established! Creating cursor...")
    sys.stdout.flush()
    
    # Create a cursor
    cursor = conn.cursor()
    
    # Execute a test query
    print("Executing test query...")
    sys.stdout.flush()
    cursor.execute("SELECT version();")
    
    # Fetch the result
    version = cursor.fetchone()
    print("Successfully connected to PostgreSQL!")
    print(f"PostgreSQL version: {version[0]}")
    sys.stdout.flush()
    
    # Close the connection
    cursor.close()
    conn.close()
    print("Connection closed properly.")
    
except Exception as e:
    print(f"Error connecting to PostgreSQL: {e}")
    traceback.print_exc()
    sys.stdout.flush()
