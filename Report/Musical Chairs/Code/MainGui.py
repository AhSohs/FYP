from pythonosc import udp_client
import time, random, threading, sys, atexit
import RPi.GPIO as GPIO
import tkinter as tk
from tkinter import ttk

SENSORS = [17, 27, 22]
WAIT_HOLD_TIME = 5
LABELS = {17: "Right", 27: "Left", 22: "Middle"}

MA3_IP, MA3_PORT = "192.168.254.231", 5000
REAPER_IP, REAPER_PORT = "192.168.254.12", 8000

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

last_sit_times = {pin: 0 for pin in SENSORS}
game_running = False
stop_threads = False


def send_message(receiver_ip, receiver_port, address, message):
    try:
        client = udp_client.SimpleUDPClient(receiver_ip, receiver_port)
        client.send_message(address, message)
        print(f"Message sent to {receiver_ip}:{receiver_port} {address} -> {message}")
    except Exception as e:
        print(f"Message not sent to {receiver_ip}:{receiver_port} {address}: {e}")


def startup_sequences():
    print("Startup/reset sequences")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 16")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_M1, 1.0)
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 5")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 6")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 8")


GPIO.setmode(GPIO.BCM)
for pin in SENSORS:
    GPIO.setup(pin, GPIO.IN, pull_up_down=GPIO.PUD_UP)


def is_sensor_pressed(pin):
    return GPIO.input(pin) == GPIO.LOW


def all_sensors_pressed(lst):
    return all(is_sensor_pressed(p) for p in lst)


def sequence_2_intro():
    print("Seq 2: Game intro")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_R1INTRO, 1.0)
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 5")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 6")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 8")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 7")


def sequence_3_round1():
    print("Sequence 3: Round 1 Start (Musical Chairs mode)")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 7")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 8")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_R1GAME, 1.0)

    pause_time = random.uniform(5, 30)
    print(f"Music will randomly pause after {pause_time:.1f}s")
    paused_event = threading.Event()
    early_sits = {}
    eliminated = None

    def pause_music():
        if not paused_event.is_set():
            send_message(REAPER_IP, REAPER_PORT, REAPER_PAUSE, 1.0)
            print("Music paused (Reaper Pause)")
            paused_event.set()

    threading.Timer(pause_time, pause_music).start()
    start = time.time()

    while not paused_event.is_set():
        for p in SENSORS:
            if is_sensor_pressed(p) and p not in early_sits:
                early_sits[p] = time.time() - start
                print(f"Early sitter: {LABELS[p]} at {early_sits[p]:.2f}s")
        if len(early_sits) == len(SENSORS):
            first = min(early_sits, key=early_sits.get)
            print(f"All sat early, {LABELS[first]} eliminated immediately.")
            eliminated = first
            pause_music()
            break
        time.sleep(0.05)

    if eliminated is None and paused_event.is_set():
        if early_sits:
            first_early = min(early_sits, key=early_sits.get)
            print(f"Early sitter existed, {LABELS[first_early]} eliminated at pause.")
            eliminated = first_early

    if eliminated is None:
        print("No early sits. Detecting sits AFTER pause.")
        for p in SENSORS:
            last_sit_times[p] = 0
        while not all_sensors_pressed(SENSORS):
            for p in SENSORS:
                if is_sensor_pressed(p) and last_sit_times[p] == 0:
                    last_sit_times[p] = time.time()
                    print(f"{LABELS[p]} sat at {last_sit_times[p]:.2f} (post-pause)")
            time.sleep(0.05)
        eliminated = max(SENSORS, key=lambda p: last_sit_times[p])

    print(f"Round 1 Eliminated: {LABELS[eliminated]} (GPIO {eliminated})")
    return eliminated


def sequence_4():
    print("Right Eliminated (ACT 4)")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 12")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 9")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_EL, 1.0)


def sequence_5():
    print("Left Eliminated")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 10")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 9")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_EM, 1.0)


def sequence_6():
    print("Middle Eliminated")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 11")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 9")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_EMR, 1.0)


def pin_to_chair_cue(pin):
    return {17: REAPER_R2TR, 22: REAPER_R2TM, 27: REAPER_R2TL}.get(pin)


def wait_for_two_pressed(pins):
    while True:
        pressed = {p for p in pins if is_sensor_pressed(p)}
        if len(pressed) >= 2:
            return pressed
        time.sleep(0.02)


def sequence_7_intro_round2():
    print("Seq 7: Round 2 Intro")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 12")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 10")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 11")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 9")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_R2INTRO, 1.0)
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 18")


