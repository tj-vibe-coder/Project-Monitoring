import os
from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()

class Config:
    # Database Configuration
    # Try to build URL from Railway's individual environment variables if available
    if all(os.getenv(var) for var in ['PGHOST', 'PGPORT', 'PGUSER', 'PGPASSWORD', 'PGDATABASE']):
        SQLALCHEMY_DATABASE_URI = f"postgresql://{os.getenv('PGUSER')}:{os.getenv('PGPASSWORD')}@{os.getenv('PGHOST')}:{os.getenv('PGPORT')}/{os.getenv('PGDATABASE')}"
    else:
        # Fallback to DATABASE_URL or SQLite
        SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URL', 'sqlite:///projects.db')
        
    # Ensure proper PostgreSQL URL format
    if SQLALCHEMY_DATABASE_URI.startswith('postgres://'):
        SQLALCHEMY_DATABASE_URI = SQLALCHEMY_DATABASE_URI.replace('postgres://', 'postgresql://', 1)
    
    # Flask Configuration
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY', os.urandom(24))
    
    # SQLAlchemy Configuration
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True to see SQL queries in console
    
    # Application Configuration
    MAX_UPDATES_PER_PROJECT = 30
    FORECAST_LIMIT = 100
    
    # User Roles
    ADMIN = 'Administrator'
    DS_ENGINEER = 'DS Engineer'
    PROCUREMENT = 'Procurement'
    FINANCE = 'Finance'
    GUEST = 'Guest'
    
    VALID_ROLES = [ADMIN, DS_ENGINEER, PROCUREMENT, FINANCE, GUEST]
    MRF_MANAGEMENT_ROLES = [ADMIN, DS_ENGINEER, PROCUREMENT]
    MRF_VIEW_ROLES = [ADMIN, DS_ENGINEER, PROCUREMENT, FINANCE, GUEST] 