from pythonosc import udp_client, dispatcher as osc_dispatcher, osc_server
import time, random, threading, sys, atexit, os
import RPi.GPIO as GPIO

SENSORS = [17, 27, 22]
LABELS = {17: "Right", 27: "Left", 22: "Middle"}
WAIT_HOLD_TIME = 5.0

MA3_IP, MA3_PORT = "192.168.254.231", 5000
REAPER_IP, REAPER_PORT = "192.168.254.12", 8000
LISTEN_PORT = 2010

REAPER_PLAY = "/action/1007"
REAPER_PAUSE = "/action/1008"
REAPER_M1 = "/action/40161"
REAPER_R1INTRO = "/action/40164"
REAPER_R1GAME = "/action/40166"
REAPER_EL = "/action/40168"
REAPER_EM = "/action/40160"
REAPER_EMR = "/action/41258"
REAPER_R2INTRO = "/action/41260"
REAPER_R2GAME = "/action/41262"
REAPER_AE = "/action/41268"
REAPER_WIN = "/action/41254"
REAPER_OUTRO = "/action/41269"
REAPER_R2TR = "/action/41263"
REAPER_R2TM = "/action/41262"
REAPER_R2TL = "/action/41252"
GMA3_ADDR = "/gma3/cmd"

state_lock = threading.Lock()
flags = {k: False for k in ["act1", "act2", "act3", "act4", "act5", "act6", "act6_5", "act7", "act8", "restart"]}
last_sit_times = {p: 0.0 for p in SENSORS}
stop_threads = False
round1_eliminated_pin = None
round2_target_pin = None
round2_correct = False
winner_pin = None
last_time_s = None
SEEK_BACK_IGNORE_WINDOW = 5.0

random.seed(time.time())


def send_message(ip, port, addr, msg):
    try:
        c = udp_client.SimpleUDPClient(ip, port)
        c.send_message(addr, msg)
        print(f"[OSC {ip}:{port}] {addr} -> {msg}")
    except Exception as e:
        print(f"[ERROR] {e}")


def is_sensor_pressed(pin):
    return GPIO.input(pin) == GPIO.LOW


def all_sensors_pressed(pins):
    return all(is_sensor_pressed(p) for p in pins)


def seconds_from_timestr(s):
    s = str(s).strip().replace("'", "").replace('"', "")
    try:
        parts = s.split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + float(parts[1])
        if len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + float(parts[2])
    except Exception:
        return None
    return None


def map_elimination_sequence(pin):
    return {27: 4, 22: 5, 17: 6}[pin]


def crossed_edge(prev_s, now_s, target_s, max_forward_jump=2.0):
    if prev_s is None or now_s is None or target_s is None:
        return False
    step = now_s - prev_s
    if step <= 0 or step > max_forward_jump:
        return False
    return prev_s < target_s <= now_s


def startup_sequences():
    print("ACT 1 Startup/reset")
    print("[GPIO] Setting startup pin HIGH")
    time.sleep(1.0)
    print("[GPIO] Setting startup pin LOW")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 16")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_M1, 1.0)
    for s in (5, 6, 8):
        send_message(MA3_IP, MA3_PORT, GMA3_ADDR, f"Go+ Sequence {s}")


def sequence_2_intro():
    print("ACT 2 Game Intro")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_R1INTRO, 1.0)
    for s in (5, 6, 8):
        send_message(MA3_IP, MA3_PORT, GMA3_ADDR, f"Off Sequence {s}")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 7")


def sequence_3_round1():
    print("ACT 3 Round 1 Start")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 7")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 8")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_R1GAME, 1.0)
    pause_time = random.uniform(5, 30)
    print(f"[Round 1] pause after {pause_time:.1f}s")
    paused = threading.Event()
    early = {}

    def pause():
        if not paused.is_set():
            send_message(REAPER_IP, REAPER_PORT, REAPER_PAUSE, 1.0)
            print("Music paused")
            paused.set()

    threading.Timer(pause_time, pause).start()
    start = time.time()
    while not paused.is_set():
        for p in SENSORS:
            if is_sensor_pressed(p) and p not in early:
                early[p] = time.time() - start
                print(f"[Round 1] early sit {LABELS[p]} {early[p]:.2f}s")
        if len(early) == len(SENSORS):
            elim = min(early, key=early.get)
            print(f"All early, {LABELS[elim]} eliminated")
            pause()
            return elim
        time.sleep(0.05)
    if early:
        elim = min(early, key=early.get)
        print(f"Early sitter {LABELS[elim]} eliminated at pause")
        return elim
    for p in SENSORS:
        last_sit_times[p] = 0
    while not all_sensors_pressed(SENSORS):
        for p in SENSORS:
            if is_sensor_pressed(p) and not last_sit_times[p]:
                last_sit_times[p] = time.time()
                print(f"{LABELS[p]} sat post-pause")
        time.sleep(0.05)
    elim = max(SENSORS, key=lambda p: last_sit_times[p])
    print(f"[Round 1] eliminated {LABELS[elim]}")
    return elim


