import sys
import importlib.util
import shutil
from pathlib import Path

REQUIRED_PACKAGES = ["Pillow", "av", "tkinterdnd2"]

def check_dependencies():
    missing = []
    for pkg in REQUIRED_PACKAGES:
        if importlib.util.find_spec(pkg) is None:
            missing.append(pkg)
    
    if shutil.which("ffmpeg") is None:
        missing.append("FFmpeg")
    
    return missing

def main():
    missing = check_dependencies()
    
    if not missing:
        print("All dependencies found. Launching application...")
        subprocess = __import__("subprocess")
        app_file = Path(__file__).parent / "app.py"
        if app_file.exists():
            subprocess.run([sys.executable, str(app_file)])
        else:
            print("[ERROR] app.py not found.")
            sys.exit(1)
        return
    
    print("The following dependencies are missing:")
    for pkg in missing:
        print(f"  - {pkg}")
    print()
    
    response = input("Would you like to install missing dependencies? (y/n): ").strip().lower()
    
    if response in ("y", "yes"):
        subprocess = __import__("subprocess")
        install_script = Path(__file__).parent / "install_dependencies.py"
        if install_script.exists():
            result = subprocess.run([sys.executable, str(install_script)])
            sys.exit(result.returncode)
        else:
            print("[ERROR] install_dependencies.py not found.")
            sys.exit(1)
    else:
        print("ERROR: Dependencies must be installed before the software can run.")
        print("Run 'python install_dependencies.py' to install dependencies.")
        sys.exit(1)

if __name__ == "__main__":
    main()
