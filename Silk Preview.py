import subprocess
import sys
import importlib
import shutil
import os
from pathlib import Path
import platform
import urllib.request
import zipfile
import tarfile

# ----------------------------
# List of required Python packages
# ----------------------------
required_packages = [
    "Pillow",
    "av",
]

# ----------------------------
# Helper to install Python packages
# ----------------------------
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
            install_package(pkg)

# ----------------------------
# Check for FFmpeg (required by PyAV)
# ----------------------------
def ensure_ffmpeg():
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"FFmpeg found at {ffmpeg_path}")
        return ffmpeg_path

    system = platform.system()
    print("FFmpeg not found on system.")

    if system == "Windows":
        print("Downloading static FFmpeg for Windows...")
        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        ffmpeg_zip = Path("ffmpeg.zip")
        ffmpeg_dir = Path("ffmpeg_bin")
        if not ffmpeg_dir.exists():
            ffmpeg_dir.mkdir(exist_ok=True)
        urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip)
        with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)
        ffmpeg_bin = next(ffmpeg_dir.glob("**/ffmpeg.exe"), None)
        if ffmpeg_bin:
            os.environ["PATH"] = str(ffmpeg_bin.parent) + os.pathsep + os.environ.get("PATH", "")
            print(f"FFmpeg ready at {ffmpeg_bin}")
            ffmpeg_zip.unlink()  # remove zip
            return str(ffmpeg_bin)
        else:
            print("[ERROR] Could not locate ffmpeg.exe after extraction.")
            return None
    elif system == "Darwin":
        print("Please install FFmpeg on macOS using Homebrew: brew install ffmpeg")
        return None
    else:  # Linux
        print("Please install FFmpeg using your package manager, e.g., 'sudo apt install ffmpeg'")
        return None

# ----------------------------
# Run everything
# ----------------------------
check_and_install_packages(required_packages)
ensure_ffmpeg()

# Launch app
app_file = Path(__file__).parent / "app.py"
if not app_file.exists():
    print("[ERROR] app.py not found.")
    sys.exit(1)

print("Launching the application...")
subprocess.run([sys.executable, str(app_file)])