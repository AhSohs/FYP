from rpi_ws281x import PixelStrip, Color
import time, random, threading, sys, colorsys, math

LED_COUNT = 400
LED_PIN1 = 18
LED_PIN2 = 19
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 100
LED_INVERT = False
LED_CHANNEL1 = 0
LED_CHANNEL2 = 1

SPIN_DURATION = 11
SPIN_SPEED = 0.00075
SPIN_STEP_SIZE = 3

FLASH_TOTAL_DURATION = 4.0
ON_TIME = 0.25
OFF_TIME = 0.25
FLASHES = int(FLASH_TOTAL_DURATION / (ON_TIME + OFF_TIME))

GROUP_SIZE = 5
FRAME_DELAY = 0.03
NEON_DURATION = 32.0
NEON_START_DELAY = 7.0

running = True

strip1 = PixelStrip(LED_COUNT, LED_PIN1, LED_FREQ_HZ, LED_DMA,
                    LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL1)
strip2 = PixelStrip(LED_COUNT, LED_PIN2, LED_FREQ_HZ, LED_DMA,
                    LED_INVERT, LED_BRIGHTNESS, LED_CHANNEL2)
strip1.begin()
strip2.begin()


def clear(strip):
    for i in range(strip.numPixels()):
        strip.setPixelColor(i, 0)
    strip.show()


def gold_palette(step):
    colors = [
        Color(255, 180, 0),
        Color(255, 215, 0),
        Color(255, 120, 0),
        Color(255, 255, 100)
    ]
    return colors[step % len(colors)]


def spin_reel(strip, reverse=False):
    start_time = time.time()

    while running and (time.time() - start_time) < SPIN_DURATION:
        step_color = gold_palette(int((time.time() - start_time) * 100))

        if reverse:
            for i in range(LED_COUNT - SPIN_STEP_SIZE):
                strip.setPixelColor(i, strip.getPixelColor(i + SPIN_STEP_SIZE))
            for j in range(SPIN_STEP_SIZE):
                strip.setPixelColor(LED_COUNT - 1 - j, step_color)
        else:
            for i in range(LED_COUNT - 1, SPIN_STEP_SIZE - 1, -1):
                strip.setPixelColor(i, strip.getPixelColor(i - SPIN_STEP_SIZE))
            for j in range(SPIN_STEP_SIZE):
                strip.setPixelColor(j, step_color)

        strip.show()
        time.sleep(SPIN_SPEED)


def spin_both():
    t1 = threading.Thread(target=spin_reel, args=(strip1, False))
    t2 = threading.Thread(target=spin_reel, args=(strip2, True))
    t1.start()
    t2.start()
    t1.join()
    t2.join()


def anticipation_pulse(s1, s2, cycles=1):
    for _ in range(cycles):
        for b in range(100, 255, 10):
            if not running:
                return
            s1.setBrightness(b)
            s2.setBrightness(b)
            s1.show()
            s2.show()
            time.sleep(0.005)

        for b in range(255, 100, -10):
            if not running:
                return
            s1.setBrightness(b)
            s2.setBrightness(b)
            s1.show()
            s2.show()
            time.sleep(0.005)


def jackpot_flash(s1, s2):
    gold = Color(255, 200, 0)
    white = Color(255, 255, 255)

    for _ in range(FLASHES):
        if not running:
            return

        for strip in (s1, s2):
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, random.choice([gold, white]))
            strip.show()

        time.sleep(ON_TIME)
        clear(s1)
        clear(s2)
        time.sleep(OFF_TIME)


def sparkle_fade(s1, s2, duration=1.5):
    end = time.time() + duration
    while running and time.time() < end:
        for strip in (s1, s2):
            for i in range(strip.numPixels()):
                if random.random() < 0.03:
                    strip.setPixelColor(i, Color(255, 215, 0))
                else:
                    strip.setPixelColor(i, 0)
            strip.show()
        time.sleep(0.04)
        
    clear(strip1)
    clear(strip2)


def neon_dark_rgb():
    color_ranges = [
        (0.00, 0.03),
        (0.97, 1.00),
        (0.22, 0.35),
        (0.45, 0.55),
        (0.55, 0.70),
        (0.70, 0.85),
    ]

    h = random.uniform(*random.choice(color_ranges))
    s = random.uniform(0.9, 1.0)
    v = random.uniform(0.35, 0.7)

    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def run_neon_breathing_groups(s1, s2, duration=30.0):
    group_count = LED_COUNT // GROUP_SIZE
    groups = []

    for _ in range(group_count):
        base_r, base_g, base_b = neon_dark_rgb()
        freq  = random.uniform(0.05, 0.15)
        omega = 2 * math.pi * freq
        phase = random.uniform(0, 2 * math.pi)
        groups.append({
            "base_r": base_r,
            "base_g": base_g,
            "base_b": base_b,
            "omega": omega,
            "phase": phase,
            "prev_factor": 0.0,
        })

    def update_group_color(group, factor):
        prev = group["prev_factor"]
        if prev < 0.05 and factor > prev:
            group["base_r"], group["base_g"], group["base_b"] = neon_dark_rgb()
        group["prev_factor"] = factor

    start_time = time.time()

    while running and (time.time() - start_time) < duration:
        t = time.time() - start_time

        for gi, group in enumerate(groups):
            factor = 0.5 * (1 + math.sin(group["omega"] * t + group["phase"]))
            update_group_color(group, factor)

            r = int(group["base_r"] * factor)
            g = int(group["base_g"] * factor)
            b = int(group["base_b"] * factor)
            c = Color(r, g, b)

            start_idx = gi * GROUP_SIZE
            end_idx = min(start_idx + GROUP_SIZE, LED_COUNT)
            for i in range(start_idx, end_idx):
                s1.setPixelColor(i, c)
                s2.setPixelColor(i, c)

        s1.show()
        s2.show()
        time.sleep(FRAME_DELAY)


try:
    clear(strip1)
    clear(strip2)

    spin_both()
    anticipation_pulse(strip1, strip2)
    jackpot_flash(strip1, strip2)
    sparkle_fade(strip1, strip2)

    time.sleep(NEON_START_DELAY)
    run_neon_breathing_groups(strip1, strip2, duration=NEON_DURATION)

    clear(strip1)
    clear(strip2)

    running = False
    sys.exit(0)

except KeyboardInterrupt:
    running = False
    clear(strip1)
    clear(strip2)
    sys.exit(0)
