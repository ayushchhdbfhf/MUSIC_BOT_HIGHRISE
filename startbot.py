import os
import sys
import subprocess
from pathlib import Path

def run(cmd):
    return subprocess.run(cmd, check=True)

def main():
    base = Path(__file__).resolve().parent
    os.chdir(base)
    venv_dir = base / ".venv"
    if not venv_dir.exists():
        run([sys.executable, "-m", "venv", str(venv_dir)])
    venv_python = venv_dir / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    run([str(venv_python), "-m", "pip", "install", "--upgrade", "pip", "wheel", "setuptools"])
    req = base / "requirements.txt"
    if req.exists():
        run([str(venv_python), "-m", "pip", "install", "-r", str(req)])
    backoff = 3
    while True:
        try:
            result = subprocess.run([str(venv_python), str(base / "main.py")])
            if result.returncode == 0:
                break
        except Exception:
            pass
        try:
            import time
            time.sleep(backoff)
            backoff = min(backoff * 2, 60)
        except Exception:
            pass

if __name__ == "__main__":
    main()