def sequence_8_round2():
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 18")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 19")
    print("Seq 8: Round 2 Start")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_R2GAME, 1.0)

    target_pin = random.choice(SENSORS)
    print(f"[Round 2] Target chair: {LABELS[target_pin]} (GPIO {target_pin})")
    clue = pin_to_chair_cue(target_pin)
    if clue:
        send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
        send_message(REAPER_IP, REAPER_PORT, clue, 1.0)

    pressed_two = wait_for_two_pressed(SENSORS)
    print(f"Two pressed: {', '.join(LABELS[p] for p in pressed_two)}")
    correct = target_pin in pressed_two
    if not correct:
        sequence_12_loser()
    return pressed_two, target_pin, correct


def sequence_12_loser():
    print("Seq 12: Loser")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Off Sequence 19")
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 17")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_AE, 1.0)


def sequence_13_victory(w):
    print(f"Sequence 13: Victory! Winner chair: {LABELS[w]} (GPIO {w})")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_WIN, 1.0)
    seq = {27: 13, 17: 14, 22: 15}.get(w)
    if seq is not None:
        send_message(MA3_IP, MA3_PORT, GMA3_ADDR, f"Go+ Sequence {seq}")


def sequence_outro():
    print("Sequence: Outro")
    send_message(REAPER_IP, REAPER_PORT, REAPER_PLAY, 1.0)
    send_message(REAPER_IP, REAPER_PORT, REAPER_OUTRO, 1.0)
    send_message(MA3_IP, MA3_PORT, GMA3_ADDR, "Go+ Sequence 16")


