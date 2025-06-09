# DS Monitoring App

A Flask-based monitoring application with system tray integration and PostgreSQL database support.

## Prerequisites

- Python 3.8 or higher
- Windows OS
- Internet connection (for database access)

## Installation

1. Extract all files to a directory of your choice
2. Double-click `install.bat`
3. Follow the on-screen instructions
4. The installer will:
   - Create a virtual environment
   - Install required dependencies
   - Set up environment variables
   - Create desktop and start menu shortcuts

## Running the Application

You can start the application in any of these ways:
1. Use the desktop shortcut "DS Monitoring"
2. Use the start menu shortcut
3. Run `install.bat` again and choose to start the application

## Files Included

Essential files:
- `main.py` - Main application entry point
- `app.py` - Flask application with routes and logic
- `config.py` - Configuration settings
- `models.py` - Database models
- `requirements.txt` - Python package dependencies
- `install.bat` - Installation script
- `icon.png` - Application icon
- `.env` - Environment variables (created during installation)

Static files:
- `static/` - Directory containing web interface files
  - HTML templates
  - CSS styles
  - JavaScript files

## Features

- Project monitoring and tracking
- Material Request Form (MRF) management
- Forecast tracking
- System tray integration
- Web-based dashboard
- Role-based access control

## Database

The application uses Railway PostgreSQL for data storage. Connection details are automatically configured during installation.

## Troubleshooting

1. If the application doesn't start:
   - Check if Python is installed correctly
   - Verify internet connection
   - Check logs in the `logs` directory

2. If the database connection fails:
   - Verify internet connection
   - Check `.env` file exists with correct credentials

## Support

For support, please contact your system administrator. 