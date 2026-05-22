import time
import ntp_sync
import dht_sensor
import pump
import mqtt_client
from config import DEVICE_ID, TELEMETRY_INTERVAL_S

TELEMETRY_TOPIC = f"greenhouse/telemetry/{DEVICE_ID}"
ACK_TOPIC       = f"commands/greenhouse/{DEVICE_ID}/ack"


def _utc_now():
    t = time.gmtime()
    return "{:04d}-{:02d}-{:02d}T{:02d}:{:02d}:{:02d}+00:00".format(
        t[0], t[1], t[2], t[3], t[4], t[5]
    )


def _on_command(topic, data):
    command_id = data.get("command_id")
    action     = data.get("action")

    if action == "TURN_ON_WATER_PUMP":
        pump.on()
    elif action == "TURN_OFF_WATER_PUMP":
        pump.off()
    else:
        print(f"Unknown action '{action}' — ignoring")
        return

    # Always ACK so the backend doesn't time out waiting
    if command_id:
        mqtt_client.publish(ACK_TOPIC, {"command_id": command_id})
        print(f"ACK sent for command {command_id}")


def _publish_telemetry():
    temp, hum = dht_sensor.read()
    payload = {
        "header": {
            "type": "telemetry",
            "device_id": DEVICE_ID,
            "timestamp": _utc_now(),
        },
        "payload": {
            "temperature": temp,
            "humidity": hum,
        },
    }
    mqtt_client.publish(TELEMETRY_TOPIC, payload)
    print(f"Telemetry published: {temp}°C  {hum}%")


def main():
    ntp_sync.sync()
    mqtt_client.connect(_on_command)

    last_publish = 0

    while True:
        mqtt_client.check_msg()

        now = time.time()
        if now - last_publish >= TELEMETRY_INTERVAL_S:
            try:
                _publish_telemetry()
                last_publish = now
            except OSError as e:
                print(f"DHT read error (sensor): {e}")
            except ValueError as e:
                print(f"DHT read error (invalid value): {e}")
            except Exception as e:
                print(f"Telemetry publish error: {e}")

        time.sleep(0.1)


main()
