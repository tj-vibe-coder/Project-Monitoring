import psycopg2
import psycopg2.extras
import os
import traceback
import sys

# Define database connection string
DB_URL = "postgresql://neondb_owner:npg_keiHc0G4bIXP@ep-sweet-firefly-a8fhichc-pooler.eastus2.azure.neon.tech/projectmonitoring?sslmode=require"

def main():
    print("\n===== PostgreSQL Connection Test =====")
    print(f"Trying to connect to: {DB_URL.split('@')[1].split('/')[0]}")
    
    try:
        # Establish connection
        print("Connecting to database...")
        conn = psycopg2.connect(DB_URL, cursor_factory=psycopg2.extras.DictCursor)
        print("Connection established!")
        
        # Create a cursor
        cursor = conn.cursor()
        
        # Execute version query
        print("Executing version query...")
        cursor.execute("SELECT version();")
        version = cursor.fetchone()[0]
        print(f"PostgreSQL version: {version}")
        
        # List tables
        print("\nListing database tables:")
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        
        tables = cursor.fetchall()
        if tables:
            for i, table_row in enumerate(tables, 1):
                print(f"{i}. {table_row[0]}")
        else:
            print("No tables found in database.")
            
        # Create test table if it doesn't exist
        print("\nTesting table creation...")
        try:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS test_connection (
                    id SERIAL PRIMARY KEY,
                    test_name VARCHAR(100),
                    test_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            conn.commit()
            print("Test table created successfully!")
            
            # Insert test data
            cursor.execute("""
                INSERT INTO test_connection (test_name)
                VALUES ('Connection test') RETURNING id;
            """)
            new_id = cursor.fetchone()[0]
            conn.commit()
            print(f"Test row inserted with ID: {new_id}")
            
        except Exception as e:
            print(f"Error during table operations: {e}")
            conn.rollback()
        
        # Close connection
        cursor.close()
        conn.close()
        print("\nConnection closed properly.")
        print("===== Test completed successfully! =====")
        return True
        
    except Exception as e:
        print(f"\nERROR: Connection failed: {e}")
        traceback.print_exc()
        print("\n===== Test failed! =====")
        return False

if __name__ == "__main__":
    success = main()
    # Exit with appropriate code for CI/CD systems
    sys.exit(0 if success else 1)
