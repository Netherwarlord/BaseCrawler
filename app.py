import sys
import os
import subprocess
import importlib.metadata

ROOT = os.path.dirname(os.path.abspath(__file__))


def _check_conda():
    env = os.environ.get("CONDA_DEFAULT_ENV", "")
    if env != "base-crawler":
        print("ERROR: BaseCrawler must run inside the 'base-crawler' conda environment.")
        print("       conda activate base-crawler")
        print("       python app.py")
        sys.exit(1)


def _ensure_requirements():
    req_file = os.path.join(ROOT, "requirements.txt")
    if not os.path.exists(req_file):
        return
    try:
        import re
        missing = []
        with open(req_file) as f:
            for line in f:
                pkg = line.strip()
                if not pkg or pkg.startswith("#"):
                    continue
                name = re.split(r"[>=<!;\[]", pkg)[0].strip()
                if not name:
                    continue
                try:
                    importlib.metadata.version(name)
                except importlib.metadata.PackageNotFoundError:
                    missing.append(pkg)
        if missing:
            print(f"Installing {len(missing)} missing package(s)…")
            subprocess.check_call([sys.executable, "-m", "pip", "install", *missing])
            print("Done.")
    except Exception as e:
        print(f"Warning: could not verify requirements: {e}")


if __name__ == "__main__":
    _check_conda()
    _ensure_requirements()
    sys.path.insert(0, ROOT)
    from Core.main import main
    main()
