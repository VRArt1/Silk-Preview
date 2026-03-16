import subprocess
import sys
import importlib.util
import shutil
import os
from pathlib import Path
import platform
import urllib.request
import zipfile

REQUIRED_PACKAGES = ["Pillow", "av", "tkinterdnd2", "opencv-python"]

def install_packages():
    for pkg in REQUIRED_PACKAGES:
        if importlib.util.find_spec(pkg) is None:
            print(f"Package '{pkg}' not found. Installing...")
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", pkg])
            except subprocess.CalledProcessError:
                print(f"[WARNING] Failed to install '{pkg}'. Video wallpapers will use fallback.")
    return True

def command_exists(cmd):
    return shutil.which(cmd) is not None

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

    elif system == "Darwin":
        print("macOS detected.")
        if command_exists("brew"):
            print("Installing FFmpeg via Homebrew...")
            subprocess.call(["brew", "install", "ffmpeg"])
        else:
            print("Homebrew not found. Install Homebrew first: https://brew.sh")
            print("Then run: brew install ffmpeg")
        return shutil.which("ffmpeg")

    else:
        print("Linux detected.")
        if command_exists("apt"):
            subprocess.call(["sudo", "apt", "install", "-y", "ffmpeg"])
        elif command_exists("dnf"):
            subprocess.call(["sudo", "dnf", "install", "-y", "ffmpeg"])
        elif command_exists("pacman"):
            subprocess.call(["sudo", "pacman", "-S", "--noconfirm", "ffmpeg"])
        elif command_exists("brew"):
            subprocess.call(["brew", "install", "ffmpeg"])
        else:
            print("Could not determine package manager.")
            print("Please install FFmpeg manually.")
        return shutil.which("ffmpeg")

def run():
    if not install_packages():
        return False
    if not ensure_ffmpeg():
        return False
    return True

if __name__ == "__main__":
    if run():
        app_file = Path(__file__).parent / "app.py"
        if app_file.exists():
            print("Launching the application...")
            subprocess.run([sys.executable, str(app_file)])
        else:
            print("[ERROR] app.py not found.")
            sys.exit(1)
    else:
        sys.exit(1)
