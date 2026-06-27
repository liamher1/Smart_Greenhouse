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
    if _relay.value() != _active():
        _relay.value(_active())
        print("Pump ON")

def off():
    if _relay.value() != _inactive():
        _relay.value(_inactive())
        print("Pump OFF")

def is_on():
    return _relay.value() == _active()
