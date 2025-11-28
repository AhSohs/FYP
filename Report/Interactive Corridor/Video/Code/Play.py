import subprocess
import time
from pythonosc import dispatcher, osc_server

VIDEO_PATH = "/home/pi/Videos/Dog.mp4"
BLACK_SCREEN = "/home/pi/Videos/Pure black.webp"
OSC_IP = "192.168.254.185"
OSC_PORT = 2007


def play_video(video_path=VIDEO_PATH):
    print("Playing video...")
    subprocess.Popen(["cvlc", "--fullscreen", "--no-video-title-show", "--play-and-exit", video_path])


def show_black_screen():
    print("Showing black screen...")
    subprocess.Popen(["feh", "--fullscreen", "--hide-pointer", "--zoom", "fill", BLACK_SCREEN])


def stop_video():
    print("Stopping video...")
    subprocess.call(["pkill", "vlc"])
    time.sleep(1)
    show_black_screen()


def trigger_video(_addr, *args):
    print("OSC trigger received. Running video sequence.")
    stop_video()
    play_video()


disp = dispatcher.Dispatcher()
disp.map("/sensor", trigger_video)

server = osc_server.ThreadingOSCUDPServer((OSC_IP, OSC_PORT), disp)
print(f"OSC server active on {OSC_IP}:{OSC_PORT} (Ctrl + C to quit)")

try:
    show_black_screen()
    server.serve_forever()
except KeyboardInterrupt:
    print("\nCleaning up before exit.")
    stop_video()
