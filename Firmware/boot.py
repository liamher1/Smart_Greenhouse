import network
import time
from config import WIFI_SSID, WIFI_PASSWORD

def connect():
    wlan = network.WLAN(network.STA_IF)
    wlan.active(True)
    if wlan.isconnected():
        return

    print(f"Connecting to WiFi '{WIFI_SSID}'...")
    wlan.connect(WIFI_SSID, WIFI_PASSWORD)

    deadline = time.time() + 10
    while not wlan.isconnected():
        if time.time() > deadline:
            raise RuntimeError("WiFi connection timed out after 10s")
        time.sleep(0.5)

    print("WiFi connected:", wlan.ifconfig()[0])

connect()
