import ntptime
import time

# Retry NTP up to MAX_ATTEMPTS times before giving up.
# Continuing without sync means timestamps will be wrong until the next reboot.
MAX_ATTEMPTS = 3

def sync():
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            ntptime.settime()
            t = time.gmtime()
            print(f"NTP synced: {t[0]}-{t[1]:02d}-{t[2]:02d} {t[3]:02d}:{t[4]:02d}:{t[5]:02d} UTC")
            return True
        except Exception as e:
            print(f"NTP sync attempt {attempt}/{MAX_ATTEMPTS} failed: {e}")
            if attempt < MAX_ATTEMPTS:
                time.sleep(2)

    print("NTP sync failed — timestamps may be inaccurate")
    return False
