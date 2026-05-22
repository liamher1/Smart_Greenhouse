import machine
from config import PUMP_PIN, PUMP_ACTIVE_HIGH

_relay = machine.Pin(PUMP_PIN, machine.Pin.OUT)

# Ensure pump is off at import time regardless of relay polarity
_relay.value(0 if PUMP_ACTIVE_HIGH else 1)


def _active():
    return 1 if PUMP_ACTIVE_HIGH else 0

def _inactive():
    return 0 if PUMP_ACTIVE_HIGH else 1


def on():
    _relay.value(_active())
    print("Pump ON")

def off():
    _relay.value(_inactive())
    print("Pump OFF")

def is_on():
    return _relay.value() == _active()
