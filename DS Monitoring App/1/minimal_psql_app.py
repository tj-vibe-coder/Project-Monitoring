import psycopg2
import psycopg2.extras
import os
from dotenv import load_dotenv
from flask import Flask, jsonify

# Load environment variables from .env file
load_dotenv()

app = Flask(__name__)

# PostgreSQL/Neon Configuration
DATABASE_URL = os.environ.get("DATABASE_URL", "postgresql://neondb_owner:npg_keiHc0G4bIXP@ep-sweet-firefly-a8fhichc-pooler.eastus2.azure.neon.tech/projectmonitoring?sslmode=require")

def get_db():
    try:
        # Connect using DATABASE_URL
        conn = psycopg2.connect(
            DATABASE_URL,
            cursor_factory=psycopg2.extras.DictCursor
        )
        return conn
    except Exception as e:
        print(f"PostgreSQL connection error: {e}")
        raise

@app.route('/')
def home():
    return "PostgreSQL Test Connection App"

@app.route('/api/test')
def api_test():
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Test query - check if database is working
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        # Test table listing - check schema access
        cursor.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name;
        """)
        tables = [row[0] for row in cursor.fetchall()]
        
        # Close connection
        cursor.close()
        conn.close()
        
        return jsonify({
            "success": True,
            "version": version[0],
            "tables": tables
        }), 200
    except Exception as e:
        return jsonify({
            "success": False,
            "error": str(e)
        }), 500

if __name__ == '__main__':
    print("Starting minimal PostgreSQL test Flask app...")
    app.run(host='0.0.0.0', port=5000)
