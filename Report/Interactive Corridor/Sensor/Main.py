from Phidget22.Devices.VoltageInput import VoltageInput
import pygame
import random
import time
import sys
from pythonosc.udp_client import SimpleUDPClient

PI_A_IP = "192.168.254.185"
PI_A_PORT = 5679

PI_B_IP = "192.168.254.38"
PI_B_PORT = 5678

PI_C_IP = "192.168.254.12"
PI_C_PORT = 5677

clientA = SimpleUDPClient(PI_A_IP, PI_A_PORT)
clientB = SimpleUDPClient(PI_B_IP, PI_B_PORT)
clientC = SimpleUDPClient(PI_C_IP, PI_C_PORT)


def run_python_1():
    clientA.send_message("/run/python1", 1)
    clientB.send_message("/run/python1", 1)
    clientC.send_message("/run/python1", 1)
    print("Sent: /run/python1")


def run_python_2():
    clientA.send_message("/run/python2", 1)
    clientB.send_message("/run/python2", 1)
    clientC.send_message("/run/python2", 1)
    print("Sent: /run/python2")


def run_python_3():
    clientA.send_message("/run/python3", 1)
    clientB.send_message("/run/python3", 1)
    clientC.send_message("/run/python3", 1)
    print("Sent: /run/python3")


def run_python_4():
    clientA.send_message("/run/python4", 1)
    clientB.send_message("/run/python4", 1)
    clientC.send_message("/run/python4", 1)
    print("Sent: /run/python4")


def run_python_5():
    clientA.send_message("/run/python5", 1)
    clientB.send_message("/run/python5", 1)
    clientC.send_message("/run/python5", 1)
    print("Sent: /run/python5")


SIGNIFICANT_CHANGE = 0.05
COOLDOWN_TIME = 100
AUDIO_DELAY = 1.0

SENSOR_CONFIG = [
    {"serial": 85428, "channels": [0, 1, 2, 3, 5, 6]},
    {"serial": 85516, "channels": [0, 1, 2, 3]}
]


def legendary_event():
    print("LEGENDARY event triggered!")
    run_python_5()


def epic_event():
    print("EPIC event triggered!")
    run_python_4()


def rare_event():
    print("RARE event triggered!")
    run_python_3()


def uncommon_event():
    print("UNCOMMON event triggered!")
    run_python_2()


def common_event():
    print("COMMON event triggered!")
    run_python_1()


EVENTS = [
    (0.05, legendary_event),
    (0.10, epic_event),
    (0.15, rare_event),
    (0.30, uncommon_event),
    (0.40, common_event),
]

LEGENDARY_AUDIO = "/home/pi/EGL314JW/Legendary.wav"
EPIC_AUDIO = "/home/pi/EGL314JW/Epic.wav"
RARE_AUDIO = "/home/pi/EGL314JW/Rare.wav"
UNCOMMON_AUDIO = "/home/pi/EGL314JW/Uncommon.wav"
COMMON_AUDIO = "/home/pi/EGL314JW/Common.wav"

pygame.mixer.init(frequency=44100, size=-16, channels=2, buffer=1024)

sound_legendary = pygame.mixer.Sound(LEGENDARY_AUDIO)
sound_epic = pygame.mixer.Sound(EPIC_AUDIO)
sound_rare = pygame.mixer.Sound(RARE_AUDIO)
sound_uncommon = pygame.mixer.Sound(UNCOMMON_AUDIO)
sound_common = pygame.mixer.Sound(COMMON_AUDIO)

ALL_SOUNDS = [
    sound_legendary,
    sound_epic,
    sound_rare,
    sound_uncommon,
    sound_common,
]

AUDIO_CHANNEL = pygame.mixer.Channel(0)


def get_sound_for_event(fn):
    if fn is legendary_event:
        return sound_legendary
    elif fn is epic_event:
        return sound_epic
    elif fn is rare_event:
        return sound_rare
    elif fn is uncommon_event:
        return sound_uncommon
    else:
        return sound_common


sensors = []
last_voltages = []
last_trigger_time = 0.0

pending_sound = None
pending_sound_time = 0.0


def init_sensors():
    global sensors, last_voltages
    sensors = []
    last_voltages = []

    for kit in SENSOR_CONFIG:
        for ch in kit["channels"]:
            vin = VoltageInput()
            vin.setDeviceSerialNumber(kit["serial"])
            vin.setChannel(ch)
            vin.openWaitForAttachment(2000)

            try:
                initial_v = vin.getVoltage()
            except Exception:
                initial_v = 0.0

            sensors.append(vin)
            last_voltages.append(initial_v)


def cleanup():
    AUDIO_CHANNEL.stop()
    for s in sensors:
        try:
            s.close()
        except Exception:
            pass


def weighted_random_event():
    global pending_sound, pending_sound_time

    r = random.random()
    cumulative = 0.0
    chosen_fn = None

    for weight, fn in EVENTS:
        cumulative += weight
        if r <= cumulative:
            chosen_fn = fn
            break

    if chosen_fn is None:
        chosen_fn = EVENTS[-1][1]

    print(f"Selected event: {chosen_fn.__name__}")

    chosen_sound = get_sound_for_event(chosen_fn)

    chosen_fn()

    pending_sound = chosen_sound
    pending_sound_time = time.time() + AUDIO_DELAY


def main():
    global last_trigger_time, pending_sound, pending_sound_time

    print("Pi 1: Tiered Event System (Legendary / Epic / Rare / Uncommon / Common)")
    print(f"Audio delay: {AUDIO_DELAY} seconds")
    init_sensors()

    try:
        while True:
            now = time.time()

            if pending_sound is not None and now >= pending_sound_time:
                AUDIO_CHANNEL.stop()
                AUDIO_CHANNEL.play(pending_sound)
                pending_sound = None

            for idx, sensor in enumerate(sensors):
                try:
                    v = sensor.getVoltage()
                except Exception:
                    continue

                delta = v - last_voltages[idx]
                last_voltages[idx] = v

                if delta >= SIGNIFICANT_CHANGE and (now - last_trigger_time) > COOLDOWN_TIME:
                    weighted_random_event()
                    last_trigger_time = time.time()

            time.sleep(0.05)

    except KeyboardInterrupt:
        print("\nExiting...")
        cleanup()
        sys.exit(0)


if __name__ == "__main__":
    main()
