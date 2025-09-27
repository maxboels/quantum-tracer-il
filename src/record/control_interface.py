import lgpio
import time

# Pins
STEERING_PIN = 18
THROTTLE_PIN = 23

# Handle öffnen
h = lgpio.gpiochip_open(0)

# Pins als Input
# lgpio.gpio_claim_input(h, STEERING_PIN)
# lgpio.gpio_claim_input(h, THROTTLE_PIN)

last_rise = None
period = None
high_time = None

def cb_func(chip, gpio, level, tick):
    """
    Wird bei jeder Flanke aufgerufen.
    tick = µs Timestamp vom Kernel
    level = 1 (High), 0 (Low)
    """
    global last_rise, period, high_time

    if level == 1:  # Rising
        if last_rise is not None:
            period = (tick - last_rise) / 1_000_000.0  # µs → s
        last_rise = tick
    elif level == 0:  # Falling
        if last_rise is not None:
            high_time = (tick - last_rise) / 1_000_000.0

# Callback registrieren für beide Flanken
cb = lgpio.callback(h, THROTTLE_PIN, lgpio.BOTH_EDGES, cb_func)

try:
    while True:
        if period and high_time and period > 0:
            freq = 1.0 / period
            duty = (high_time / period) * 100.0
            print(f"f = {freq:8.1f} Hz, duty = {duty:6.2f} %")
            period = None
            high_time = None
        time.sleep(0.05)
except KeyboardInterrupt:
    pass
finally:
    cb.cancel()
    lgpio.gpiochip_close(h)