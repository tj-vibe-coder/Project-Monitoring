import sys
import os
import subprocess
import logging
from flask import Flask
from models import db
from config import Config
import webbrowser
import time
import pystray
from PIL import Image
import threading
import signal
from dotenv import load_dotenv

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

def create_required_folders():
    """Create necessary folders if they don't exist"""
    folders = ['static', 'logs', 'instance']
    for folder in folders:
        try:
            if not os.path.exists(folder):
                os.makedirs(folder)
                logger.info(f"Created folder: {folder}")
        except Exception as e:
            logger.error(f"Error creating folder {folder}: {str(e)}")
            raise

def check_env_file():
    """Verify .env file exists and contains required variables"""
    if not os.path.exists('.env'):
        logger.error("Missing .env file. Please create one with your database credentials.")
        raise FileNotFoundError("Missing .env file")
    
    load_dotenv()
    required_vars = ['DATABASE_URL']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
        raise ValueError(f"Missing environment variables: {', '.join(missing_vars)}")

def initialize_database():
    """Initialize and verify database connection"""
    try:
        app = Flask(__name__)
        app.config.from_object(Config)
        db.init_app(app)
        
        with app.app_context():
            # Create all tables
            db.create_all()
            logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"Database initialization failed: {str(e)}")
        raise

def run_flask_app():
    """Run the Flask application"""
    try:
        from waitress import serve
        from app import app
        logger.info("Starting server with Waitress...")
        serve(app, host='0.0.0.0', port=5000, threads=8)
    except ImportError:
        logger.warning("Waitress not found, using Flask development server...")
        from app import app
        app.run(host='0.0.0.0', port=5000)
    except Exception as e:
        logger.error(f"Error starting Flask app: {str(e)}")
        raise

def create_tray_icon():
    """Create system tray icon and menu"""
    def open_dashboard(icon, item):
        webbrowser.open('http://localhost:5000')

    def exit_app(icon, item):
        logger.info("Application shutdown initiated from system tray")
        icon.stop()
        os._exit(0)

    try:
        # Load the custom icon
        icon_path = os.path.join(os.path.dirname(__file__), 'icon.png')
        if os.path.exists(icon_path):
            icon_image = Image.open(icon_path)
        else:
            logger.warning("Custom icon not found, using default")
            icon_size = (64, 64)
            icon_image = Image.new('RGB', icon_size, 'blue')
        
        # Create the tray icon
        icon = pystray.Icon(
            "DS Monitoring",
            icon_image,
            "DS Monitoring App",
            menu=pystray.Menu(
                pystray.MenuItem("Open Dashboard", open_dashboard),
                pystray.MenuItem("Exit", exit_app)
            )
        )
        return icon
    except Exception as e:
        logger.error(f"Error creating system tray icon: {str(e)}")
        raise

def main():
    logger.info("=== DS Monitoring App Installer ===")
    
    try:
        # Create required folders
        logger.info("Creating required folders...")
        create_required_folders()
        
        # Check .env file
        logger.info("Checking environment configuration...")
        check_env_file()
        
        # Initialize database
        logger.info("Initializing database...")
        initialize_database()
        
        # Start Flask app in a separate thread
        logger.info("Starting application server...")
        flask_thread = threading.Thread(target=run_flask_app, daemon=True)
        flask_thread.start()
        
        # Wait for server to start
        time.sleep(2)
        
        # Create and run tray icon
        logger.info("Starting system tray icon...")
        icon = create_tray_icon()
        icon.run()
        
    except Exception as e:
        logger.error(f"Application startup failed: {str(e)}")
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == '__main__':
    main() 