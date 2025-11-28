from rpi_ws281x import PixelStrip, Color
import time, random, threading, sys, math, colorsys

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

BPM = 129.0
BEAT_DURATION = 60.0 / BPM
FRAMES_PER_BEAT = 10
FRAME_DT = BEAT_DURATION / FRAMES_PER_BEAT

CLUB_START_DELAY = 1.0
CLUB_EFFECT_DURATION = 16.0

BLAST_DURATION = 2.0

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

    clear(s1)
    clear(s2)


def neon_color():
    h = random.random()
    s = random.uniform(0.9, 1.0)
    v = random.uniform(0.5, 0.9)
    r, g, b = colorsys.hsv_to_rgb(h, s, v)
    return int(r * 255), int(g * 255), int(b * 255)


def blend_color(rgb, factor):
    r, g, b = rgb
    return Color(int(r * factor), int(g * factor), int(b * factor))


def club_129bpm_effect(s1, s2, duration_sec):
    global running

    segment_size = 25
    start_time = time.time()
    end_time = start_time + duration_sec

    while running and time.time() < end_time:
        base_color = neon_color()
        accent_color = neon_color()

        for beat in range(4):
            if not running or time.time() >= end_time:
                break

            for frame in range(FRAMES_PER_BEAT):
                if not running or time.time() >= end_time:
                    break

                phase = frame / float(FRAMES_PER_BEAT)
                intensity = math.sin(phase * math.pi)
                pulse = max(0.0, intensity)

                for i in range(LED_COUNT):
                    seg_index = i // segment_size

                    if beat == 0:
                        c = blend_color(base_color, pulse)
                    elif beat == 1:
                        front = int(phase * (LED_COUNT / segment_size))
                        if seg_index <= front:
                            c = blend_color(accent_color, pulse)
                        else:
                            c = blend_color(base_color, pulse * 0.3)
                    elif beat == 2:
                        if i < LED_COUNT // 2:
                            c = blend_color(base_color, pulse)
                        else:
                            c = blend_color(accent_color, pulse * 0.8)
                    else:
                        if seg_index % 2 == 0:
                            c = blend_color(base_color, pulse)
                        else:
                            c = blend_color(accent_color, pulse * 0.8)

                    s1.setPixelColor(i, c)
                    s2.setPixelColor(i, c)

                s1.show()
                s2.show()
                time.sleep(FRAME_DT)

    for step in range(20, -1, -1):
        factor = step / 20.0
        for i in range(LED_COUNT):
            c_val = s1.getPixelColor(i)
            r = (c_val >> 16) & 0xFF
            g = (c_val >> 8) & 0xFF
            b = c_val & 0xFF
            s1.setPixelColor(i, Color(int(r * factor), int(g * factor), int(b * factor)))
            s2.setPixelColor(i, Color(int(r * factor), int(g * factor), int(b * factor)))
        s1.show()
        s2.show()
        time.sleep(0.03)


def blast_effect(s1, s2, duration_sec):
    center = LED_COUNT // 2
    start_time = time.time()
    end_time = start_time + duration_sec

    while running and time.time() < end_time:
        t = time.time() - start_time
        phase = min(1.0, t / duration_sec)
        radius = int(phase * center)

        for i in range(LED_COUNT):
            dist = abs(i - center)
            if dist <= radius:
                if (i + int(t * 50)) % 2 == 0:
                    col = Color(255, 230, 80)
                else:
                    col = Color(255, 255, 255)
            else:
                col = 0

            s1.setPixelColor(i, col)
            s2.setPixelColor(i, col)

        s1.show()
        s2.show()
        time.sleep(0.02)


try:
    clear(strip1)
    clear(strip2)

    spin_both()
    anticipation_pulse(strip1, strip2)
    jackpot_flash(strip1, strip2)
    sparkle_fade(strip1, strip2)

    time.sleep(CLUB_START_DELAY)
    club_129bpm_effect(strip1, strip2, duration_sec=CLUB_EFFECT_DURATION)

    clear(strip1)
    clear(strip2)

    blast_effect(strip1, strip2, duration_sec=BLAST_DURATION)

    clear(strip1)
    clear(strip2)

    running = False
    sys.exit(0)

except KeyboardInterrupt:
    running = False
    clear(strip1)
    clear(strip2)
    sys.exit(0)
