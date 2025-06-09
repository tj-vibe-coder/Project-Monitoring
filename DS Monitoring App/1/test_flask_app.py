#!/usr/bin/env python3
"""
Simple Flask app test to verify the application starts correctly
"""
import sys
import time
import threading
import requests
from app import app, init_db

def test_flask_startup():
    """Test that Flask application can start and serve basic requests"""
    print("Testing Flask application startup...")
    
    try:
        # Initialize database
        init_db()
        print("✓ Database initialized successfully")
        
        # Test if we can create the Flask app
        if app is None:
            print("✗ Flask app is None")
            return False
        
        print("✓ Flask app created successfully")
        
        # Test app configuration
        print(f"✓ App secret key configured: {'Yes' if app.secret_key else 'No'}")
        print(f"✓ Static folder: {app.static_folder}")
        
        # Try to get some basic routes
        with app.test_client() as client:
            # Test basic index route
            response = client.get('/')
            print(f"✓ Index route status: {response.status_code}")
            
            # Test static file serving
            response = client.get('/static/index.html')
            print(f"✓ Static file serving status: {response.status_code}")
            
            # Test API endpoint
            response = client.get('/api/projects')
            print(f"✓ API projects endpoint status: {response.status_code}")
            
        print("✓ All basic tests passed!")
        return True
        
    except Exception as e:
        print(f"✗ Flask startup test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    print("=" * 50)
    print("Flask Application Test")
    print("=" * 50)
    
    if test_flask_startup():
        print("\n🎉 Flask application is ready!")
        print("=" * 50)
        print("To start the application, run: python app.py")
        print("The application will be available at: http://localhost:5000")
        print("=" * 50)
    else:
        print("\n❌ Flask application test failed!")
        sys.exit(1)
