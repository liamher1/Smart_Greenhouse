"""
End-to-end MQTT test:
  1. Wait for ESP32 telemetry to arrive (confirms publish works)
  2. Send a FAN_ON command to the device
  3. Wait for the device ACK (confirms subscribe + command handling works)
  4. Send FAN_OFF and wait for ACK
  5. Print a pass/fail summary
"""
import json, time, uuid, threading
import paho.mqtt.client as mqtt

BROKER      = "127.0.0.1"
PORT        = 1883
DEVICE_ID   = "esp32-gh-01"
TEL_TOPIC   = f"greenhouse/telemetry/{DEVICE_ID}"
CMD_TOPIC   = f"commands/greenhouse/{DEVICE_ID}"
ACK_TOPIC   = f"commands/greenhouse/{DEVICE_ID}/ack"

TELEMETRY_TIMEOUT = 30   # seconds to wait for first telemetry
ACK_TIMEOUT       = 15   # seconds to wait for command ACK

telemetry_event = threading.Event()
ack_events: dict[str, threading.Event] = {}
results = []

def ts():
    return time.strftime("%H:%M:%S")

def on_connect(client, userdata, flags, rc, props=None):
    print(f"[{ts()}] Monitor connected to broker (rc={rc})")
    client.subscribe(TEL_TOPIC)
    client.subscribe(ACK_TOPIC)
    print(f"[{ts()}] Subscribed to:\n  {TEL_TOPIC}\n  {ACK_TOPIC}\n")

def on_message(client, userdata, msg):
    topic = msg.topic
    try:
        payload = json.loads(msg.payload)
    except Exception:
        payload = msg.payload.decode()

    if topic == TEL_TOPIC:
        inner = payload.get("payload", {})
        hdr   = payload.get("header", {})
        print(f"[{ts()}] TELEMETRY from {hdr.get('device_id','?')}")
        print(f"          temp={inner.get('temperature')}°C  "
              f"hum={inner.get('humidity')}%  "
              f"soil={inner.get('soil_moisture')}")
        telemetry_event.set()

    elif topic == ACK_TOPIC:
        cid = payload.get("command_id")
        print(f"[{ts()}] ACK received  command_id={cid}")
        if cid in ack_events:
            ack_events[cid].set()

client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
client.on_connect = on_connect
client.on_message = on_message
client.connect(BROKER, PORT, 60)
client.loop_start()

# ── Step 1: wait for telemetry ────────────────────────────────────────────────
print(f"[{ts()}] Waiting up to {TELEMETRY_TIMEOUT}s for ESP32 telemetry...")
got_tel = telemetry_event.wait(timeout=TELEMETRY_TIMEOUT)
if got_tel:
    print(f"[{ts()}] PASS — telemetry received\n")
    results.append(("Telemetry publish (ESP32->broker)", True))
else:
    print(f"[{ts()}] FAIL — no telemetry within {TELEMETRY_TIMEOUT}s\n")
    results.append(("Telemetry publish (ESP32->broker)", False))

# ── Step 2 & 3: send FAN_ON, wait for ACK ────────────────────────────────────
for action in ("FAN_ON", "FAN_OFF"):
    cid = str(uuid.uuid4())
    ack_events[cid] = threading.Event()
    cmd = {"command_id": cid, "action": action}
    client.publish(CMD_TOPIC, json.dumps(cmd))
    print(f"[{ts()}] Sent {action}  command_id={cid}")
    got_ack = ack_events[cid].wait(timeout=ACK_TIMEOUT)
    label = f"Command {action} ACK (broker->ESP32->broker)"
    if got_ack:
        print(f"[{ts()}] PASS — ACK received\n")
        results.append((label, True))
    else:
        print(f"[{ts()}] FAIL — no ACK within {ACK_TIMEOUT}s\n")
        results.append((label, False))
    time.sleep(1)

client.loop_stop()
client.disconnect()

# ── Summary ───────────────────────────────────────────────────────────────────
print("=" * 55)
print("RESULTS")
print("=" * 55)
for label, ok in results:
    status = "PASS" if ok else "FAIL"
    print(f"  [{status}] {label}")
print("=" * 55)
