import sys
import os

# Add the project root directory to python path if needed
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

from ui.app import App

def main():
    try:
        app = App()
        app.mainloop()
    except Exception as e:
        print(f"Error starting application: {e}")
        input("Press Enter to exit...")

if __name__ == "__main__":
    main()
