from rpi_ws281x import PixelStrip, Color
import time, random, threading, sys

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

WHITE_SPARKLE_DURATION = 8.0
FIRE_WIPE_DURATION = 5.0
GROUPS_DURATION = 20.0
WINNING_DURATION = 23.0
DELAY_BETWEEN_SPARKLES = 0.5

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


def fire_palette():
    return random.choice([
        Color(255, 60, 0),
        Color(255, 80, 0),
        Color(255, 120, 0),
        Color(255, 180, 0),
        Color(255, 100, 20),
    ])


def fade_to_black(s1, s2, steps=20, gap_time=0.5):
    for level in range(steps, -1, -1):
        factor = level / float(steps)

        for strip in (s1, s2):
            for i in range(strip.numPixels()):
                c = strip.getPixelColor(i)

                r = (c >> 16) & 0xFF
                g = (c >> 8) & 0xFF
                b = c & 0xFF

                r = int(r * factor)
                g = int(g * factor)
                b = int(b * factor)

                strip.setPixelColor(i, Color(r, g, b))

            strip.show()

        time.sleep(0.02)

    clear(s1)
    clear(s2)
    time.sleep(gap_time)


def spin_reel(strip, reverse=False):
    start_time = time.time()

    while (time.time() - start_time) < SPIN_DURATION:
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
            s1.setBrightness(b)
            s2.setBrightness(b)
            s1.show()
            s2.show()
            time.sleep(0.005)

        for b in range(255, 100, -10):
            s1.setBrightness(b)
            s2.setBrightness(b)
            s1.show()
            s2.show()
            time.sleep(0.005)


def jackpot_flash(s1, s2):
    gold = Color(255, 200, 0)
    white = Color(255, 255, 255)

    for _ in range(FLASHES):
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
    while time.time() < end:
        for strip in (s1, s2):
            for i in range(strip.numPixels()):
                strip.setPixelColor(
                    i,
                    Color(255, 215, 0) if random.random() < 0.03 else 0
                )
            strip.show()
        time.sleep(0.04)


def sparkle_fade_white(s1, s2, duration=WHITE_SPARKLE_DURATION):
    end = time.time() + duration
    while time.time() < end:
        for strip in (s1, s2):
            for i in range(strip.numPixels()):
                strip.setPixelColor(
                    i,
                    Color(255, 255, 255) if random.random() < 0.03 else 0
                )
            strip.show()
        time.sleep(0.04)

    clear(s1)
    clear(s2)


def fire_wipe(s1, s2, duration=FIRE_WIPE_DURATION):
    FADE_OUT_STEPS = 60
    FADE_FACTOR = 0.85

    total_steps = LED_COUNT + FADE_OUT_STEPS
    delay = duration / float(total_steps)

    for step in range(total_steps):
        for strip in (s1, s2):
            for i in range(strip.numPixels()):
                c = strip.getPixelColor(i)
                r = (c >> 16) & 0xFF
                g = (c >> 8) & 0xFF
                b = c & 0xFF

                r = int(r * FADE_FACTOR)
                g = int(g * FADE_FACTOR)
                b = int(b * FADE_FACTOR)

                strip.setPixelColor(i, Color(r, g, b))

        if step < LED_COUNT:
            idx = step
            c = fire_palette()
            s1.setPixelColor(idx, c)
            s2.setPixelColor(idx, c)

        s1.show()
        s2.show()
        time.sleep(delay)

    clear(s1)
    clear(s2)


def moving_groups(s1, s2, duration=GROUPS_DURATION):
    start = time.time()
    pos = 0

    group_size = LED_COUNT // 5
    half_strip = LED_COUNT // 2
    step_per_frame = 2
    frame_delay = 0.01

    color_a = Color(0, 220, 255)
    color_b = Color(255, 0, 180)

    while time.time() - start < duration:
        for strip in (s1, s2):
            for i in range(strip.numPixels()):
                strip.setPixelColor(i, 0)

            for j in range(group_size):
                strip.setPixelColor((pos + j) % LED_COUNT, color_a)
                strip.setPixelColor((pos + half_strip + j) % LED_COUNT, color_b)

            strip.show()

        pos = (pos + step_per_frame) % LED_COUNT
        time.sleep(frame_delay)

    clear(s1)
    clear(s2)


def winning_effect(s1, s2, duration=WINNING_DURATION):
    end = time.time() + duration
    space_bg = Color(5, 5, 30)

    neon_colors = [
        Color(0, 255, 200),
        Color(160, 0, 255),
        Color(255, 0, 160),
        Color(180, 255, 40),
    ]

    for strip in (s1, s2):
        for i in range(strip.numPixels()):
            strip.setPixelColor(i, space_bg)
        strip.show()

    while time.time() < end:
        for strip in (s1, s2):
            for _ in range(20):
                strip.setPixelColor(random.randrange(LED_COUNT), random.choice(neon_colors))
            for _ in range(15):
                strip.setPixelColor(random.randrange(LED_COUNT), space_bg)
            strip.show()

        time.sleep(0.09)

    clear(s1)
    clear(s2)


try:
    clear(strip1)
    clear(strip2)

    spin_both()
    anticipation_pulse(strip1, strip2)
    jackpot_flash(strip1, strip2)
    sparkle_fade(strip1, strip2)
    fade_to_black(strip1, strip2, steps=20, gap_time=DELAY_BETWEEN_SPARKLES)
    sparkle_fade_white(strip1, strip2)
    fire_wipe(strip1, strip2)
    moving_groups(strip1, strip2)
    winning_effect(strip1, strip2)

    clear(strip1)
    clear(strip2)

except KeyboardInterrupt:
    clear(strip1)
    clear(strip2)
