import dht
import machine
import time
from config import DHT_PIN

_TEMP_MIN, _TEMP_MAX = -40.0, 80.0
_HUM_MIN,  _HUM_MAX  =   0.0, 100.0

def read():
    """Return (temperature_c, humidity_pct) from the DHT22.

    Raises ValueError if the reading is out of the sensor's valid range.
    Raises OSError if the sensor doesn't respond after two attempts.
    """
    # Recreate the sensor object each call — ensures a clean pin state
    # regardless of what happened in previous reads or during startup.
    for attempt in range(2):
        sensor = dht.DHT22(machine.Pin(DHT_PIN))
        try:
            sensor.measure()
            temp = sensor.temperature()
            hum  = sensor.humidity()

            if not (_TEMP_MIN <= temp <= _TEMP_MAX):
                raise ValueError(f"Temperature {temp}°C out of range")
            if not (_HUM_MIN <= hum <= _HUM_MAX):
                raise ValueError(f"Humidity {hum}% out of range")

            return temp, hum
        except OSError:
            if attempt == 0:
                time.sleep_ms(2000)  # DHT22 requires 2 s between reads
    raise OSError("DHT22 timed out after 2 attempts")
