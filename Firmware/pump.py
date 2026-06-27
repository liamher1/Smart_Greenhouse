import relay_board
from config import PUMP_RELAY_CHANNEL


def on():
    if not relay_board.is_on(PUMP_RELAY_CHANNEL):
        relay_board.on(PUMP_RELAY_CHANNEL)
        print("Pump ON")


def off():
    if relay_board.is_on(PUMP_RELAY_CHANNEL):
        relay_board.off(PUMP_RELAY_CHANNEL)
        print("Pump OFF")


def is_on():
    return relay_board.is_on(PUMP_RELAY_CHANNEL)
