import dht
import machine
from config import DHT_PIN

_sensor = dht.DHT22(machine.Pin(DHT_PIN))

# Sanity bounds — readings outside these are treated as sensor errors
_TEMP_MIN, _TEMP_MAX = -40.0, 80.0
_HUM_MIN,  _HUM_MAX  =   0.0, 100.0

def read():
    """Return (temperature_c, humidity_pct) from the DHT22.

    Raises ValueError if the reading is out of the sensor's valid range.
    Raises OSError if the sensor doesn't respond (wiring / timing issue).
    """
    _sensor.measure()
    temp = _sensor.temperature()
    hum  = _sensor.humidity()

    if not (_TEMP_MIN <= temp <= _TEMP_MAX):
        raise ValueError(f"Temperature {temp}°C out of range")
    if not (_HUM_MIN <= hum <= _HUM_MAX):
        raise ValueError(f"Humidity {hum}% out of range")

    return temp, hum
