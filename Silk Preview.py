import subprocess
import sys
import importlib
from pathlib import Path

required_packages = [
    "Pillow",  # for Image, ImageTk, etc.
    "av",      # for video frame support
]

def install_package(pkg_name: str):
    try:
        print(f"Installing '{pkg_name}'...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg_name])
    except subprocess.CalledProcessError:
        print(f"[WARNING] Failed to install '{pkg_name}'. You may need to install it manually.")
        return False
    return True

def check_and_install_packages(packages):
    for pkg in packages:
        try:
            importlib.import_module(pkg)
        except ImportError:
            print(f"Package '{pkg}' not found.")
            success = install_package(pkg)
            if not success:
                print(f"Please install '{pkg}' manually, e.g., 'pip install {pkg}'")
                # Continue, but warn user

check_and_install_packages(required_packages)

app_file = Path(__file__).parent / "app.py"

if not app_file.exists():
    print("[ERROR] app.py not found in the current directory.")
    sys.exit(1)

print("Launching the application...")
subprocess.run([sys.executable, str(app_file)])