class GameGUI:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Chair Game Controller")
        self.root.geometry("520x420")
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

        self.container = ttk.Frame(self.root, padding=20)
        self.container.pack(fill="both", expand=True)
        self.status = tk.StringVar(value="Waiting for all 3 participants to sit...")
        ttk.Label(self.root, textvariable=self.status, anchor="w").pack(fill="x", side="bottom")

        self.eliminated1 = None
        self.winner = None
        self.last_round2_target = None
        self.show_waiting_page()

    def clear_page(self):
        for w in self.container.winfo_children():
            w.destroy()

    def update_sensor_labels(self):
        for p in SENSORS:
            state = "DOWN" if is_sensor_pressed(p) else "UP"
            self.sensor_vars[p].set(f"{LABELS[p]} seat (GPIO {p}): {state}")
        self.root.after(200, self.update_sensor_labels)

    def show_waiting_page(self):
        self.clear_page()
        ttk.Label(self.container, text="Waiting for 3 participants...", font=("Arial", 18, "bold")).pack(pady=10)
        ttk.Label(self.container, text=f"When all seats are held for {WAIT_HOLD_TIME}s, GUI opens.").pack(pady=10)
        self.sensor_vars = {p: tk.StringVar(value=f"{LABELS[p]} seat (GPIO {p}): UP") for p in SENSORS}
        for p in SENSORS:
            ttk.Label(self.container, textvariable=self.sensor_vars[p]).pack()
        self.update_sensor_labels()

    def show_start_page(self):
        self.clear_page()
        ttk.Label(self.container, text="All Participants Seated!", font=("Arial", 18, "bold")).pack(pady=10)
        ttk.Button(self.container, text="Start Game Intro (Seq 2)", command=self.start_seq2).pack(pady=20)

    def start_seq2(self):
        global game_running
        game_running = True
        sequence_2_intro()
        self.show_round1_page()

    def show_round1_page(self):
        self.clear_page()
        ttk.Label(self.container, text="Round 1", font=("Arial", 18, "bold")).pack(pady=10)
        ttk.Button(self.container, text="Start Round 1 (Seq 3)", command=self.run_round1).pack(pady=20)

    def run_round1(self):
        def worker():
            elim = sequence_3_round1()
            self.eliminated1 = elim
            self.root.after(0, self.show_round1_result_page)
        threading.Thread(target=worker, daemon=True).start()
        self.show_modal("Round 1 Running", "Waiting for players to sit...")

    def show_round1_result_page(self):
        self.destroy_modal()
        self.clear_page()
        ttk.Label(self.container, text="Round 1 Result", font=("Arial", 18, "bold")).pack(pady=10)
        ttk.Label(self.container, text=f"Eliminated: {LABELS[self.eliminated1]} (GPIO {self.eliminated1})").pack(pady=10)
        ttk.Label(self.container, text="Play a sequence (operator selectable):").pack(pady=6)
        f = ttk.Frame(self.container)
        f.pack(pady=6)
        ttk.Button(f, text="Seq 4", command=sequence_4).grid(row=0, column=0, padx=5)
        ttk.Button(f, text="Seq 5", command=sequence_5).grid(row=0, column=1, padx=5)
        ttk.Button(f, text="Seq 6", command=sequence_6).grid(row=0, column=2, padx=5)
        ttk.Separator(self.container).pack(fill="x", pady=10)
        ttk.Button(self.container, text="Proceed to Round 2 Intro (Seq 7)", command=self.show_round2_intro).pack(pady=10)

    def show_round2_intro(self):
        sequence_7_intro_round2()
        self.clear_page()
        ttk.Label(self.container, text="Round 2 Intro", font=("Arial", 18, "bold")).pack(pady=10)
        if self.last_round2_target is not None:
            ttk.Label(self.container, text=f"Last target was: {LABELS[self.last_round2_target]}").pack(pady=4)
        ttk.Button(self.container, text="Start Round 2 (Seq 8)", command=self.run_round2).pack(pady=20)

    def run_round2(self):
        def worker():
            pressed_two, target, ok = sequence_8_round2()
            self.last_round2_target = target
            if ok:
                self.winner = target
                self.root.after(0, lambda: self.show_round2_win_page(pressed_two, target))
            else:
                self.root.after(0, lambda: self.show_round2_wrong_page(pressed_two, target))
        threading.Thread(target=worker, daemon=True).start()
        self.show_modal("Round 2 Running", "Waiting for two chairs to be sat on...")

    def show_round2_win_page(self, pressed_two, target):
        self.destroy_modal()
        self.clear_page()
        ttk.Label(self.container, text="Round 2 Result - CORRECT", font=("Arial", 18, "bold")).pack(pady=10)
        chosen = ", ".join(f"{LABELS[p]} (GPIO {p})" for p in pressed_two)
        ttk.Label(self.container, text=f"Chairs pressed: {chosen}").pack(pady=6)
        ttk.Label(self.container, text=f"Target chair: {LABELS[target]} (GPIO {target})").pack(pady=6)

        ttk.Separator(self.container).pack(fill="x", pady=10)
        ttk.Button(self.container, text="Play Winning Sequence", command=lambda: sequence_13_victory(target)).pack(pady=6)
        ttk.Button(self.container, text="Play Outro", command=sequence_outro).pack(pady=6)
        ttk.Button(self.container, text="Restart Game", command=self.reset_to_waiting).pack(pady=6)

    def show_round2_wrong_page(self, pressed_two, target):
        self.destroy_modal()
        self.clear_page()
        ttk.Label(self.container, text="Round 2 Result - WRONG", font=("Arial", 18, "bold")).pack(pady=10)
        chosen = ", ".join(f"{LABELS[p]} (GPIO {p})" for p in pressed_two)
        ttk.Label(self.container, text=f"Chairs pressed: {chosen}").pack(pady=6)
        ttk.Label(self.container, text=f"Target chair was: {LABELS[target]} (GPIO {target})").pack(pady=6)
        ttk.Separator(self.container).pack(fill="x", pady=10)
        ttk.Button(self.container, text="Restart Round 2", command=self.show_round2_intro).pack(pady=10)

    def reset_to_waiting(self):
        global game_running
        game_running = False
        self.status.set("Waiting for all 3 participants to sit...")
        startup_sequences()
        self.show_waiting_page()

    def show_modal(self, title, msg):
        self.modal = tk.Toplevel(self.root)
        self.modal.title(title)
        self.modal.grab_set()
        ttk.Label(self.modal, text=msg, padding=20).pack()
        self.modal.geometry("+%d+%d" % (self.root.winfo_rootx() + 80, self.root.winfo_rooty() + 80))

    def destroy_modal(self):
        try:
            self.modal.destroy()
        except Exception:
            pass

    def on_close(self):
        global stop_threads
        stop_threads = True
        GPIO.cleanup()
        self.root.destroy()
        sys.exit(0)


def wait_for_all_to_sit(gui: GameGUI):
    global stop_threads, game_running
    while not stop_threads:
        if not game_running:
            if all_sensors_pressed(SENSORS):
                t0 = time.time()
                while all_sensors_pressed(SENSORS) and not game_running and not stop_threads:
                    if time.time() - t0 >= WAIT_HOLD_TIME:
                        print("All players seated! Opening GUI.")
                        gui.root.after(0, lambda: gui.status.set("All seated. Ready to start."))
                        gui.root.after(0, gui.show_start_page)
                        while not game_running and all_sensors_pressed(SENSORS) and not stop_threads:
                            time.sleep(0.2)
                        break
                    time.sleep(0.05)
        time.sleep(0.1)


def main():
    gui = GameGUI()
    startup_sequences()
    threading.Thread(target=wait_for_all_to_sit, args=(gui,), daemon=True).start()
    atexit.register(GPIO.cleanup)
    gui.root.mainloop()


if __name__ == "__main__":
    main()
