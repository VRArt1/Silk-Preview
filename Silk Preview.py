import subprocess
import sys
import importlib
import shutil
import os
from pathlib import Path
import platform
import urllib.request
import zipfile

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
# Check if a command exists
# ----------------------------
def command_exists(cmd):
    return shutil.which(cmd) is not None


# ----------------------------
# Install FFmpeg automatically
# ----------------------------
def ensure_ffmpeg():
    ffmpeg_path = shutil.which("ffmpeg")
    if ffmpeg_path:
        print(f"FFmpeg found at {ffmpeg_path}")
        return ffmpeg_path

    system = platform.system()
    print("FFmpeg not found on system.")

    # ----------------------------
    # WINDOWS
    # ----------------------------
    if system == "Windows":
        print("Downloading static FFmpeg for Windows...")

        ffmpeg_url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
        ffmpeg_zip = Path("ffmpeg.zip")
        ffmpeg_dir = Path("ffmpeg_bin")

        ffmpeg_dir.mkdir(exist_ok=True)

        urllib.request.urlretrieve(ffmpeg_url, ffmpeg_zip)

        with zipfile.ZipFile(ffmpeg_zip, 'r') as zip_ref:
            zip_ref.extractall(ffmpeg_dir)

        ffmpeg_bin = next(ffmpeg_dir.glob("**/ffmpeg.exe"), None)

        if ffmpeg_bin:
            os.environ["PATH"] = str(ffmpeg_bin.parent) + os.pathsep + os.environ.get("PATH", "")
            print(f"FFmpeg ready at {ffmpeg_bin}")
            ffmpeg_zip.unlink()
            return str(ffmpeg_bin)
        else:
            print("[ERROR] Could not locate ffmpeg.exe after extraction.")
            return None

    # ----------------------------
    # MACOS
    # ----------------------------
    elif system == "Darwin":
        print("macOS detected.")

        if command_exists("brew"):
            print("Installing FFmpeg via Homebrew...")
            subprocess.call(["brew", "install", "ffmpeg"])
        else:
            print("Homebrew not found.")
            print("Install Homebrew first: https://brew.sh")
            print("Then run: brew install ffmpeg")

        return shutil.which("ffmpeg")

    # ----------------------------
    # LINUX
    # ----------------------------
    else:
        print("Linux detected.")

        if command_exists("apt"):
            print("Installing FFmpeg using apt...")
            subprocess.call(["sudo", "apt", "install", "-y", "ffmpeg"])

        elif command_exists("dnf"):
            print("Installing FFmpeg using dnf...")
            subprocess.call(["sudo", "dnf", "install", "-y", "ffmpeg"])

        elif command_exists("pacman"):
            print("Installing FFmpeg using pacman...")
            subprocess.call(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"])

        elif command_exists("brew"):
            print("Installing FFmpeg via Linuxbrew...")
            subprocess.call(["brew", "install", "ffmpeg"])

        else:
            print("Could not determine package manager.")
            print("Please install FFmpeg manually.")

        return shutil.which("ffmpeg")


# ----------------------------
# Run dependency checks
# ----------------------------
check_and_install_packages(required_packages)
ensure_ffmpeg()


# ----------------------------
# Launch the main app
# ----------------------------
app_file = Path(__file__).parent / "app.py"

if not app_file.exists():
    print("[ERROR] app.py not found.")
    sys.exit(1)

print("Launching the application...")
subprocess.run([sys.executable, str(app_file)])