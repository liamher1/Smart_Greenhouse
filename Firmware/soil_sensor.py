import machine
from config import SOIL_MOISTURE_PIN

_adc = machine.ADC(machine.Pin(SOIL_MOISTURE_PIN))
_adc.atten(machine.ADC.ATTN_11DB)


def read():
    """Return raw ADC reading 0–4095 (0 = wet, 4095 = dry)."""
    return _adc.read()
