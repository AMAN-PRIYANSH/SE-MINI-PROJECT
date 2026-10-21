"""Start the whole system on one host (SADS 2.5): Web Server + ML/DL/QML services.

Usage:
    python run_all.py            # uses CCFD_API_KEY if set, otherwise generates one
    python run_all.py --only ml  # start a subset (server, ml, dl, qml)

Each component runs as its own OS process, so stopping one service does not
stop the others (SRS NFR-06). Press Ctrl+C to stop everything.
"""
import argparse
import importlib.util
import os
import secrets
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent

COMPONENTS = {
    "ml": "services.ml.server",
    "dl": "services.dl.server",
    "qml": "services.qml.server",
    "server": "server.app",
}


def module_exists(name):
    try:
        return importlib.util.find_spec(name) is not None
    except ModuleNotFoundError:
        return False


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--only", nargs="*", choices=list(COMPONENTS), default=list(COMPONENTS))
    args = parser.parse_args()

    env = os.environ.copy()
    if not env.get("CCFD_API_KEY"):
        env["CCFD_API_KEY"] = secrets.token_urlsafe(24)
        print(f"Generated API key for this session: {env['CCFD_API_KEY']}")
        print("(set CCFD_API_KEY yourself to keep the same key between runs)\n")
    env.setdefault("PYTHONPATH", str(ROOT))

    sys.path.insert(0, str(ROOT))
    procs = []
    for name in args.only:
        module = COMPONENTS[name]
        if not module_exists(module):
            print(f"[skip] {name}: {module} is not implemented yet")
            continue
        procs.append((name, subprocess.Popen([sys.executable, "-m", module], cwd=ROOT, env=env)))
        print(f"[start] {name} ({module})")

    if not procs:
        print("Nothing to start.")
        return
    port = env.get("CCFD_PORT", "5000")
    print(f"\nOpen http://127.0.0.1:{port}/ in your browser. Ctrl+C stops everything.")

    try:
        while True:
            for name, p in procs:
                if p.poll() is not None:
                    print(f"[exit] {name} stopped with code {p.returncode}")
                    procs.remove((name, p))
            if not procs:
                break
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for _, p in procs:
            if p.poll() is None:
                if os.name == "nt":
                    p.terminate()
                else:
                    p.send_signal(signal.SIGINT)
        for _, p in procs:
            try:
                p.wait(timeout=10)
            except subprocess.TimeoutExpired:
                p.kill()


if __name__ == "__main__":
    main()
