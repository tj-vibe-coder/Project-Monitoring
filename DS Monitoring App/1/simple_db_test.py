import psycopg2
import psycopg2.extras
import time

# Define database connection string
connection_string = "postgresql://neondb_owner:npg_keiHc0G4bIXP@ep-sweet-firefly-a8fhichc-pooler.eastus2.azure.neon.tech/projectmonitoring?sslmode=require"

print("Starting connection test...")

try:
    print(f"Connecting to PostgreSQL at {connection_string.split('@')[1].split('/')[0]}")
    time.sleep(1)
    conn = psycopg2.connect(connection_string)
    print("Connection established!")
    
    cursor = conn.cursor()
    print("Running test query...")
    time.sleep(1)
    
    cursor.execute("SELECT version();")
    version = cursor.fetchone()
    print(f"PostgreSQL version: {version[0]}")
    time.sleep(1)
    
    print("Closing connection...")
    cursor.close()
    conn.close()
    print("Test completed successfully!")
    
except Exception as e:
    print(f"Connection failed: {e}")
    import traceback
    traceback.print_exc()
