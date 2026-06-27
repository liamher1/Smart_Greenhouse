import json
import time
import ntp_sync
import dht_sensor
import soil_sensor
import float_switch
import pump
import fan
import mqtt_client
from config import DEVICE_ID, TELEMETRY_INTERVAL_SEC, MQTT_COMMAND_TOPIC

TELEMETRY_TOPIC = f"greenhouse/telemetry/{DEVICE_ID}"
ACK_TOPIC       = f"commands/greenhouse/{DEVICE_ID}/ack"

_MAX_MQTT_RETRIES = 3


def _utc_now():
    t = time.gmtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}+00:00".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )


def _on_command(topic, data):
    command_id = data.get("command_id")
    action     = data.get("action")

    if action == "PUMP_ON":
        if float_switch.is_empty():
            print("Safety interlock: tank empty — PUMP_ON blocked")
            return
        pump.on()
    elif action == "PUMP_OFF":
        pump.off()
    elif action == "FAN_ON":
        fan.on()
    elif action == "FAN_OFF":
        fan.off()
    else:
        print(f"Unknown action '{action}' — ignoring")
        return

    if command_id:
        mqtt_client.publish(ACK_TOPIC, {"command_id": command_id})
        print(f"ACK sent for command {command_id}")


def _connect_mqtt():
    for attempt in range(_MAX_MQTT_RETRIES):
        try:
            mqtt_client.connect(_on_command)
            return True
        except Exception as e:
            remaining = _MAX_MQTT_RETRIES - attempt - 1
            if remaining > 0:
                print(f"MQTT connect failed: {e} — retrying in 5s ({remaining} left)")
                time.sleep(5)
            else:
                print(f"MQTT connect failed: {e} — running in offline mode")
    return False


def _reconnect_with_backoff():
    delay = 2
    while True:
        try:
            mqtt_client.connect(_on_command)
            print("MQTT reconnected")
            return True
        except Exception as e:
            print(f"MQTT reconnect failed: {e} — retrying in {delay}s")
            time.sleep(delay)
            delay = min(delay * 2, 60)


def _publish_telemetry(mqtt_ok):
    try:
        temp, hum = dht_sensor.read()
    except (OSError, ValueError) as e:
        print(f"DHT read error (invalid value): {e}")
        temp, hum = None, None

    soil = soil_sensor.read()
    tank_empty = float_switch.is_empty()

    payload = {
        "header": {
            "type": "telemetry",
            "device_id": DEVICE_ID,
            "timestamp": _utc_now(),
        },
        "payload": {
            "temperature": temp,
            "humidity": hum,
            "soil_moisture": soil,
        },
    }
    print(f"Telemetry: {json.dumps(payload)}")
    if mqtt_ok:
        mqtt_client.publish(TELEMETRY_TOPIC, payload)


def main():
    ntp_sync.sync()

    # Diagnostic: read DHT22 before MQTT connects to isolate socket interference
    try:
        t, h = dht_sensor.read()
        print(f"PRE-MQTT DHT read OK: {t} C  {h} %")
    except Exception as e:
        print(f"PRE-MQTT DHT read FAILED: {e}")

    mqtt_ok = _connect_mqtt()

    last_publish = time.ticks_ms() - TELEMETRY_INTERVAL_SEC * 1000

    while True:
        # Safety interlock — enforce every iteration regardless of MQTT state
        if float_switch.is_empty():
            pump.off()

        # MQTT command check with reconnect on drop
        if mqtt_ok:
            try:
                mqtt_client.check_msg()
            except OSError as e:
                mqtt_ok = False
                print(f"MQTT lost: {e} — reconnecting with backoff")
                mqtt_ok = _reconnect_with_backoff()

        # Non-blocking telemetry cadence
        if time.ticks_diff(time.ticks_ms(), last_publish) >= TELEMETRY_INTERVAL_SEC * 1000:
            try:
                _publish_telemetry(mqtt_ok)
            except Exception as e:
                print(f"Telemetry publish error: {e}")
            last_publish = time.ticks_ms()

        time.sleep_ms(100)


main()
