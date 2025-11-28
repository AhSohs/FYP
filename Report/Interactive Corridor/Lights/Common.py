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

FADE_IN_DURATION = 4.0
FADE_OUT_DURATION = 4.0
FRAME_DELAY = 0.02

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


def set_white(strip, pixel, brightness):
    brightness = max(0.0, min(1.0, brightness))
    val = int(255 * brightness)
    strip.setPixelColor(pixel, Color(val, val, val))


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


def fade_in_time_based(s1, s2):
    n = s1.numPixels()
    start_time = time.monotonic()

    while running:
        t = time.monotonic() - start_time
        if t >= FADE_IN_DURATION:
            break

        progress = t / FADE_IN_DURATION
        front_pos = progress * (n - 1)

        for i in range(n):
            if i < int(front_pos):
                brightness = 1.0
            elif i > int(front_pos) + 1:
                brightness = 0.0
            else:
                dist = abs(i - front_pos)
                brightness = max(0.0, min(1.0, 1.0 - dist))

            set_white(s1, i, brightness)
            set_white(s2, i, brightness)

        s1.show()
        s2.show()
        time.sleep(FRAME_DELAY)

    if running:
        for i in range(n):
            set_white(s1, i, 1.0)
            set_white(s2, i, 1.0)
        s1.show()
        s2.show()


def fade_out_time_based(s1, s2):
    n = s1.numPixels()
    start_time = time.monotonic()

    while running:
        t = time.monotonic() - start_time
        if t >= FADE_OUT_DURATION:
            break

        progress = t / FADE_OUT_DURATION
        front_pos = progress * (n - 1)

        for i in range(n):
            if i < int(front_pos):
                brightness = 0.0
            elif i > int(front_pos) + 1:
                brightness = 1.0
            else:
                dist = abs(i - front_pos)
                brightness = max(0.0, min(1.0, 1.0 - dist))

            set_white(s1, i, brightness)
            set_white(s2, i, brightness)

        s1.show()
        s2.show()
        time.sleep(FRAME_DELAY)

    if running:
        for i in range(n):
            set_white(s1, i, 0.0)
            set_white(s2, i, 0.0)
        s1.show()
        s2.show()


def white_fade_sequence(s1, s2):
    if not running:
        return
    fade_in_time_based(s1, s2)
    if not running:
        return
    fade_out_time_based(s1, s2)


try:
    clear(strip1)
    clear(strip2)

    spin_both()
    anticipation_pulse(strip1, strip2)
    jackpot_flash(strip1, strip2)
    sparkle_fade(strip1, strip2)
    white_fade_sequence(strip1, strip2)

    clear(strip1)
    clear(strip2)

    running = False
    sys.exit(0)

except KeyboardInterrupt:
    running = False
    clear(strip1)
    clear(strip2)
    sys.exit(0)
