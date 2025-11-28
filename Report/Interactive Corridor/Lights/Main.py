from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
import subprocess
import os
import sys

print("OSC SERVER PYTHON:", sys.executable)

ENV_PYTHON = "/home/pi/EGL314/bin/python"
BASE_DIR = "/home/pi/EGL314"

child_procs = {}


def run_script(script_name):
    script_path = os.path.join(BASE_DIR, script_name)
    print(f"[OSC] Launching: {script_path}")

    old = child_procs.get(script_name)
    if old and old.poll() is None:
        print(f"[OSC] Terminating previous instance of {script_name}...")
        try:
            old.terminate()
        except Exception as e:
            print(f"[OSC] Error terminating old process: {e}")

    proc = subprocess.Popen(
        [ENV_PYTHON, script_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    child_procs[script_name] = proc


def run_python_1(addr, *args):
    run_script("common.py")

def run_python_2(addr, *args):
    run_script("Uncommon.py")

def run_python_3(addr, *args):
    run_script("Rare.py")

def run_python_4(addr, *args):
    run_script("Epic.py")

def run_python_5(addr, *args):
    run_script("Legendary.py")


dispatcher = Dispatcher()
dispatcher.map("/run/python1", run_python_1)
dispatcher.map("/run/python2", run_python_2)
dispatcher.map("/run/python3", run_python_3)
dispatcher.map("/run/python4", run_python_4)
dispatcher.map("/run/python5", run_python_5)


def cleanup_children():
    print("[OSC] Cleaning up children...")
    for name, proc in child_procs.items():
        if proc.poll() is None:
            print(f"[OSC]  - Terminating {name} (pid {proc.pid})...")
            try:
                proc.terminate()
            except Exception as e:
                print(f"[OSC]  ! Error terminating {name}: {e}")


if __name__ == "__main__":
    print("OSC Slave listening on port 5678...")
    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", 5678), dispatcher)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[OSC] Ctrl+C received, shutting down OSC server...")
    finally:
        cleanup_children()
        print("[OSC] Shutdown complete. Bye.")
        sys.exit(0)

