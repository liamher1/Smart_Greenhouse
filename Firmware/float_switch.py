import machine
from config import FLOAT_SWITCH_PIN

_pin = machine.Pin(FLOAT_SWITCH_PIN, machine.Pin.IN, machine.Pin.PULL_UP)


def is_empty():
    """Return True when the water tank is empty (pin reads HIGH)."""
    return _pin.value() == 1
