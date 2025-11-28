from rpi_ws281x import PixelStrip, Color
import time, random, threading, sys

LED_COUNT = 400
LED_PIN1 = 18
LED_PIN2 = 19
LED_FREQ_HZ = 800000
LED_DMA = 10
LED_BRIGHTNESS = 200
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

NUM_SPOTS = 18
FRAME_WAIT_MS = 20
FADE_FACTOR = 0.75
SPARKLE_CHANCE = 0.05

DISCO_DURATION = 14
FADE_OUT_START = 12

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


def wheel(pos: int) -> Color:
    pos = pos % 256
    if pos < 85:
        return Color(pos * 3, 255 - pos * 3, 0)
    elif pos < 170:
        pos -= 85
        return Color(255 - pos * 3, 0, pos * 3)
    else:
        pos -= 170
        return Color(0, pos * 3, 255 - pos * 3)


def dim_color(c: int, factor: float) -> Color:
    r = (c >> 16) & 0xFF
    g = (c >> 8) & 0xFF
    b = c & 0xFF
    r = int(r * factor)
    g = int(g * factor)
    b = int(b * factor)
    return Color(r, g, b)


def fade_strip(strip: PixelStrip, factor: float):
    n = strip.numPixels()
    for i in range(n):
        old_c = strip.getPixelColor(i)
        strip.setPixelColor(i, dim_color(old_c, factor))


def disco_ball(strips, duration=DISCO_DURATION):
    if not strips:
        return

    n = strips[0].numPixels()
    start_time = time.time()
    end_time = start_time + duration

    spots = []
    for _ in range(NUM_SPOTS):
        pos = random.uniform(0, n - 1)
        speed = random.choice([-1, 1]) * random.uniform(0.3, 1.6)
        color = wheel(random.randint(0, 255))
        spots.append({"pos": pos, "speed": speed, "color": color})

    while running and time.time() < end_time:
        now = time.time()
        elapsed = now - start_time

        if elapsed >= FADE_OUT_START:
            dynamic_fade = 0.4
        else:
            dynamic_fade = FADE_FACTOR

        for strip in strips:
            fade_strip(strip, dynamic_fade)

        if elapsed < FADE_OUT_START:
            for s in spots:
                s["pos"] += s["speed"]

                if s["pos"] < 0:
                    s["pos"] = 0
                    s["speed"] *= -1
                elif s["pos"] > n - 1:
                    s["pos"] = n - 1
                    s["speed"] *= -1

                idx = int(s["pos"])
                for strip in strips:
                    strip.setPixelColor(idx, s["color"])

            if random.random() < SPARKLE_CHANCE:
                idx = random.randint(0, n - 1)
                for strip in strips:
                    strip.setPixelColor(idx, Color(255, 255, 255))

        for strip in strips:
            strip.show()

        time.sleep(FRAME_WAIT_MS / 1000.0)

    for strip in strips:
        clear(strip)


try:
    clear(strip1)
    clear(strip2)

    spin_both()
    anticipation_pulse(strip1, strip2)
    jackpot_flash(strip1, strip2)
    sparkle_fade(strip1, strip2)

    time.sleep(2)

    disco_ball([strip1, strip2], duration=DISCO_DURATION)

    clear(strip1)
    clear(strip2)

    running = False
    sys.exit(0)

except KeyboardInterrupt:
    running = False
    clear(strip1)
    clear(strip2)
    sys.exit(0)
