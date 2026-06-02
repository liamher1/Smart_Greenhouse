import machine
from config import FAN_PIN, FAN_ACTIVE_HIGH

_relay = machine.Pin(FAN_PIN, machine.Pin.OUT)

# Ensure fan is off at import time regardless of relay polarity
_relay.value(0 if FAN_ACTIVE_HIGH else 1)


def _active():
    return 1 if FAN_ACTIVE_HIGH else 0

def _inactive():
    return 0 if FAN_ACTIVE_HIGH else 1


def on():
    _relay.value(_active())
    print("Fan ON")

def off():
    _relay.value(_inactive())
    print("Fan OFF")

def is_on():
    return _relay.value() == _active()
