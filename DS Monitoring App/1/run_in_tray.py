import threading
import webbrowser
import os
import sys
import time
from pystray import Icon, Menu, MenuItem
from PIL import Image

# Function to run Flask app in a thread
def run_flask():
    os.system(f'{sys.executable} app.py')

def open_browser():
    webbrowser.open('http://127.0.0.1:5000')

def quit_app(icon, item):
    icon.stop()
    os._exit(0)

def main():
    # Start Flask app in a background thread
    flask_thread = threading.Thread(target=run_flask, daemon=True)
    flask_thread.start()
    # Wait a bit to ensure Flask starts
    time.sleep(2)
    # Load icon image
    icon_path = os.path.join(os.path.dirname(__file__), 'static', 'favicon.ico')
    image = Image.open(icon_path)
    # Create tray icon
    menu = Menu(
        MenuItem('Open App', lambda icon, item: open_browser()),
        MenuItem('Quit', quit_app)
    )
    tray_icon = Icon('DS Monitoring App', image, 'DS Monitoring App', menu)
    tray_icon.run()

if __name__ == '__main__':
    main()
