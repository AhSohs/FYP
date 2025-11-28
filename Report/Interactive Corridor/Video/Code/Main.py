from pythonosc.dispatcher import Dispatcher
from pythonosc import osc_server
import subprocess
import os
import sys

print("OSC SERVER PYTHON:", sys.executable)

SYSTEM_PYTHON = "/usr/bin/python3"
BASE_DIR = "/home/pi/TV"


def run_script(script_name):
    script_path = os.path.join(BASE_DIR, script_name)
    print(f"[OSC] Launching: {script_path}")
    subprocess.Popen(
        [SYSTEM_PYTHON, script_path],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )


def run_python_1(addr, *args):
    run_script("Common.py")


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

if __name__ == "__main__":
    PORT = 5679
    print(f"OSC Slave listening on port {PORT}...")
    server = osc_server.ThreadingOSCUDPServer(("0.0.0.0", PORT), dispatcher)
    server.serve_forever()