def seq_elimination(pin):
    seq = map_elimination_sequence(pin)
    if seq == 4:
        print("ACT 4 Left Eliminated")
        send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 10")
        send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
        send_message(REAPER_IP, REAPER_PORT, REAPER_EM, 1.0)
    elif seq == 5:
        print("ACT 4 Middle Eliminated")
        send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 11")
        send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
        send_message(REAPER_IP, REAPER_PORT, REAPER_EMR, 1.0)
    elif seq == 6:
        print("ACT 4 Right Eliminated")
        send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 12")
        send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
        send_message(REAPER_IP, REAPER_PORT, REAPER_EL, 1.0)
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 9")


def sequence_7_intro_round2():
    print("ACT 5 Round 2 Intro")
    for s in (12, 10, 11, 9):
        send_message(MA3_IP, MA3_PORT, GMA3_ADDR, f"Off Sequence {s}")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_R2INTRO, 1.0)
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 18")


def wait_for_two_pressed():
    while True:
        pressed = {p for p in SENSORS if is_sensor_pressed(p)}
        if len(pressed) >= 2:
            return pressed
        time.sleep(0.02)


def sequence_8_round2():
    print("ACT 6 Round 2 Start")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 18")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 19")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_R2GAME, 1.0)
    target = random.choice(SENSORS)
    print(f"[Round 2] target {LABELS[target]}")
    clue = {17: REAPER_R2TR, 22: REAPER_R2TM, 27: REAPER_R2TL}[target]
    send_message(REAPER_IP, REAPER_PORT, clue, 1.0)
    pressed = wait_for_two_pressed()
    print(f"[Round 2] pressed {', '.join(LABELS[p] for p in pressed)}")
    correct = target in pressed
    if not correct:
        sequence_12_loser()
    return pressed, target, correct


def sequence_12_loser():
    print("ACT 6.5 Loser sequence")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 19")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 17")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_AE, 1.0)
    with state_lock:
        flags["act6_5"] = True


def sequence_13_victory(pin):
    print(f"ACT 7 Victory {LABELS[pin]}")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_WIN, 1.0)
    seq = {27: 13, 17: 14, 22: 15}[pin]
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, f"Go+ Sequence {seq}")


def sequence_outro():
    print("ACT 8 Outro")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_OUTRO, 1.0)
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 16")


