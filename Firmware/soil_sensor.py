import machine
from config import SOIL_MOISTURE_PIN, SOIL_ADC_DRY, SOIL_ADC_WET

_adc = machine.ADC(machine.Pin(SOIL_MOISTURE_PIN))
_adc.atten(machine.ADC.ATTN_11DB)


def read() -> float:
    """Return soil moisture as a percentage (0.0 = dry, 100.0 = saturated).

    Converts the raw ADC reading using the calibration constants in config.py.
    Clamps the result to 0–100 to handle readings outside the calibration range.
    """
    raw = _adc.read()
    pct = (SOIL_ADC_DRY - raw) / (SOIL_ADC_DRY - SOIL_ADC_WET) * 100.0
    return max(0.0, min(100.0, pct))