GPIO.setmode(GPIO.BCM)
for p in SENSORS:
    GPIO.setup(p, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def bg_inactivity_watchdog():
    IDLE_LIMIT = 90.0
    last_active = time.time()
    print("Inactivity watchdog armed (1 min 30 s limit)")
    while True:
        if any(is_sensor_pressed(p) for p in SENSORS):
            last_active = time.time()
        if time.time() - last_active > IDLE_LIMIT:
            print("Inactivity detected (>90s) restarting system")
            GPIO.cleanup()
            time.sleep(1)
            os.execv(sys.executable, ['python3'] + sys.argv)
        time.sleep(0.5)


def bg_wait_for_act2():
    while not stop_threads:
        with state_lock:
            done = flags["act2"]
        if not done and all_sensors_pressed(SENSORS):
            t0 = time.time()
            while all_sensors_pressed(SENSORS):
                if time.time() - t0 >= WAIT_HOLD_TIME:
                    print("All seated Act 2")
                    sequence_2_intro()
                    with state_lock:
                        flags["act2"] = True
                    threading.Thread(target=bg_inactivity_watchdog, daemon=True).start()
                    break
                time.sleep(0.05)
        time.sleep(0.1)


def trigger_act4(pin):
    def _():
        time.sleep(3)
        seq_elimination(pin)
        with state_lock:
            flags["act4"] = True
    threading.Thread(target=_, daemon=True).start()


class Round1Controller:
    def __init__(self):
        self.started = False
        self.lock = threading.Lock()

    def try_start(self):
        with self.lock:
            if self.started:
                return
            self.started = True
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        global round1_eliminated_pin
        elim = sequence_3_round1()
        round1_eliminated_pin = elim
        trigger_act4(elim)


class Round2Controller:
    def __init__(self):
        self.started = False
        self.lock = threading.Lock()

    def reset(self):
        with self.lock:
            self.started = False

    def try_start(self):
        with self.lock:
            if self.started:
                return
            self.started = True
        threading.Thread(target=self.run, daemon=True).start()

    def run(self):
        global round2_target_pin, round2_correct, winner_pin
        pressed, target, ok = sequence_8_round2()
        round2_target_pin = target
        round2_correct = ok
        if ok:
            def _():
                time.sleep(3)
                with state_lock:
                    if not flags["act7"]:
                        flags["act7"] = True
                winner_pin = target
                sequence_13_victory(target)
            threading.Thread(target=_, daemon=True).start()
        else:
            print("Round 2 wrong, no Act 7")


round1_ctrl = Round1Controller()
round2_ctrl = Round2Controller()


def process_playhead_time(now_s):
    global last_time_s
    if now_s is None:
        return

    back_seek = last_time_s is not None and now_s + SEEK_BACK_IGNORE_WINDOW < last_time_s
    if back_seek:
        last_time_s = now_s
        return

    ACT3_T = 3 * 60 + 49
    ACT5_Ts = [5 * 60 + 56, 6 * 60 + 34, 6 * 60 + 58]
    ACT6_Ts = [7 * 60 + 43]
    ACT6_RETURN_T = 8 * 60 + 19
    ACT7_END_T = 12 * 60 + 49
    ACT7_BUFFER = 2.0
    RESTART_T = 8 * 60 + 39
    prev = last_time_s

    with state_lock:
        if not flags["act3"] and crossed_edge(prev, now_s, ACT3_T):
            print("Cross 3:49 Act 3")
            flags["act3"] = True
    if flags["act3"]:
        round1_ctrl.try_start()

    with state_lock:
        if (not flags["act5"]) and any(crossed_edge(prev, now_s, t) for t in ACT5_Ts):
            print("Cross Act 5 Round 2 Intro")
            flags["act5"] = True
            sequence_7_intro_round2()

    with state_lock:
        if (not flags["act6"]) and any(crossed_edge(prev, now_s, t) for t in ACT6_Ts):
            print("Cross Act 6 Round 2 Start")
            flags["act6"] = True
            round2_ctrl.try_start()

    with state_lock:
        if flags.get("act6_5") and crossed_edge(prev, now_s, ACT6_RETURN_T):
            print("Act 6.5 ended Back to Act 5")
            flags["act6_5"] = False
            flags["act5"] = False
            flags["act6"] = False
            round2_ctrl.reset()
            sequence_7_intro_round2()
            flags["act5"] = True

    with state_lock:
        if flags.get("act7") and crossed_edge(prev, now_s, ACT7_END_T):
            print("Act 7 ended Act 8 (after 2s buffer)")
            threading.Timer(ACT7_BUFFER, sequence_outro).start()
            flags["act8"] = True

    with state_lock:
        if flags.get("act8") and not flags.get("restart") and crossed_edge(prev, now_s, RESTART_T):
            flags["restart"] = True
            print("Full system restart triggered at 8:39")
            GPIO.cleanup()
            time.sleep(1)
            os.execv(sys.executable, ['python3'] + sys.argv)

    last_time_s = now_s


def osc_handler(address, *args):
    if address == "/time/str" and args:
        t = seconds_from_timestr(args[0])
        if t is not None:
            process_playhead_time(t)


def start_server():
    ip = "0.0.0.0"
    print(f"Listening for OSC on {ip}:{LISTEN_PORT}")
    disp = osc_dispatcher.Dispatcher()
    disp.map("/*", osc_handler)
    server = osc_server.ThreadingOSCUDPServer((ip, LISTEN_PORT), disp)
    server.serve_forever()


def main():
    startup_sequences()
    with state_lock:
        flags["act1"] = True
    threading.Thread(target=bg_wait_for_act2, daemon=True).start()
    threading.Thread(target=start_server, daemon=True).start()
    atexit.register(GPIO.cleanup)
    print("Ready Headless controller running")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        GPIO.cleanup()
        print("Exit")


if __name__ == "__main__":
    main()
